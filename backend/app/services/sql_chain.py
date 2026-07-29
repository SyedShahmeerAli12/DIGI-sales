"""
Text-to-SQL over the synthetic FMCG sales database (backend/data/fmcg_sales.db),
via Vanna's RAG-for-SQL pattern: schema (DDL) is embedded once at startup, and
at query time Vanna retrieves the most relevant tables/examples before asking
the LLM to write SQL — grounded generation, not a blind one-shot guess.

Reliability guards on top of Vanna, since raw LLM-to-SQL is well known to
hallucinate table/column names or generate destructive statements:
- every generated query is checked to be a single SELECT statement only
- every table/column name referenced must exist in the real schema
- the query is dry-run (EXPLAIN) before executing
- on any failure, the caller gets None instead of a guessed answer
"""

import re
import sqlite3
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from openai import OpenAI as OpenAIClient
from qdrant_client import QdrantClient
from vanna.legacy.openai import OpenAI_Chat
from vanna.legacy.qdrant import Qdrant_VectorStore

from app.core.config import settings
from app.services.vector_store import get_chat_model

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "fmcg_sales.db"


@lru_cache
def get_table_ddl() -> dict[str, str]:
    """Reads the real CREATE TABLE statements from the generated database
    itself — the single source of truth, instead of a hand-typed copy that
    could silently drift from the actual schema."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        rows = conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table'"
        ).fetchall()
        return dict(rows)
    finally:
        conn.close()


@lru_cache
def get_data_date_range() -> tuple[str, str]:
    """Reads the real min/max dates covered by the data (from the main
    sales_transactions fact table), instead of a hand-typed copy that could
    silently drift if the source spreadsheet is ever regenerated/updated."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        row = conn.execute(
            "SELECT MIN(Date), MAX(Date) FROM sales_transactions"
        ).fetchone()
        return row[0], row[1]
    finally:
        conn.close()


def _build_schema_documentation() -> str:
    start_date, end_date = get_data_date_range()
    end_year = datetime.strptime(end_date, "%Y-%m-%d").year
    return (
        "This is a synthetic FMCG (fast-moving consumer goods) Sales BI demo "
        "dataset for a distributor in Pakistan, covering multiple regions/cities. "
        "Product hierarchy: SKU_ID/SKU_Name -> Variant -> Brand -> Business_Unit "
        "(products table). Sales hierarchy is ONE self-referencing table "
        "(sales_hierarchy): each employee has a Role (Order Booker, Supervisor, "
        "Area Sales Manager, Regional Sales Manager, National Sales Manager) and "
        "a Manager_ID pointing to their manager's own Employee_ID in the same "
        "table — to find who someone reports to, self-join sales_hierarchy on "
        "Manager_ID = Employee_ID once. IMPORTANT: a manager's DIRECT reports "
        "are usually one role level down, not the role the question actually "
        "asks about — e.g. an Area Sales Manager's direct reports are "
        "Supervisors, NOT Order Bookers; Order Bookers are two levels below "
        "an ASM (ASM -> Supervisor -> Order Booker). A single-level join "
        "between ASM and Order Booker will match zero rows and wrongly look "
        "like there's no data. Whenever a question asks 'how many/which X "
        "oversees/manages the most Y' where Y is not the manager's immediate "
        "next role down, use a recursive CTE that walks the full chain down "
        "to the target role, not a single join. "
        "sales_transactions is the main fact table — one row per sale, already "
        "denormalized with the full hierarchy chain (Order_Booker_ID, "
        "Supervisor_ID, Area_Manager_ID, Regional_Manager_ID), customer, "
        "distributor, product, channel, and promotion for that sale. "
        "Net_Sales_PKR is the revenue figure to sum for 'sales'/'revenue' "
        "questions; Gross_Profit_PKR for profit/margin questions. "
        "customers links Customer_ID to Distributor_ID, Order_Booker_ID, Route, "
        "Channel (Retail/Wholesale/etc). distributors and their Service_Level "
        "cover distributor performance/coverage questions. "
        "targets has one row per Region/City/Territory per Month with "
        "Sales_Target_PKR — compare against SUM(Net_Sales_PKR) from "
        "sales_transactions for the same territory/month to get achievement. "
        "promotions has Start_Date/End_Date, Region_Scope, Brand, Discount_Pct, "
        "Campaign_Cost_PKR — join to sales_transactions via Promotion_ID (NULL "
        "means that sale wasn't part of any promotion) to analyze campaign "
        "uplift/ROI. inventory is a stock snapshot (Stock_Units vs "
        "Reorder_Level, Stock_Status) as of the most recent Snapshot_Date only "
        "— not historical. outlet_visits tracks field-force visit/productivity "
        "(Visited, Productive_Visit) by Order_Booker_ID/Customer_ID/date, for "
        "July 2026 only. "
        "Known intentional demo patterns in this data (real signal, not noise): "
        "the North region's sales decline starting May 2026; Karachi South "
        "accelerates/grows during 2026; sales_transactions rows with a "
        "non-null Promotion_ID show an uplift versus non-promoted sales for "
        "the same brand/period. "
        f"The data covers exactly {start_date} through {end_date} (today, in "
        f"sales_transactions.Date). Never invent a year/date outside this "
        f"range — resolve 'this year' as {end_year}, 'last month' as the "
        f"calendar month before {end_date}, and 'today'/'most recent' as the "
        f"literal date '{end_date}'. All date columns (Date, Month, "
        f"Snapshot_Date, Start_Date, End_Date) are plain YYYY-MM-DD text — "
        f"compare them as strings/dates directly. NEVER use SQLite's "
        f"DATE('now'), CURRENT_DATE, or datetime('now') — this data is a "
        f"frozen snapshot, not live, so those always resolve to the real live "
        f"clock instead of '{end_date}' and will silently return wrong/empty "
        f"results as real time moves past this snapshot. Always use the "
        f"literal '{end_date}' string instead. "
        "targets.Month is stored as a full date string 'YYYY-MM-DD' (e.g. "
        "'2025-01-01'), NOT 'YYYY-MM' — when joining targets to "
        "sales_transactions.Date to compare target vs actual, normalize BOTH "
        "sides to the same format first, e.g. strftime('%Y-%m', t.Month) = "
        "strftime('%Y-%m', st.Date). Comparing t.Month directly to "
        "strftime('%Y-%m', st.Date) without normalizing t.Month the same way "
        "matches zero rows and silently makes every actual-sales figure look "
        "like 0, turning a 'who missed their target' question into 'who has "
        "the highest raw target' instead — a different, wrong answer. "
        "SKU_Name already includes the variant/pack size as part of the same "
        "string (e.g. 'FreshUp Cola 250ml', 'PureSip Water 500ml') — match the "
        "full SKU_Name string exactly rather than splitting it into a "
        "brand-only name plus a separate Variant filter that doesn't match how "
        "the string is actually stored. Likewise, Territory values already "
        "include the City name as part of the same string (e.g. 'Karachi "
        "South', 'Karachi Central', 'Lahore East', 'Peshawar City') — they are "
        "NEVER just the area name alone ('South' is not a valid Territory on "
        "its own). Match the full Territory string exactly; do not filter "
        "City='Karachi' AND Territory='South' as if they were independent — "
        "that matches zero rows. "
        "When computing a rate/percentage/fraction of one thing out of a "
        "larger total, always LEFT JOIN from the larger/full table to the "
        "smaller reference table, never a plain/INNER JOIN — an INNER JOIN "
        "silently restricts both sides of the ratio to only the matching "
        "rows, which changes the meaning of the denominator and produces a "
        "wildly wrong percentage even though the query runs without error. "
        "When comparing whether something increased/decreased/grew/declined "
        "between two time periods (e.g. 'before vs after May 2026', 'this "
        "year vs last year'), NEVER compare raw cumulative SUMs over periods "
        "of unequal length (e.g. summing 16 months vs summing 3 months) — the "
        "longer period will always look bigger regardless of any real trend. "
        "Always normalize first: compare monthly/daily AVERAGES for each "
        "period, or compare the same-length window (e.g. the 3 months before "
        "vs the 3 months after), so the comparison is fair."
    )

ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are DIGI, a sales intelligence assistant. Answer the user's question "
            "using ONLY the SQL query result below — never invent numbers not present "
            "in it. Respond in Markdown. Answer in the same language (English or Urdu) "
            "the question was asked in.\n\n"
            "Formatting: never answer in a single terse line — give at least 3-4 lines "
            "of context around the figure (what it means, and relevant comparison/scale) "
            "not just the bare number. But every word of that extra context must still "
            "come only from the actual query result — never add estimates, conversions "
            "(e.g. inventing a currency exchange rate), or any figure not literally "
            "present in the result, even to sound more informative. This includes doing "
            "your own arithmetic on the result's numbers (e.g. manually adding up several "
            "rows into a total) — LLMs are unreliable at mental math and this produces "
            "wrong figures presented as fact; only state a combined total if the SQL "
            "result itself already contains that computed value as its own row/column. "
            "If you have nothing grounded to add beyond the number itself, keep it to "
            "the number plainly stated rather than pad with an invented or self-computed "
            "estimate. "
            "If the result has multiple rows (a ranking, a comparison, several "
            "SKUs/distributors/etc. each with their own figures), format it as a "
            "Markdown table — but for a single scalar result, just state it, don't "
            "wrap one number in a one-row table. When building that table, drop any "
            "raw internal ID/key column (SKU_ID, Employee_ID, Customer_ID, "
            "Distributor_ID, Promotion_ID, etc.) if the result also has a human-"
            "readable name for that same thing (SKU_Name, Employee_Name, "
            "Distributor_Name, Promotion_Name, etc.) — show only the readable name, "
            "the ID is meaningless to a business user and just adds noise. Only keep "
            "an ID column if no readable name exists for it. Use a heading for any multi-part "
            "answer. Never put a name in quotation marks — whenever you'd naturally "
            "quote a product/SKU/brand/distributor/employee name, wrap it in Markdown "
            "bold (**like this**) instead.\n\n"
            "Question: {question}\n\nSQL query used: {sql}\n\nQuery result:\n{result}",
        ),
    ]
)


class _FmcgVanna(Qdrant_VectorStore, OpenAI_Chat):
    def __init__(self, config=None, openai_client=None):
        Qdrant_VectorStore.__init__(self, config=config)
        OpenAI_Chat.__init__(self, client=openai_client, config=config)


@lru_cache
def get_vanna() -> _FmcgVanna:
    # Vanna's own SQL-generation calls are bound to whichever client is
    # passed here directly — this must respect chat_provider too, not just
    # get_chat_model() (which only covers the RAG/phrasing side), otherwise
    # "test on Groq only" would still silently hit OpenAI for every generated
    # query, since Groq's API is OpenAI-compatible and reused via base_url.
    if settings.chat_provider == "groq":
        openai_client = OpenAIClient(
            api_key=settings.groq_api_key, base_url="https://api.groq.com/openai/v1"
        )
        model = settings.groq_chat_model
    else:
        openai_client = OpenAIClient(api_key=settings.openai_api_key)
        model = settings.chat_model

    vn = _FmcgVanna(
        config={
            "client": QdrantClient(url=settings.qdrant_url),
            "model": model,
            # separate collections from the FAQ knowledge base's collection
            "ddl_collection_name": "fmcg_sql_ddl",
            "documentation_collection_name": "fmcg_sql_docs",
            "sql_collection_name": "fmcg_sql_examples",
            # The schema is small and fixed — similarity-based schema linking
            # with the default limit (10) can silently drop a table that
            # turns out to be essential for a correct join. n_results
            # comfortably above the table count means every table is always
            # included instead of relying on retrieval to guess what matters.
            "n_results": len(get_table_ddl()) + 5,
            # default is 0.7 — far too high for SQL generation, where the same
            # question should deterministically produce the same query instead
            # of occasionally inventing a different (wrong) one on rerun.
            "temperature": 0,
        },
        openai_client=openai_client,
    )
    vn.connect_to_sqlite(str(DB_PATH))
    _train_if_needed(vn)
    return vn


# Validated question->SQL pairs, retrieved by Vanna via semantic similarity at
# generation time and shown as a concrete template — a much stronger signal
# than the schema documentation alone, which the model could (and did, on
# rerun) ignore for period-comparison questions. Added after the documentation
# fix alone failed to reliably prevent comparing raw cumulative SUMs over
# unequal-length periods (verified: gave "Karachi South is NOT growing" when
# the real monthly-average trend shows it clearly is — the exact demo pattern
# this dataset was built to showcase).
GOLDEN_SQL_EXAMPLES = [
    (
        "Has the North region declined since May 2026?",
        """WITH monthly AS (
    SELECT strftime('%Y-%m', Date) AS ym, SUM(Net_Sales_PKR) AS monthly_sales
    FROM sales_transactions
    WHERE Region = 'North'
    GROUP BY strftime('%Y-%m', Date)
)
SELECT
    ROUND(AVG(CASE WHEN ym < '2026-05' THEN monthly_sales END), 0) AS avg_monthly_before_may_2026,
    ROUND(AVG(CASE WHEN ym >= '2026-05' THEN monthly_sales END), 0) AS avg_monthly_after_may_2026
FROM monthly;""",
    ),
    (
        "Is Karachi South growing in 2026 compared to 2025?",
        """WITH monthly AS (
    SELECT strftime('%Y-%m', Date) AS ym, strftime('%Y', Date) AS yr, SUM(Net_Sales_PKR) AS monthly_sales
    FROM sales_transactions
    WHERE Territory = 'Karachi South'
    GROUP BY strftime('%Y-%m', Date)
)
SELECT yr, ROUND(AVG(monthly_sales), 0) AS avg_monthly_sales
FROM monthly GROUP BY yr ORDER BY yr;""",
    ),
    (
        "What is the total revenue in Karachi South?",
        "SELECT ROUND(SUM(Net_Sales_PKR), 0) AS total_revenue "
        "FROM sales_transactions WHERE Territory = 'Karachi South';",
    ),
    (
        "Which territory missed its sales target the most?",
        """WITH ts AS (
    SELECT t.Territory, t.Month, t.Sales_Target_PKR,
        (SELECT COALESCE(SUM(st.Net_Sales_PKR), 0) FROM sales_transactions st
         WHERE st.Territory = t.Territory AND strftime('%Y-%m', st.Date) = strftime('%Y-%m', t.Month)) AS actual_sales
    FROM targets t
)
SELECT Territory, ROUND(SUM(Sales_Target_PKR - actual_sales), 0) AS total_missed
FROM ts GROUP BY Territory ORDER BY total_missed DESC LIMIT 5;""",
    ),
    (
        "Which Area Sales Manager oversees the most order bookers?",
        """WITH RECURSIVE reports_to(Employee_ID, Manager_ID, Root_ASM) AS (
    SELECT Employee_ID, Manager_ID, Employee_ID AS Root_ASM
    FROM sales_hierarchy
    WHERE Role = 'Area Sales Manager'
    UNION ALL
    SELECT sh.Employee_ID, sh.Manager_ID, rt.Root_ASM
    FROM sales_hierarchy sh
    JOIN reports_to rt ON sh.Manager_ID = rt.Employee_ID
)
SELECT asm.Employee_Name, COUNT(*) AS order_booker_count
FROM reports_to rt
JOIN sales_hierarchy ob ON rt.Employee_ID = ob.Employee_ID AND ob.Role = 'Order Booker'
JOIN sales_hierarchy asm ON rt.Root_ASM = asm.Employee_ID
GROUP BY asm.Employee_Name
ORDER BY order_booker_count DESC
LIMIT 5;""",
    ),
]


def _train_if_needed(vn: _FmcgVanna) -> None:
    existing = vn.get_training_data()
    if existing is not None and len(existing) > 0:
        return
    for ddl in get_table_ddl().values():
        vn.train(ddl=ddl)
    vn.train(documentation=_build_schema_documentation())
    for question, sql in GOLDEN_SQL_EXAMPLES:
        vn.train(question=question, sql=sql)


@lru_cache
def _allowed_tables_columns() -> dict[str, set[str]]:
    return {
        table: set(re.findall(r"(\w+)\s+(?:INTEGER|TEXT|REAL)", ddl))
        for table, ddl in get_table_ddl().items()
    }


def _looks_like_select_only(sql: str) -> bool:
    """SELECT or WITH (CTE) queries only — both are read-only. Anything else
    (INSERT/UPDATE/DELETE/DDL/etc.) is rejected outright."""
    stripped = sql.strip().rstrip(";").strip()
    if not re.match(r"^\s*(SELECT|WITH)\b", stripped, re.IGNORECASE):
        return False
    forbidden = r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|ATTACH|PRAGMA|REPLACE)\b"
    return re.search(forbidden, stripped, re.IGNORECASE) is None


def _cte_names(sql: str) -> set[str]:
    """Names defined by a WITH clause — plain ('WITH foo AS (', ', bar AS (')
    or recursive with an explicit column list ('WITH RECURSIVE foo(a, b) AS
    ('). These are query-local aliases, not real tables, but FROM/JOIN
    references to them are legitimate and must not be flagged as hallucinated
    schema. Verified failure: the plain-CTE-only version of this regex
    rejected a valid, correctly-generated recursive hierarchy-traversal query
    (WITH RECURSIVE + a column list before AS), causing it to silently fall
    back to a worse FAQ answer instead of the real one."""
    return set(
        re.findall(
            r"(?:WITH(?:\s+RECURSIVE)?|,)\s+(\w+)\s*(?:\([^)]*\))?\s+AS\s*\(",
            sql,
            re.IGNORECASE,
        )
    )


def _references_only_known_schema(sql: str) -> bool:
    known_tables = set(_allowed_tables_columns().keys()) | _cte_names(sql)
    referenced_tables = set(re.findall(r"\bFROM\s+(\w+)|\bJOIN\s+(\w+)", sql, re.IGNORECASE))
    referenced_tables = {t for pair in referenced_tables for t in pair if t}
    return referenced_tables.issubset(known_tables) and len(referenced_tables) > 0


def _dry_run_ok(sql: str) -> bool:
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute(f"EXPLAIN {sql}")
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def generate_and_execute(question: str) -> dict | None:
    """Returns {'sql', 'result_text'} on success, or None if the query couldn't
    be generated/validated/executed safely — callers must treat None as 'can't
    answer this confidently', never fall back to guessing."""
    vn = get_vanna()

    try:
        sql = vn.generate_sql(question, allow_llm_to_see_data=False)
    except Exception:  # noqa: BLE001 - any generation failure means "can't answer"
        return None

    if not sql or not _looks_like_select_only(sql):
        return None
    if not _references_only_known_schema(sql):
        return None
    if not _dry_run_ok(sql):
        return None

    try:
        result_df = vn.run_sql(sql)
    except Exception:  # noqa: BLE001 - execution failure means "can't answer"
        return None

    return {"sql": sql, "result_text": result_df.head(50).to_markdown(index=False)}


def answer_analytical_question(question: str) -> dict | None:
    """Returns {'answer', 'sql'} on success, or None if it couldn't be answered
    confidently (see generate_and_execute)."""
    executed = generate_and_execute(question)
    if executed is None:
        return None

    chain = ANSWER_PROMPT | get_chat_model() | StrOutputParser()
    answer = chain.invoke(
        {"question": question, "sql": executed["sql"], "result": executed["result_text"]}
    )
    return {"answer": answer, "sql": executed["sql"]}


def stream_analytical_answer(question: str, sql: str, result_text: str):
    """Yields answer tokens for an already-generated-and-executed SQL result."""
    chain = ANSWER_PROMPT | get_chat_model() | StrOutputParser()
    for chunk in chain.stream({"question": question, "sql": sql, "result": result_text}):
        if chunk:
            yield chunk
