import os, sys
from pathlib import Path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # Ensure current directory is
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

# Load .env from backend/ directory FIRST - before any other imports
env_path = Path(__file__).parent / 'backend' / '.env'
load_dotenv(env_path, override=True)

# Now set USE_SQLITE to true for local development
os.environ.setdefault('USE_SQLITE', 'true')

# Remove service-account key override for local development
os.environ.pop('GOOGLE_APPLICATION_CREDENTIALS', None)

# Now we can safely import
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sqlalchemy
import io
import pandas as pd
from collections import defaultdict
from datetime import datetime, date
from typing import List, Dict, Any

from backend.database import get_engine
from backend import gcs
from backend.routes.inventory import router as inventory_router
from backend.routes.uploads import router as uploads_router
from backend.routes.targets import router as targets_router
from backend.routes.market_data import router as market_data_router

app = FastAPI(title="Inventory Management API")
app.include_router(inventory_router)
app.include_router(uploads_router)
app.include_router(targets_router)
app.include_router(market_data_router)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single engine instance shared across requests
_engine: sqlalchemy.Engine | None = None

def get_db_engine() -> sqlalchemy.Engine:
    global _engine
    if _engine is None:
        _engine = get_engine()
    return _engine


def _normalize_product_name(name: str | None) -> str:
    if not name:
        return ""
    return " ".join(name.upper().strip().split())


def _parse_iso_date(raw: str | None) -> date | None:
    if not raw:
        return None
    return datetime.strptime(raw, "%Y-%m-%d").date()


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0


def _get_stock_dates(engine: sqlalchemy.Engine) -> list[str]:
    query = sqlalchemy.text("""
        SELECT DISTINCT date
        FROM inventory_detail
        WHERE date IS NOT NULL
        ORDER BY date DESC
    """)
    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()
    return [str(r[0]) for r in rows]


def _resolve_dates(
    engine: sqlalchemy.Engine,
    as_of_raw: str | None,
    backdate_raw: str | None,
) -> tuple[date, date | None, list[str]]:
    available_dates = _get_stock_dates(engine)
    if not available_dates:
        raise HTTPException(status_code=404, detail="No stock report data found")

    as_of = _parse_iso_date(as_of_raw) if as_of_raw else datetime.strptime(available_dates[0], "%Y-%m-%d").date()

    if backdate_raw:
        backdate = _parse_iso_date(backdate_raw)
    else:
        backdate = None
        for raw_date in available_dates:
            d = datetime.strptime(raw_date, "%Y-%m-%d").date()
            if d < as_of:
                backdate = d
                break

    return as_of, backdate, available_dates


def _load_stock_rows_for_date(engine: sqlalchemy.Engine, target_date: date | None) -> list[dict]:
    if target_date is None:
        return []

    query = sqlalchemy.text("""
        SELECT
            date,
            vessel_date,
            vessel_name,
            product_name,
            port_name,
            company_terminal_name,
            company_name,
            unsold_qty,
            sold_qty_pending_lifting,
            physical_stock,
            otr_qty,
            cost_price_INR,
            average_selling_price_INR,
            no_of_days_of_stock
        FROM inventory_detail
        WHERE date = :target_date
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"target_date": target_date}).mappings().all()
    return [dict(r) for r in rows]


def _aggregate_stock(rows: list[dict]) -> dict:
    grouped: dict[tuple[str, str, str], dict] = {}

    for row in rows:
        key = (
            str(row.get("product_name") or "").strip(),
            str(row.get("port_name") or "").strip(),
            str(row.get("company_name") or "").strip(),
        )

        if key not in grouped:
            grouped[key] = {
                "product_name": key[0],
                "port_name": key[1],
                "company_name": key[2],
                "physical_stock": 0.0,
                "unsold_qty": 0.0,
                "sold_qty_pending_lifting": 0.0,
                "otr_qty": 0.0,
                "inventory_days_sum": 0.0,
                "inventory_days_count": 0,
                "weighted_cost_sum": 0.0,
                "weighted_selling_sum": 0.0,
                "price_weight": 0.0,
                "vessel_count": 0,
            }

        agg = grouped[key]
        physical = _to_float(row.get("physical_stock"))
        unsold = _to_float(row.get("unsold_qty"))
        sold_pending = _to_float(row.get("sold_qty_pending_lifting"))
        otr = _to_float(row.get("otr_qty"))
        inventory_days = row.get("no_of_days_of_stock")
        cost_price = _to_float(row.get("cost_price_INR"))
        selling_price = _to_float(row.get("average_selling_price_INR"))

        agg["physical_stock"] += physical
        agg["unsold_qty"] += unsold
        agg["sold_qty_pending_lifting"] += sold_pending
        agg["otr_qty"] += otr
        agg["vessel_count"] += 1

        if inventory_days is not None:
            agg["inventory_days_sum"] += _to_float(inventory_days)
            agg["inventory_days_count"] += 1

        if physical > 0:
            agg["weighted_cost_sum"] += physical * cost_price
            agg["weighted_selling_sum"] += physical * selling_price
            agg["price_weight"] += physical

    final: dict[tuple[str, str, str], dict] = {}
    for key, agg in grouped.items():
        weight = agg["price_weight"] if agg["price_weight"] > 0 else 1.0
        avg_cost = agg["weighted_cost_sum"] / weight
        avg_sell = agg["weighted_selling_sum"] / weight
        avg_days = (
            agg["inventory_days_sum"] / agg["inventory_days_count"]
            if agg["inventory_days_count"] > 0
            else None
        )
        stock_value = agg["physical_stock"] * avg_cost

        final[key] = {
            "product_name": agg["product_name"],
            "port_name": agg["port_name"],
            "company_name": agg["company_name"],
            "physical_stock": round(agg["physical_stock"], 3),
            "unsold_qty": round(agg["unsold_qty"], 3),
            "sold_qty_pending_lifting": round(agg["sold_qty_pending_lifting"], 3),
            "otr_qty": round(agg["otr_qty"], 3),
            "inventory_days": round(avg_days, 2) if avg_days is not None else None,
            "cost_price_inr": round(avg_cost, 2),
            "average_selling_price_inr": round(avg_sell, 2),
            "margin_per_mt_inr": round(avg_sell - avg_cost, 2),
            "stock_value": round(stock_value, 2),
            "vessel_count": agg["vessel_count"],
        }

    return final


def _load_latest_targets_map(engine: sqlalchemy.Engine, as_of: date) -> dict[str, dict]:
    inspector = sqlalchemy.inspect(engine)
    cfg_columns = {col["name"] for col in inspector.get_columns("commodity_daily_configs")}

    def cfg_col_expr(name: str) -> str:
        if name in cfg_columns:
            return f"cfg.{name}"
        return f"NULL AS {name}"

    query = sqlalchemy.text("""
        SELECT
            c.commodity_name,
            {desired_stock_level},
            {min_stock_level},
            {max_stock_level},
            {target_inventory_days},
            {target_storage_cap_days},
            {estimated_days_to_sale},
            {expected_gross_margin},
            {annual_cost_of_capital_rate}
        FROM commodity_daily_configs cfg
        JOIN commodities c ON c.id = cfg.commodity_id
        WHERE cfg.config_date = (
            SELECT MAX(cfg2.config_date)
            FROM commodity_daily_configs cfg2
            WHERE cfg2.commodity_id = cfg.commodity_id
              AND cfg2.config_date <= :as_of
        )
    """.format(
        desired_stock_level=cfg_col_expr("desired_stock_level"),
        min_stock_level=cfg_col_expr("min_stock_level"),
        max_stock_level=cfg_col_expr("max_stock_level"),
        target_inventory_days=cfg_col_expr("target_inventory_days"),
        target_storage_cap_days=cfg_col_expr("target_storage_cap_days"),
        estimated_days_to_sale=cfg_col_expr("estimated_days_to_sale"),
        expected_gross_margin=cfg_col_expr("expected_gross_margin"),
        annual_cost_of_capital_rate=cfg_col_expr("annual_cost_of_capital_rate"),
    ))

    with engine.connect() as conn:
        rows = conn.execute(query, {"as_of": as_of}).mappings().all()

    return {
        _normalize_product_name(row["commodity_name"]): dict(row)
        for row in rows
    }


def _severity_rank(severity: str) -> int:
    if severity == "critical":
        return 3
    if severity == "warning":
        return 2
    return 1


def _build_flags_and_variance(row: dict, target: dict | None) -> tuple[list[dict], dict]:
    flags: list[dict] = []
    variance = {
        "vs_desired_stock": None,
        "vs_min_stock": None,
        "vs_target_inventory_days": None,
    }

    if not target:
        return flags, variance

    physical = _to_float(row.get("physical_stock"))
    inventory_days = row.get("inventory_days")
    desired = target.get("desired_stock_level")
    minimum = target.get("min_stock_level")
    target_days = target.get("target_inventory_days")
    storage_cap = target.get("target_storage_cap_days")
    days_to_sale = target.get("estimated_days_to_sale")

    if desired is not None:
        variance["vs_desired_stock"] = round(physical - _to_float(desired), 3)
    if minimum is not None:
        variance["vs_min_stock"] = round(physical - _to_float(minimum), 3)
    if target_days is not None and inventory_days is not None:
        variance["vs_target_inventory_days"] = round(_to_float(inventory_days) - _to_float(target_days), 2)

    if minimum is not None and physical < _to_float(minimum):
        flags.append({
            "type": "critical_low_stock",
            "severity": "critical",
            "message": f"Open position below minimum operating cover ({physical:.1f} < {_to_float(minimum):.1f})",
        })
    elif desired is not None and physical < _to_float(desired):
        flags.append({
            "type": "below_target_stock",
            "severity": "warning",
            "message": f"Open position below desired trading cover ({physical:.1f} < {_to_float(desired):.1f})",
        })

    if storage_cap is not None and inventory_days is not None and _to_float(inventory_days) > _to_float(storage_cap):
        flags.append({
            "type": "storage_cap_breach",
            "severity": "critical",
            "message": f"Holding period exceeds storage cap ({_to_float(inventory_days):.1f} > {_to_float(storage_cap):.1f})",
        })
    elif target_days is not None and inventory_days is not None and _to_float(inventory_days) > _to_float(target_days):
        flags.append({
            "type": "high_inventory_days",
            "severity": "warning",
            "message": f"Holding period above target ({_to_float(inventory_days):.1f} > {_to_float(target_days):.1f})",
        })

    if days_to_sale is not None and inventory_days is not None and _to_float(inventory_days) > _to_float(days_to_sale):
        flags.append({
            "type": "aging_inventory",
            "severity": "warning",
            "message": f"Position aging beyond expected realization window ({_to_float(inventory_days):.1f} days)",
        })

    if _to_float(row.get("margin_per_mt_inr")) < 0:
        flags.append({
            "type": "negative_margin",
            "severity": "critical",
            "message": "Average selling price is below cost price",
        })

    return flags, variance


def _build_stock_analytics(
    engine: sqlalchemy.Engine,
    as_of_raw: str | None,
    backdate_raw: str | None,
    search: str | None = None,
) -> dict:
    as_of, backdate, available_dates = _resolve_dates(engine, as_of_raw, backdate_raw)
    current_rows = _load_stock_rows_for_date(engine, as_of)
    previous_rows = _load_stock_rows_for_date(engine, backdate)

    current_grouped = _aggregate_stock(current_rows)
    previous_grouped = _aggregate_stock(previous_rows)
    target_map = _load_latest_targets_map(engine, as_of)

    search_key = (search or "").strip().lower()
    result_rows = []
    all_alerts = []

    for key, current in current_grouped.items():
        previous = previous_grouped.get(key)
        prev_physical = _to_float(previous.get("physical_stock")) if previous else 0.0
        delta_physical = _to_float(current.get("physical_stock")) - prev_physical

        target = target_map.get(_normalize_product_name(current.get("product_name")))
        flags, variance = _build_flags_and_variance(current, target)

        if previous and prev_physical > 0 and delta_physical < 0:
            drop_pct = abs(delta_physical) / prev_physical
            if drop_pct >= 0.2:
                flags.append({
                    "type": "rapid_stock_drop",
                    "severity": "warning",
                    "message": f"Open position reduced {drop_pct * 100:.1f}% vs backdate",
                })

        severity = "ok"
        if any(flag["severity"] == "critical" for flag in flags):
            severity = "critical"
        elif flags:
            severity = "warning"

        row = {
            **current,
            "as_of_date": str(as_of),
            "backdate": str(backdate) if backdate else None,
            "delta_physical_stock": round(delta_physical, 3),
            "delta_unsold_qty": round(
                _to_float(current.get("unsold_qty")) - _to_float(previous.get("unsold_qty") if previous else 0),
                3,
            ),
            "delta_sold_qty_pending": round(
                _to_float(current.get("sold_qty_pending_lifting")) - _to_float(previous.get("sold_qty_pending_lifting") if previous else 0),
                3,
            ),
            "delta_otr_qty": round(
                _to_float(current.get("otr_qty")) - _to_float(previous.get("otr_qty") if previous else 0),
                3,
            ),
            "delta_inventory_days": (
                round(_to_float(current.get("inventory_days")) - _to_float(previous.get("inventory_days")), 2)
                if previous and current.get("inventory_days") is not None and previous.get("inventory_days") is not None
                else None
            ),
            "target": target,
            "target_variance": variance,
            "alert_flags": flags,
            "alert_level": severity,
        }

        if search_key:
            composite = f"{row['product_name']} {row['port_name']} {row['company_name']}".lower()
            if search_key not in composite:
                continue

        result_rows.append(row)

        for flag in flags:
            all_alerts.append({
                "item_name": row["product_name"],
                "port_name": row["port_name"],
                "company_name": row["company_name"],
                "alert_type": flag["type"],
                "alert_message": flag["message"],
                "severity": flag["severity"],
            })

    result_rows.sort(
        key=lambda r: (
            _severity_rank(r.get("alert_level", "ok")),
            abs(_to_float(r.get("delta_physical_stock"))),
            _to_float(r.get("stock_value")),
        ),
        reverse=True,
    )

    all_alerts.sort(
        key=lambda a: (_severity_rank(a.get("severity", "ok")), a.get("item_name") or ""),
        reverse=True,
    )

    summary = {
        "total_products": len(result_rows),
        "total_physical_stock": round(sum(_to_float(r.get("physical_stock")) for r in result_rows), 3),
        "total_sold_qty": round(sum(_to_float(r.get("sold_qty_pending_lifting")) for r in result_rows), 3),
        "total_stock_value": round(sum(_to_float(r.get("stock_value")) for r in result_rows), 2),
        "critical_count": sum(1 for r in result_rows if r.get("alert_level") == "critical"),
        "warning_count": sum(1 for r in result_rows if r.get("alert_level") == "warning"),
        "ok_count": sum(1 for r in result_rows if r.get("alert_level") == "ok"),
    }

    return {
        "as_of_date": str(as_of),
        "backdate": str(backdate) if backdate else None,
        "available_dates": available_dates,
        "rows": result_rows,
        "alerts": all_alerts,
        "summary": summary,
    }


@app.get('/api/stock-analytics/dates')
async def get_stock_analytics_dates():
    engine = get_db_engine()
    dates = _get_stock_dates(engine)
    return {
        "success": True,
        "data": dates,
    }


@app.get('/api/stock-analytics/summary')
async def get_stock_analytics_summary(
    as_of: str | None = None,
    backdate: str | None = None,
    search: str | None = None,
):
    engine = get_db_engine()
    analytics = _build_stock_analytics(engine, as_of, backdate, search)
    return {
        "success": True,
        "as_of_date": analytics["as_of_date"],
        "backdate": analytics["backdate"],
        "available_dates": analytics["available_dates"],
        "summary": analytics["summary"],
        "data": analytics["rows"],
    }


@app.get('/api/stock-analytics/drilldown')
async def get_stock_analytics_drilldown(
    product_name: str,
    port_name: str,
    company_name: str,
    as_of: str | None = None,
    backdate: str | None = None,
):
    engine = get_db_engine()
    as_of_date, backdate_date, _ = _resolve_dates(engine, as_of, backdate)
    current_rows = _load_stock_rows_for_date(engine, as_of_date)
    previous_rows = _load_stock_rows_for_date(engine, backdate_date)

    def _match(row: dict) -> bool:
        return (
            str(row.get("product_name") or "") == product_name
            and str(row.get("port_name") or "") == port_name
            and str(row.get("company_name") or "") == company_name
        )

    current_filtered = [r for r in current_rows if _match(r)]
    previous_filtered = [r for r in previous_rows if _match(r)]

    previous_by_vessel = {
        (
            str(r.get("vessel_name") or ""),
            str(r.get("vessel_date") or ""),
            str(r.get("company_terminal_name") or ""),
        ): r
        for r in previous_filtered
    }

    vessel_rows = []
    for row in current_filtered:
        vessel_key = (
            str(row.get("vessel_name") or ""),
            str(row.get("vessel_date") or ""),
            str(row.get("company_terminal_name") or ""),
        )
        prev = previous_by_vessel.get(vessel_key)

        vessel_rows.append({
            "vessel_name": row.get("vessel_name"),
            "vessel_date": str(row.get("vessel_date")) if row.get("vessel_date") else None,
            "terminal": row.get("company_terminal_name"),
            "physical_stock": _to_float(row.get("physical_stock")),
            "unsold_qty": _to_float(row.get("unsold_qty")),
            "sold_qty_pending_lifting": _to_float(row.get("sold_qty_pending_lifting")),
            "otr_qty": _to_float(row.get("otr_qty")),
            "inventory_days": _to_float(row.get("no_of_days_of_stock")),
            "cost_price_inr": _to_float(row.get("cost_price_INR")),
            "average_selling_price_inr": _to_float(row.get("average_selling_price_INR")),
            "margin_per_mt_inr": _to_float(row.get("average_selling_price_INR")) - _to_float(row.get("cost_price_INR")),
            "delta_physical_stock": _to_float(row.get("physical_stock")) - _to_float(prev.get("physical_stock") if prev else 0),
            "delta_unsold_qty": _to_float(row.get("unsold_qty")) - _to_float(prev.get("unsold_qty") if prev else 0),
        })

    return {
        "success": True,
        "as_of_date": str(as_of_date),
        "backdate": str(backdate_date) if backdate_date else None,
        "product_name": product_name,
        "port_name": port_name,
        "company_name": company_name,
        "data": vessel_rows,
    }


@app.get('/api/inventory')
async def get_inventory():
    """Get all inventory data"""
    engine = get_db_engine()
    query = sqlalchemy.text("""
        SELECT
            id, record_date, item, port, company, unit,
            physical_stock, ready_unsold, safety_stock, reorder_point,
            storage_cap_days, cycle_days, monthly_volume,
            market_price, selling_price, cif_duty, purchase_price,
            pending_lifting, port_stock, incoming_qty, arrival_date,
            status
        FROM inventory
        ORDER BY company, item
    """)
    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()

    data = [
        {k: (str(v) if hasattr(v, 'isoformat') else v) for k, v in row.items()}
        for row in rows
    ]
    return {
        'success': True,
        'data': data,
        'total': len(data)
    }


@app.get('/api/inventory/summary')
async def get_summary():
    """Get inventory summary statistics"""
    engine = get_db_engine()
    query = sqlalchemy.text("""
        SELECT
            COUNT(*)                              AS total_items,
            COALESCE(SUM(physical_stock),   0)    AS total_physical_stock,
            COALESCE(SUM(ready_unsold),     0)    AS total_ready_unsold,
            COALESCE(SUM(incoming_qty),     0)    AS total_incoming_qty,
            COUNT(*) FILTER (WHERE status = 'CRITICAL') AS critical_count,
            COUNT(*) FILTER (WHERE status = 'WARNING')  AS warning_count,
            COUNT(*) FILTER (WHERE status = 'OK')       AS ok_count
        FROM inventory
    """)
    with engine.connect() as conn:
        row = conn.execute(query).mappings().one()

    summary = {k: float(v) if v is not None else 0 for k, v in row.items()}
    return {
        'success': True,
        'summary': summary
    }


@app.post('/api/upload')
async def upload_file(file: UploadFile = File(...)):
    """Upload an Excel file to GCS."""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail='Only .xlsx / .xls files are accepted')

    contents = await file.read()
    gcs_path = gcs.upload_file(contents, file.filename)
    return {'success': True, 'gcs_path': gcs_path, 'filename': file.filename}


@app.post('/api/refresh')
async def refresh_inventory():
    """Detect new GCS files and import them into the inventory table."""
    engine = get_db_engine()

    # All files currently in GCS
    all_files = gcs.list_uploaded_files()
    if not all_files:
        return {'success': True, 'message': 'No files in GCS', 'imported': []}

    # Files already processed
    with engine.connect() as conn:
        rows = conn.execute(sqlalchemy.text('SELECT gcs_path FROM processed_files')).fetchall()
    already_done = {r[0] for r in rows}

    new_files = [f for f in all_files if f['gcs_path'] not in already_done]
    if not new_files:
        return {'success': True, 'message': 'No new files to process', 'imported': []}

    imported = []
    for file_info in new_files:
        raw = gcs.download_file(file_info['gcs_path'])
        df = _parse_excel(raw)
        rows_inserted = _insert_inventory(df, engine)
        _record_processed(file_info, rows_inserted, engine)
        imported.append({'gcs_path': file_info['gcs_path'], 'rows': rows_inserted})

    return {'success': True, 'imported': imported}


@app.get('/api/files')
async def list_files():
    """List all GCS upload files with their processing status."""
    engine = get_db_engine()
    all_files = gcs.list_uploaded_files()

    with engine.connect() as conn:
        rows = conn.execute(
            sqlalchemy.text('SELECT gcs_path, rows_imported, processed_at FROM processed_files')
        ).mappings().all()
    processed = {r['gcs_path']: dict(r) for r in rows}

    result = []
    for f in all_files:
        p = processed.get(f['gcs_path'])
        result.append({
            **f,
            'processed': p is not None,
            'rows_imported': p['rows_imported'] if p else None,
            'processed_at': str(p['processed_at']) if p else None,
        })
    return {'success': True, 'files': result}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

COLUMN_MAP = [
    'record_date', 'item', 'port', 'company', 'unit',
    'physical_stock', 'ready_unsold', 'safety_stock', 'reorder_point',
    'storage_cap_days', 'cycle_days', 'monthly_volume',
    'market_price', 'selling_price', 'cif_duty', 'purchase_price',
    'pending_lifting', 'port_stock', 'incoming_qty', 'arrival_date',
]

NUMERIC_COLS = [
    'physical_stock', 'ready_unsold', 'safety_stock', 'reorder_point',
    'storage_cap_days', 'cycle_days', 'monthly_volume',
    'market_price', 'selling_price', 'cif_duty', 'purchase_price',
    'pending_lifting', 'port_stock', 'incoming_qty',
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


def _parse_excel(raw: bytes) -> pd.DataFrame:
    df = pd.read_excel(io.BytesIO(raw), header=0)
    df = df.iloc[:, :len(COLUMN_MAP)]   # drop STATUS col if present
    df.columns = COLUMN_MAP
    df = df[df['item'].notna()]
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['record_date'] = pd.to_datetime(df['record_date'], dayfirst=True, errors='coerce').dt.date
    return df


def _insert_inventory(df: pd.DataFrame, engine: sqlalchemy.Engine) -> int:
    records = df.where(pd.notna(df), None).to_dict(orient='records')
    with engine.begin() as conn:
        conn.execute(INSERT_SQL, records)
    return len(records)


def _record_processed(file_info: dict, rows: int, engine: sqlalchemy.Engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            sqlalchemy.text(
                'INSERT INTO processed_files (gcs_path, filename, rows_imported) '
                'VALUES (:gcs_path, :filename, :rows)'
            ),
            {'gcs_path': file_info['gcs_path'], 'filename': file_info['filename'], 'rows': rows},
        )


@app.get('/api/product-settings')
async def get_product_settings():
    """Get all product settings"""
    engine = get_db_engine()
    query = sqlalchemy.text("""
        SELECT
            id, item, safety_stock, reorder_point,
            max_storage_days, max_inventory_days, monthly_target_volume,
            is_active, notes, updated_at
        FROM product_settings
        WHERE is_active = TRUE
        ORDER BY item
    """)
    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()

    data = [
        {k: (str(v) if hasattr(v, 'isoformat') else v) for k, v in row.items()}
        for row in rows
    ]
    return {
        'success': True,
        'data': data,
        'total': len(data)
    }


@app.get('/api/product-settings/{item_id}')
async def get_product_setting(item_id: int):
    """Get a single product setting by ID"""
    engine = get_db_engine()
    query = sqlalchemy.text("""
        SELECT
            id, item, safety_stock, reorder_point,
            max_storage_days, max_inventory_days, monthly_target_volume,
            is_active, notes, updated_at
        FROM product_settings
        WHERE id = :id
    """)
    with engine.connect() as conn:
        row = conn.execute(query, {'id': item_id}).mappings().first()
    
    if not row:
        raise HTTPException(status_code=404, detail='Product setting not found')
    
    data = {k: (str(v) if hasattr(v, 'isoformat') else v) for k, v in row.items()}
    return {'success': True, 'data': data}


@app.post('/api/product-settings')
async def create_product_setting(setting: Dict[str, Any]):
    """Create a new product setting"""
    engine = get_db_engine()
    
    required_fields = ['item']
    if not all(field in setting for field in required_fields):
        raise HTTPException(status_code=400, detail='Missing required field: item')
    
    insert_query = sqlalchemy.text("""
        INSERT INTO product_settings (
            item, safety_stock, reorder_point,
            max_storage_days, max_inventory_days, monthly_target_volume,
            notes
        ) VALUES (
            :item, :safety_stock, :reorder_point,
            :max_storage_days, :max_inventory_days, :monthly_target_volume,
            :notes
        )
        RETURNING id, item, safety_stock, reorder_point,
                  max_storage_days, max_inventory_days, monthly_target_volume,
                  is_active, notes, updated_at
    """)
    
    try:
        with engine.begin() as conn:
            row = conn.execute(insert_query, {
                'item': setting.get('item'),
                'safety_stock': setting.get('safety_stock'),
                'reorder_point': setting.get('reorder_point'),
                'max_storage_days': setting.get('max_storage_days'),
                'max_inventory_days': setting.get('max_inventory_days'),
                'monthly_target_volume': setting.get('monthly_target_volume'),
                'notes': setting.get('notes'),
            }).mappings().first()
        
        data = {k: (str(v) if hasattr(v, 'isoformat') else v) for k, v in row.items()}
        return {'success': True, 'data': data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put('/api/product-settings/{item_id}')
async def update_product_setting(item_id: int, setting: Dict[str, Any]):
    """Update an existing product setting"""
    engine = get_db_engine()
    
    update_query = sqlalchemy.text("""
        UPDATE product_settings
        SET
            item = COALESCE(:item, item),
            safety_stock = :safety_stock,
            reorder_point = :reorder_point,
            max_storage_days = :max_storage_days,
            max_inventory_days = :max_inventory_days,
            monthly_target_volume = :monthly_target_volume,
            notes = :notes
        WHERE id = :id
        RETURNING id, item, safety_stock, reorder_point,
                  max_storage_days, max_inventory_days, monthly_target_volume,
                  is_active, notes, updated_at
    """)
    
    try:
        with engine.begin() as conn:
            row = conn.execute(update_query, {
                'id': item_id,
                'item': setting.get('item'),
                'safety_stock': setting.get('safety_stock'),
                'reorder_point': setting.get('reorder_point'),
                'max_storage_days': setting.get('max_storage_days'),
                'max_inventory_days': setting.get('max_inventory_days'),
                'monthly_target_volume': setting.get('monthly_target_volume'),
                'notes': setting.get('notes'),
            }).mappings().first()
        
        if not row:
            raise HTTPException(status_code=404, detail='Product setting not found')
        
        data = {k: (str(v) if hasattr(v, 'isoformat') else v) for k, v in row.items()}
        return {'success': True, 'data': data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete('/api/product-settings/{item_id}')
async def delete_product_setting(item_id: int):
    """Soft delete a product setting (set is_active to false)"""
    engine = get_db_engine()
    
    delete_query = sqlalchemy.text("""
        UPDATE product_settings
        SET is_active = FALSE
        WHERE id = :id
        RETURNING id
    """)
    
    with engine.begin() as conn:
        row = conn.execute(delete_query, {'id': item_id}).first()
    
    if not row:
        raise HTTPException(status_code=404, detail='Product setting not found')
    
    return {'success': True, 'message': 'Product setting deleted'}


@app.get('/api/intelligence/insights')
async def get_intelligence_insights():
    """Get intelligence insights for the dashboard"""
    engine = get_db_engine()
    query = sqlalchemy.text("""        
        SELECT
            id, item_name, insight_type, insight_message, severity, created_at
        FROM insights
        ORDER BY created_at DESC                    
    """)
    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()

    data = [
        {k: (str(v) if hasattr(v, 'isoformat') else (list(v) if isinstance(v, (list, tuple)) else v)) for k, v in row.items()}
        for row in rows
    ]
    
    return {
        'success': True,
        'data': data,
        'total': len(data)
    }




@app.get('/api/intelligence/alerts')
async def get_intelligence_alerts(
    as_of: str | None = None,
    backdate: str | None = None,
):
    """Get alert feed derived from stock analytics."""
    engine = get_db_engine()
    analytics = _build_stock_analytics(engine, as_of, backdate)
    alerts = analytics["alerts"][:20]

    response = []
    for idx, alert in enumerate(alerts, start=1):
        response.append({
            "id": idx,
            "item": alert["item_name"],
            "item_name": alert["item_name"],
            "port_name": alert["port_name"],
            "company_name": alert["company_name"],
            "alert_type": alert["alert_type"],
            "alert_message": alert["alert_message"],
            "severity": alert["severity"],
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })

    return {
        "success": True,
        "as_of_date": analytics["as_of_date"],
        "backdate": analytics["backdate"],
        "data": response,
    }


@app.get('/api/intelligence/narrative')
async def get_intelligence_narrative(
    as_of: str | None = None,
    backdate: str | None = None,
):
    """Get executive narrative reframed for trading operations."""
    engine = get_db_engine()
    analytics = _build_stock_analytics(engine, as_of, backdate)
    summary = analytics["summary"]

    overall_health = "STABLE"
    if summary["critical_count"] > 0:
        overall_health = "EXECUTION_RISK"
    elif summary["warning_count"] > 0:
        overall_health = "WATCHLIST"

    recommended_actions = []
    if summary["critical_count"] > 0:
        recommended_actions.append("Prioritize low-cover and negative-margin books for immediate trading intervention")
    if summary["warning_count"] > 0:
        recommended_actions.append("Review books with extended holding periods against target cycle and storage caps")
    if analytics["backdate"]:
        recommended_actions.append("Inspect books with sharp position changes versus selected backdate")
    recommended_actions.append("Use drill-down to review vessel-level pricing, aging, and realization path")

    narrative = {
        "overall_health": overall_health,
        "executive_summary": (
            f"As of {analytics['as_of_date']}, the trading book spans {summary['total_products']} grouped lanes "
            f"with net open position {summary['total_physical_stock']:.1f} MT and marked value "
            f"Rs {summary['total_stock_value']:.0f}."
        ),
        "critical_count": summary["critical_count"],
        "warning_count": summary["warning_count"],
        "normal_count": summary["ok_count"],
        "recommended_actions": recommended_actions,
        "as_of_date": analytics["as_of_date"],
        "backdate": analytics["backdate"],
    }

    return {
        "success": True,
        "data": narrative,
    }



@app.get('/health')
async def health_check():
    """Health check endpoint"""
    return {'status': 'healthy'}


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
