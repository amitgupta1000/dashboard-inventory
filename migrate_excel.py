"""
One-time migration: loads data from stock_report.xlsx into the inventory table.

Usage:
    set CLOUD_SQL_INSTANCE=my-project:us-central1:my-instance
    set DB_NAME=inventory
    set DB_USER=app_user
    set DB_PASS=secret
    python migrate_excel.py [path/to/stock_report.xlsx]
"""

import sys
import pandas as pd
import sqlalchemy
from backend.db import get_engine

EXCEL_PATH = sys.argv[1] if len(sys.argv) > 1 else "stock_report.xlsx"

COLUMN_MAP = [
    "company_name",
    "port_name",
    "product_name",
    "physical_stock",
    "total_sold_qty",
    "total_unsold_qty",
    "incoming_vessel_qty",
    "avg_import_price_usd",
    "avg_price_inr",
    "current_market_price",
    "replacement_cost",
    "stock_value",
]

NUMERIC_COLUMNS = COLUMN_MAP[3:]  # everything after the text columns


def load_excel(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, header=0)
    df.columns = COLUMN_MAP
    df = df[df["company_name"].notna()]
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def migrate(df: pd.DataFrame, engine: sqlalchemy.Engine) -> None:
    records = df.where(pd.notna(df), None).to_dict(orient="records")
    insert = sqlalchemy.text("""
        INSERT INTO inventory (
            company_name, port_name, product_name,
            physical_stock, total_sold_qty, total_unsold_qty,
            incoming_vessel_qty, avg_import_price_usd, avg_price_inr,
            current_market_price, replacement_cost, stock_value
        ) VALUES (
            :company_name, :port_name, :product_name,
            :physical_stock, :total_sold_qty, :total_unsold_qty,
            :incoming_vessel_qty, :avg_import_price_usd, :avg_price_inr,
            :current_market_price, :replacement_cost, :stock_value
        )
    """)
    with engine.begin() as conn:
        conn.execute(insert, records)
    print(f"Inserted {len(records)} rows into inventory.")


if __name__ == "__main__":
    print(f"Loading {EXCEL_PATH} ...")
    df = load_excel(EXCEL_PATH)
    print(f"  {len(df)} rows found.")
    engine = get_engine()
    migrate(df, engine)
