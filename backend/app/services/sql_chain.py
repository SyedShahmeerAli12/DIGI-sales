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
    """Reads the real min/max dates covered by the generated data, instead of
    a hand-typed copy of app/scripts/generate_fmcg_data.py's START_DATE/END_DATE
    that could silently drift if the data is regenerated with different dates."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        row = conn.execute("SELECT MIN(date), MAX(date) FROM dim_date").fetchone()
        return row[0], row[1]
    finally:
        conn.close()


def _build_schema_documentation() -> str:
    start_date, end_date = get_data_date_range()
    end_year = datetime.strptime(end_date, "%Y-%m-%d").year
    return (
        "This is a synthetic FMCG (fast-moving consumer goods) sales database for a "
        "distributor in Pakistan. Sales hierarchy: dim_region -> dim_sales_manager -> "
        "dim_territory -> dim_area -> dim_order_booker (the field sales rep). "
        "fact_invoice_header + fact_invoice_line together are the sales transactions "
        "(one invoice per customer visit, several product lines each). net_sale in "
        "fact_invoice_line is the actual revenue figure to sum for 'sales'/'revenue'. "
        "dim_date.is_ramadan and is_eid flag the real Ramadan/Eid dates for seasonal "
        "analysis. fact_targets has one row per order booker per month with "
        "target_value vs achieved_value. "
        f"The data covers exactly {start_date} through {end_date} (today). Never "
        f"invent a year/date outside this range — resolve 'this year' as {end_year}, "
        f"'last month' as the calendar month before {end_date}, and 'today'/'most "
        f"recent' as the literal date '{end_date}', using dim_date/date columns "
        f"(format YYYY-MM-DD) or dim_date.year/month accordingly. NEVER use SQLite's "
        f"DATE('now'), CURRENT_DATE, or datetime('now') — this data is a frozen "
        f"snapshot, not live, so those always resolve to the real live clock instead "
        f"of '{end_date}' and will silently return wrong/empty results as real time "
        f"moves past this snapshot. Always use the literal '{end_date}' string instead."
    )

ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are DIGI, a sales intelligence assistant. Answer the user's question "
            "using ONLY the SQL query result below — never invent numbers not present "
            "in it. Respond in Markdown, concisely. Answer in the same language "
            "(English or Urdu) the question was asked in.\n\n"
            "Question: {question}\n\nSQL query used: {sql}\n\nQuery result:\n{result}",
        ),
    ]
)


class _FmcgVanna(Qdrant_VectorStore, OpenAI_Chat):
    def __init__(self, config=None):
        Qdrant_VectorStore.__init__(self, config=config)
        OpenAI_Chat.__init__(self, config=config)


@lru_cache
def get_vanna() -> _FmcgVanna:
    vn = _FmcgVanna(
        config={
            "client": QdrantClient(url=settings.qdrant_url),
            "api_key": settings.openai_api_key,
            "model": settings.chat_model,
            # separate collections from the FAQ knowledge base's collection
            "ddl_collection_name": "fmcg_sql_ddl",
            "documentation_collection_name": "fmcg_sql_docs",
            "sql_collection_name": "fmcg_sql_examples",
            # The schema is small and fixed (12 tables) — similarity-based schema
            # linking with the default limit (10) can silently drop a table that
            # turns out to be essential for a correct join. n_results comfortably
            # above the table count means every table is always included instead
            # of relying on retrieval to guess which ones matter.
            "n_results": len(get_table_ddl()) + 5,
            # default is 0.7 — far too high for SQL generation, where the same
            # question should deterministically produce the same query instead
            # of occasionally inventing a different (wrong) one on rerun.
            "temperature": 0,
        }
    )
    vn.connect_to_sqlite(str(DB_PATH))
    _train_if_needed(vn)
    return vn


def _train_if_needed(vn: _FmcgVanna) -> None:
    existing = vn.get_training_data()
    if existing is not None and len(existing) > 0:
        return
    for ddl in get_table_ddl().values():
        vn.train(ddl=ddl)
    vn.train(documentation=_build_schema_documentation())


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
    """Names defined by a WITH clause (e.g. 'WITH foo AS (', ', bar AS (') —
    these are query-local aliases, not real tables, but FROM/JOIN references
    to them are legitimate and must not be flagged as hallucinated schema."""
    return set(re.findall(r"(?:WITH|,)\s+(\w+)\s+AS\s*\(", sql, re.IGNORECASE))


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
