"""
Loads the FMCG AI Sales BI Demo dataset (backend/data/FMCG_AI_Sales_BI_Demo_Data.xlsx)
into backend/data/fmcg_sales.db (SQLite) — one table per sheet (skipping the
README sheet), column names/structure kept exactly as provided in the source
file since it's already well-designed for this purpose.

Run from backend/: python -m app.scripts.ingest_fmcg_excel
"""

from pathlib import Path

import pandas as pd
import sqlite3

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
XLSX_PATH = DATA_DIR / "FMCG_AI_Sales_BI_Demo_Data.xlsx"
DB_PATH = DATA_DIR / "fmcg_sales.db"

SKIP_SHEETS = {"README"}


def _table_name(sheet_name: str) -> str:
    return sheet_name.strip().lower()


def main():
    xl = pd.ExcelFile(XLSX_PATH)
    sheets = [s for s in xl.sheet_names if s not in SKIP_SHEETS]

    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)

    for sheet in sheets:
        df = xl.parse(sheet)
        # Normalize date-typed columns to plain YYYY-MM-DD strings for
        # consistent SQL comparisons (pandas reads Excel dates as datetime64).
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime("%Y-%m-%d")
        table = _table_name(sheet)
        df.to_sql(table, conn, index=False)
        print(f"{table}: {len(df)} rows, columns={list(df.columns)}")

    conn.commit()
    conn.close()
    print(f"Wrote {DB_PATH}")


if __name__ == "__main__":
    main()
