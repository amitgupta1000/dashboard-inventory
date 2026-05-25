"""
One-time migration: loads data from stock_report.xlsx into the inventory table.

Usage:
    python migrate_excel.py [path/to/stock_report.xlsx]

Expected Excel column order (left → right):
    Date, Item, Port, Company, Unit,
    Physical Stock, Ready/Unsold, Safety Stock, Reorder Point,
    Storage Cap (d), Cycle Days, Monthly Volume,
    Market Price, Selling Price, CIF+Duty, Purchase Price,
    Pending Lifting, Port Stock, Incoming Qty, Arrival Date
    (STATUS column is auto-computed — skip it)
"""

import sys
import pandas as pd
import sqlalchemy
from database import get_engine

EXCEL_PATH = sys.argv[1] if len(sys.argv) > 1 else "stock_report.xlsx"

COLUMN_MAP = [
    "record_date",
    "item",
    "port",
    "company",
    "unit",
    "physical_stock",
    "ready_unsold",
    "safety_stock",
    "reorder_point",
    "storage_cap_days",
    "cycle_days",
    "monthly_volume",
    "market_price",
    "selling_price",
    "cif_duty",
    "purchase_price",
    "pending_lifting",
    "port_stock",
    "incoming_qty",
    "arrival_date",
]

NUMERIC_COLUMNS = [
    "physical_stock", "ready_unsold", "safety_stock", "reorder_point",
    "storage_cap_days", "cycle_days", "monthly_volume",
    "market_price", "selling_price", "cif_duty", "purchase_price",
    "pending_lifting", "port_stock", "incoming_qty",
]

INSERT_SQL = sqlalchemy.text("""
    INSERT INTO inventory (
        record_date, item, port, company, unit,
        physical_stock, ready_unsold, safety_stock, reorder_point,
        storage_cap_days, cycle_days, monthly_volume,
        market_price, selling_price, cif_duty, purchase_price,
        pending_lifting, port_stock, incoming_qty, arrival_date
    ) VALUES (
        :record_date, :item, :port, :company, :unit,
        :physical_stock, :ready_unsold, :safety_stock, :reorder_point,
        :storage_cap_days, :cycle_days, :monthly_volume,
        :market_price, :selling_price, :cif_duty, :purchase_price,
        :pending_lifting, :port_stock, :incoming_qty, :arrival_date
    )
""")


def load_excel(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, header=0)
    # Drop STATUS column if present (it's auto-computed)
    df = df.iloc[:, : len(COLUMN_MAP)]
    df.columns = COLUMN_MAP
    df = df[df["item"].notna()]
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["record_date"] = pd.to_datetime(df["record_date"], dayfirst=True, errors="coerce").dt.date
    return df


def migrate(df: pd.DataFrame, engine: sqlalchemy.Engine) -> None:
    records = df.where(pd.notna(df), None).to_dict(orient="records")
    with engine.begin() as conn:
        conn.execute(INSERT_SQL, records)
    print(f"Inserted {len(records)} rows into inventory.")


if __name__ == "__main__":
    print(f"Loading {EXCEL_PATH} ...")
    df = load_excel(EXCEL_PATH)
    print(f"  {len(df)} rows found.")
    engine = get_engine()
    migrate(df, engine)
