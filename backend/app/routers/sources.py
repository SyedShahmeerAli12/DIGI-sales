import json
import sqlite3
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.routers.auth import get_current_user
from app.services.sql_chain import DB_PATH, get_data_date_range

router = APIRouter(prefix="/api/sources", tags=["sources"])

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
QA_PATH = DATA_DIR / "source_questions_qa.json"

# (table, display label, group) — grouped for a readable overview, not just a
# flat table list.
FMCG_ENTITIES = [
    ("dim_region", "Regions", "Sales Organization"),
    ("dim_sales_manager", "Sales Managers", "Sales Organization"),
    ("dim_territory", "Territories", "Sales Organization"),
    ("dim_area", "Areas", "Sales Organization"),
    ("dim_order_booker", "Order Bookers", "Sales Organization"),
    ("dim_product", "Products (SKUs)", "Products & Customers"),
    ("dim_customer", "Customers", "Products & Customers"),
    ("fact_invoice_header", "Invoices", "Transactions"),
    ("fact_invoice_line", "Invoice Line Items", "Transactions"),
    ("fact_returns", "Returns", "Transactions"),
    ("fact_inventory", "Inventory Snapshots", "Transactions"),
    ("fact_targets", "Monthly Targets", "Transactions"),
]


@router.get("/source-question")
async def get_source_question_document(_user: str = Depends(get_current_user)):
    path = DATA_DIR / "source_questions_qa.pdf"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Source document not found.")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename="Source Question.pdf",
    )


@router.get("/overview")
async def get_data_overview(_user: str = Depends(get_current_user)):
    """A stakeholder-facing summary of what data backs the assistant's answers
    and how much of it there is — for the FAQ knowledge base and the FMCG
    analytics database, not the raw internals."""
    entries = json.loads(QA_PATH.read_text(encoding="utf-8"))
    persona_counts = Counter(e["persona"] for e in entries)

    conn = sqlite3.connect(str(DB_PATH))
    try:
        groups: dict[str, list[dict]] = {}
        for table, label, group in FMCG_ENTITIES:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            groups.setdefault(group, []).append(
                {"table": table, "label": label, "count": count}
            )
    finally:
        conn.close()

    start_date, end_date = get_data_date_range()

    return {
        "faq_knowledge_base": {
            "label": "Source Question.docx",
            "total_questions": len(entries),
            "personas": [
                {"name": name, "count": count} for name, count in persona_counts.items()
            ],
        },
        "fmcg_database": {
            "label": "FMCG Sales Database",
            "date_range": {"start": start_date, "end": end_date},
            "groups": [
                {"name": name, "entities": entities} for name, entities in groups.items()
            ],
        },
    }
