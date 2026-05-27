"""Load vessel-level stock report CSV into the inventory_detail table.

The source file has a title row plus a header row. The important rule for this
dataset is that `no_of_days_of_stock` is derived, not trusted from the file:

    no_of_days_of_stock = report_date - vessel_date

`report_date` comes from the title row (e.g. `STOCK REPORT 22-05-2026`).
"""

from __future__ import annotations

import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import sessionmaker

import os

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

os.environ.setdefault("USE_SQLITE", "true")

from backend.database import Base, Commodity, InventoryDetail, get_engine


BASE_COLUMNS = [
    "vessel_date",
    "vessel_name",
    "product_name",
    "port_name",
    "unsold_qty",
    "sold_qty_pending_lifting",
    "physical_stock",
    "otr_qty",
    "company_terminal_name",
    "company_name",
    "file_reported_days_of_stock",
]

OPTIONAL_COLUMN_ALIASES = {
    "cost_price_INR": {
        "cost_price_mt_inr",
        "cost_price_inr",
        "cost_price",
    },
    "average_selling_price_INR": {
        "average_selling_price_mt_inr",
        "average_selling_price_inr",
        "average_selling_price",
    },
}


def normalize_column_name(name: str) -> str:
    cleaned = str(name).strip().lower().replace("\n", " ")
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
    return cleaned.strip("_")


def normalize_product_name(name: str | None) -> str:
    if not name:
        return ""
    return " ".join(str(name).upper().strip().split())


def build_commodity_name_map(session) -> dict[str, str]:
    """Return normalized commodity name -> canonical commodity_name from DB."""
    result = session.execute(select(Commodity).where(Commodity.is_active == True))
    commodities = result.scalars().all()
    return {
        normalize_product_name(c.commodity_name): c.commodity_name
        for c in commodities
        if c.commodity_name
    }


def parse_report_date(title_line: str) -> date:
    match = re.search(r"STOCK REPORT\s+(\d{1,2}-\d{1,2}-\d{4})", title_line.upper())
    if not match:
        raise ValueError(f"Could not parse report date from title: {title_line!r}")
    return datetime.strptime(match.group(1), "%d-%m-%Y").date()


def to_float(value) -> Optional[float]:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text_value = str(value).strip()
    if not text_value:
        return None
    try:
        return float(text_value)
    except ValueError:
        return None


def to_date(value) -> Optional[date]:
    if value is None or pd.isna(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce", dayfirst=False)
    if pd.isna(parsed):
        return None
    return parsed.date()


def read_stock_report(path: str) -> tuple[date, pd.DataFrame]:
    raw_lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    if not raw_lines:
        raise ValueError(f"Empty stock report: {path}")

    report_date = parse_report_date(raw_lines[0])

    source = pd.read_csv(path, header=1, encoding="utf-8-sig")

    if source.shape[1] < len(BASE_COLUMNS):
        raise ValueError(
            f"Unexpected stock report format. Expected at least {len(BASE_COLUMNS)} columns, "
            f"found {source.shape[1]}"
        )

    df = source.iloc[:, : len(BASE_COLUMNS)].copy()
    df.columns = BASE_COLUMNS

    normalized_source_columns = {
        normalize_column_name(col): col
        for col in source.columns
    }

    for target_field, aliases in OPTIONAL_COLUMN_ALIASES.items():
        matched_source_column = next(
            (normalized_source_columns[alias] for alias in aliases if alias in normalized_source_columns),
            None,
        )
        if matched_source_column is not None:
            df[target_field] = source[matched_source_column]
        else:
            df[target_field] = None

    for column in ["vessel_date", "product_name", "port_name", "company_terminal_name", "company_name"]:
        df[column] = df[column].astype(str).str.strip()

    return report_date, df


def ensure_inventory_detail_columns(engine) -> None:
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("inventory_detail")}

    ddl_statements = []
    if "company_name" not in columns:
        ddl_statements.append("ALTER TABLE inventory_detail ADD COLUMN company_name VARCHAR(255)")
    if "cost_price_INR" not in columns:
        ddl_statements.append("ALTER TABLE inventory_detail ADD COLUMN cost_price_INR NUMERIC(15, 4)")
    if "average_selling_price_INR" not in columns:
        ddl_statements.append("ALTER TABLE inventory_detail ADD COLUMN average_selling_price_INR NUMERIC(15, 4)")

    if not ddl_statements:
        return

    with engine.begin() as connection:
        for ddl in ddl_statements:
            connection.execute(text(ddl))


def upsert_stock_row(
    session,
    report_date: date,
    row: pd.Series,
    source_file_name: str,
    commodity_name_map: dict[str, str],
) -> str:
    vessel_date = to_date(row["vessel_date"])
    inventory_days = (report_date - vessel_date).days if vessel_date else None
    product_name_raw = row["product_name"]
    normalized_name = normalize_product_name(product_name_raw)
    canonical_product_name = commodity_name_map.get(normalized_name, product_name_raw)

    key_query = select(InventoryDetail).where(
        InventoryDetail.date == report_date,
        InventoryDetail.vessel_name == row["vessel_name"],
        InventoryDetail.product_name == canonical_product_name,
        InventoryDetail.port_name == row["port_name"],
        InventoryDetail.company_terminal_name == row["company_terminal_name"],
        InventoryDetail.company_name == row["company_name"],
    )
    existing = session.execute(key_query).scalar_one_or_none()

    payload = {
        "date": report_date,
        "vessel_date": vessel_date,
        "vessel_name": row["vessel_name"] or None,
        "product_name": canonical_product_name or None,
        "port_name": row["port_name"] or None,
        "company_terminal_name": row["company_terminal_name"] or None,
        "company_name": row["company_name"] or None,
        "unsold_qty": to_float(row["unsold_qty"]),
        "sold_qty_pending_lifting": to_float(row["sold_qty_pending_lifting"]),
        "physical_stock": to_float(row["physical_stock"]),
        "otr_qty": to_float(row["otr_qty"]),
        "cost_price_INR": to_float(row["cost_price_INR"]),
        "average_selling_price_INR": to_float(row["average_selling_price_INR"]),
        "no_of_days_of_stock": inventory_days,
    }

    if existing:
        for field, value in payload.items():
            setattr(existing, field, value)
        session.add(existing)
        return "updated"

    session.add(InventoryDetail(**payload))
    return "inserted"


def load_stock_report(path: str) -> dict:
    report_date, df = read_stock_report(path)

    engine = get_engine()
    Base.metadata.create_all(engine)
    ensure_inventory_detail_columns(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    inserted = 0
    updated = 0
    failed = 0

    try:
        commodity_name_map = build_commodity_name_map(session)

        for _, row in df.iterrows():
            try:
                action = upsert_stock_row(
                    session,
                    report_date,
                    row,
                    Path(path).name,
                    commodity_name_map,
                )
                if action == "inserted":
                    inserted += 1
                else:
                    updated += 1
            except Exception:
                failed += 1

        session.commit()
        return {
            "report_date": report_date.isoformat(),
            "inserted": inserted,
            "updated": updated,
            "failed": failed,
            "source_file": Path(path).name,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    default_path = Path("data_files/stock_report.csv")
    result = load_stock_report(str(default_path))
    print(result)