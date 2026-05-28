import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend.database import get_engine
from sqlalchemy import text


def main() -> None:
    engine = get_engine()
    required_columns = {
        "incoming_period_1": "DOUBLE PRECISION",
        "incoming_period_2": "DOUBLE PRECISION",
        "monthly_volumes": "DOUBLE PRECISION",
        "pending_lifting": "DOUBLE PRECISION",
        "replac_dollar": "DOUBLE PRECISION",
        "replace": "DOUBLE PRECISION",
        "index": "DOUBLE PRECISION",
        "market_price": "DOUBLE PRECISION",
        "selling_p": "DOUBLE PRECISION",
        "current_month": "DOUBLE PRECISION",
        "next_month": "DOUBLE PRECISION",
        "arrival_date": "VARCHAR(100)",
        "product_name": "VARCHAR(255)",
        "port": "VARCHAR(100)",
        "usdinr_rate": "DOUBLE PRECISION",
        "created_at": "TIMESTAMP WITHOUT TIME ZONE",
    }

    with engine.begin() as conn:
        existing_cols = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'market_data_hvb'"
                )
            )
        }

        added = []
        for col_name, col_type in required_columns.items():
            if col_name not in existing_cols:
                conn.execute(text(f"ALTER TABLE market_data_hvb ADD COLUMN {col_name} {col_type}"))
                added.append(col_name)

    print(f"Added columns: {added}")


if __name__ == "__main__":
    main()
