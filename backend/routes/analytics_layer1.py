"""
Layer 1 Analytics: Data Exploration and Summary Views

Provides:
1. Vessel-level details (raw inventory data by vessel)
2. Summary views aggregated by product, company, or port
"""

from datetime import date, datetime
from typing import Any, Literal
from fastapi import APIRouter, HTTPException, Query
import sqlalchemy

from backend.database import get_engine

router = APIRouter(prefix="/api/analytics", tags=["analytics-layer1"])

_engine: sqlalchemy.Engine | None = None


def get_db_engine() -> sqlalchemy.Engine:
    global _engine
    if _engine is None:
        _engine = get_engine()
    return _engine


def _parse_iso_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid date format '{raw}'. Use YYYY-MM-DD")


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0


def _normalize_key(value: Any) -> str:
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())


def _load_market_price_fallback_map(engine: sqlalchemy.Engine, as_of: date) -> dict[tuple[str, str], float]:
    """
    Load fallback market prices from market_data_hvb for the given as_of date.
    If no snapshot exists for as_of, uses latest available report_date <= as_of,
    else falls back to the latest overall snapshot.
    """
    try:
        with engine.connect() as conn:
            fallback_date_query = sqlalchemy.text("""
                SELECT MAX(report_date)
                FROM market_data_hvb
                WHERE report_date <= :as_of
            """)
            fallback_date = conn.execute(fallback_date_query, {"as_of": as_of}).scalar()

            if fallback_date is None:
                latest_date_query = sqlalchemy.text("""
                    SELECT MAX(report_date)
                    FROM market_data_hvb
                """)
                fallback_date = conn.execute(latest_date_query).scalar()

            if fallback_date is None:
                return {}

            rows_query = sqlalchemy.text("""
                SELECT
                    product_name,
                    port,
                    market_price
                FROM market_data_hvb
                WHERE report_date = :report_date
                  AND market_price IS NOT NULL
            """)
            rows = conn.execute(rows_query, {"report_date": fallback_date}).fetchall()
    except Exception:
        # If market table is unavailable, silently keep fallback map empty.
        return {}

    buckets: dict[tuple[str, str], list[float]] = {}
    for product_name, port, market_price in rows:
        price = _to_float(market_price)
        if price <= 0:
            continue
        key = (_normalize_key(product_name), _normalize_key(port))
        buckets.setdefault(key, []).append(price)

    result: dict[tuple[str, str], float] = {}
    for key, values in buckets.items():
        if values:
            result[key] = sum(values) / len(values)

    return result


def _get_stock_dates(engine: sqlalchemy.Engine) -> list[str]:
    """Get all distinct dates with stock data, sorted newest first."""
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
    """Resolve as_of and backdate to actual dates, with defaults."""
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

    if backdate is not None and backdate >= as_of:
        raise HTTPException(status_code=400, detail="backdate must be earlier than as_of")

    return as_of, backdate, available_dates


def _load_vessel_details(engine: sqlalchemy.Engine, target_date: date | None) -> list[dict]:
    """Load raw vessel-level inventory details for a specific date."""
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
            "cost_price_INR",
            "average_selling_price_INR",
            "market_price_INR",
            no_of_days_of_stock
        FROM inventory_detail
        WHERE date = :target_date
        ORDER BY vessel_name, product_name, company_name
    """)
    
    with engine.connect() as conn:
        rows = conn.execute(query, {"target_date": target_date}).fetchall()
    
    return [
        {
            "date": str(row[0]) if row[0] else None,
            "vessel_date": str(row[1]) if row[1] else None,
            "vessel_name": row[2],
            "product_name": row[3],
            "port_name": row[4],
            "terminal": row[5],
            "company_name": row[6],
            "unsold_qty": _to_float(row[7]),
            "sold_qty_pending_lifting": _to_float(row[8]),
            "physical_stock": _to_float(row[9]),
            "otr_qty": _to_float(row[10]),
            "cost_price_inr": _to_float(row[11]),
            "average_selling_price_inr": _to_float(row[12]),
            "market_price_inr": _to_float(row[13]),
            "inventory_days": _to_float(row[14]),
        }
        for row in rows
    ]


def _aggregate_by_product(details: list[dict], unsold_days_threshold: float) -> list[dict]:
    """Aggregate vessel-level details by product."""
    grouped: dict[str, dict] = {}
    
    for row in details:
        product = row["product_name"]
        if product not in grouped:
            grouped[product] = {
                "product_name": product,
                "physical_stock": 0,
                "unsold_qty": 0,
                "sold_qty_pending_lifting": 0,
                "otr_qty": 0,
                "weighted_cost_sum": 0,
                "weighted_selling_sum": 0,
                "price_weight": 0,
                "inventory_days_sum": 0,
                "inventory_days_count": 0,
                "vessel_count": 0,
                "company_count": 0,
                "port_count": 0,
                "vessel_names": set(),
            }
        
        agg = grouped[product]
        physical = _to_float(row["physical_stock"])
        agg["physical_stock"] += physical
        agg["unsold_qty"] += _to_float(row["unsold_qty"])
        agg["sold_qty_pending_lifting"] += _to_float(row["sold_qty_pending_lifting"])
        agg["otr_qty"] += _to_float(row["otr_qty"])
        
        cost = _to_float(row["cost_price_inr"])
        selling = _to_float(row["average_selling_price_inr"])
        agg["weighted_cost_sum"] += physical * cost
        agg["weighted_selling_sum"] += physical * selling
        agg["price_weight"] += physical
        
        if row["inventory_days"] is not None and _to_float(row.get("unsold_qty")) > unsold_days_threshold:
            agg["inventory_days_sum"] += _to_float(row["inventory_days"])
            agg["inventory_days_count"] += 1
        
        if row.get("vessel_name"):
            agg["vessel_names"].add(row["vessel_name"])
    
    result = []
    for product, agg in grouped.items():
        weight = agg["price_weight"] if agg["price_weight"] > 0 else 1.0
        avg_cost = agg["weighted_cost_sum"] / weight
        avg_sell = agg["weighted_selling_sum"] / weight
        avg_days = (
            agg["inventory_days_sum"] / agg["inventory_days_count"]
            if agg["inventory_days_count"] > 0
            else None
        )
        stock_value = agg["physical_stock"] * avg_cost
        
        result.append({
            "product_name": product,
            "physical_stock": round(agg["physical_stock"], 2),
            "unsold_qty": round(agg["unsold_qty"], 2),
            "sold_qty_pending_lifting": round(agg["sold_qty_pending_lifting"], 2),
            "otr_qty": round(agg["otr_qty"], 2),
            "inventory_days": round(avg_days, 2) if avg_days is not None else None,
            "cost_price_inr": round(avg_cost, 2),
            "average_selling_price_inr": round(avg_sell, 2),
            "margin_per_mt_inr": round(avg_sell - avg_cost, 2),
            "stock_value": round(stock_value, 2),
            "vessel_count": len(agg["vessel_names"]),
        })
    
    return sorted(result, key=lambda x: x["stock_value"], reverse=True)


def _aggregate_by_company(details: list[dict], unsold_days_threshold: float) -> list[dict]:
    """Aggregate vessel-level details by company."""
    grouped: dict[str, dict] = {}
    
    for row in details:
        company = row["company_name"]
        if company not in grouped:
            grouped[company] = {
                "company_name": company,
                "physical_stock": 0,
                "unsold_qty": 0,
                "sold_qty_pending_lifting": 0,
                "otr_qty": 0,
                "weighted_cost_sum": 0,
                "weighted_selling_sum": 0,
                "price_weight": 0,
                "inventory_days_sum": 0,
                "inventory_days_count": 0,
                "product_count": 0,
                "port_count": 0,
                "product_names": set(),
                "port_names": set(),
            }
        
        agg = grouped[company]
        physical = _to_float(row["physical_stock"])
        agg["physical_stock"] += physical
        agg["unsold_qty"] += _to_float(row["unsold_qty"])
        agg["sold_qty_pending_lifting"] += _to_float(row["sold_qty_pending_lifting"])
        agg["otr_qty"] += _to_float(row["otr_qty"])
        
        cost = _to_float(row["cost_price_inr"])
        selling = _to_float(row["average_selling_price_inr"])
        agg["weighted_cost_sum"] += physical * cost
        agg["weighted_selling_sum"] += physical * selling
        agg["price_weight"] += physical
        
        if row["inventory_days"] is not None and _to_float(row.get("unsold_qty")) > unsold_days_threshold:
            agg["inventory_days_sum"] += _to_float(row["inventory_days"])
            agg["inventory_days_count"] += 1

        if row.get("product_name"):
            agg["product_names"].add(row["product_name"])
        if row.get("port_name"):
            agg["port_names"].add(row["port_name"])
    
    result = []
    for company, agg in grouped.items():
        weight = agg["price_weight"] if agg["price_weight"] > 0 else 1.0
        avg_cost = agg["weighted_cost_sum"] / weight
        avg_sell = agg["weighted_selling_sum"] / weight
        avg_days = (
            agg["inventory_days_sum"] / agg["inventory_days_count"]
            if agg["inventory_days_count"] > 0
            else None
        )
        stock_value = agg["physical_stock"] * avg_cost
        
        result.append({
            "company_name": company,
            "physical_stock": round(agg["physical_stock"], 2),
            "unsold_qty": round(agg["unsold_qty"], 2),
            "sold_qty_pending_lifting": round(agg["sold_qty_pending_lifting"], 2),
            "otr_qty": round(agg["otr_qty"], 2),
            "inventory_days": round(avg_days, 2) if avg_days is not None else None,
            "cost_price_inr": round(avg_cost, 2),
            "average_selling_price_inr": round(avg_sell, 2),
            "margin_per_mt_inr": round(avg_sell - avg_cost, 2),
            "stock_value": round(stock_value, 2),
            "product_count": len(agg["product_names"]),
            "port_count": len(agg["port_names"]),
        })
    
    return sorted(result, key=lambda x: x["stock_value"], reverse=True)


def _aggregate_by_port(details: list[dict], unsold_days_threshold: float) -> list[dict]:
    """Aggregate vessel-level details by port."""
    grouped: dict[str, dict] = {}
    
    for row in details:
        port = row["port_name"]
        if port not in grouped:
            grouped[port] = {
                "port_name": port,
                "physical_stock": 0,
                "unsold_qty": 0,
                "sold_qty_pending_lifting": 0,
                "otr_qty": 0,
                "weighted_cost_sum": 0,
                "weighted_selling_sum": 0,
                "price_weight": 0,
                "inventory_days_sum": 0,
                "inventory_days_count": 0,
                "product_count": 0,
                "company_count": 0,
                "product_names": set(),
                "company_names": set(),
            }
        
        agg = grouped[port]
        physical = _to_float(row["physical_stock"])
        agg["physical_stock"] += physical
        agg["unsold_qty"] += _to_float(row["unsold_qty"])
        agg["sold_qty_pending_lifting"] += _to_float(row["sold_qty_pending_lifting"])
        agg["otr_qty"] += _to_float(row["otr_qty"])
        
        cost = _to_float(row["cost_price_inr"])
        selling = _to_float(row["average_selling_price_inr"])
        agg["weighted_cost_sum"] += physical * cost
        agg["weighted_selling_sum"] += physical * selling
        agg["price_weight"] += physical
        
        if row["inventory_days"] is not None and _to_float(row.get("unsold_qty")) > unsold_days_threshold:
            agg["inventory_days_sum"] += _to_float(row["inventory_days"])
            agg["inventory_days_count"] += 1

        if row.get("product_name"):
            agg["product_names"].add(row["product_name"])
        if row.get("company_name"):
            agg["company_names"].add(row["company_name"])
    
    result = []
    for port, agg in grouped.items():
        weight = agg["price_weight"] if agg["price_weight"] > 0 else 1.0
        avg_cost = agg["weighted_cost_sum"] / weight
        avg_sell = agg["weighted_selling_sum"] / weight
        avg_days = (
            agg["inventory_days_sum"] / agg["inventory_days_count"]
            if agg["inventory_days_count"] > 0
            else None
        )
        stock_value = agg["physical_stock"] * avg_cost
        
        result.append({
            "port_name": port,
            "physical_stock": round(agg["physical_stock"], 2),
            "unsold_qty": round(agg["unsold_qty"], 2),
            "sold_qty_pending_lifting": round(agg["sold_qty_pending_lifting"], 2),
            "otr_qty": round(agg["otr_qty"], 2),
            "inventory_days": round(avg_days, 2) if avg_days is not None else None,
            "cost_price_inr": round(avg_cost, 2),
            "average_selling_price_inr": round(avg_sell, 2),
            "margin_per_mt_inr": round(avg_sell - avg_cost, 2),
            "stock_value": round(stock_value, 2),
            "product_count": len(agg["product_names"]),
            "company_count": len(agg["company_names"]),
        })
    
    return sorted(result, key=lambda x: x["stock_value"], reverse=True)


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/dates")
async def get_available_dates():
    """Get all available stock data dates."""
    engine = get_db_engine()
    dates = _get_stock_dates(engine)
    return {
        "success": True,
        "available_dates": dates,
    }


@router.get("/vessel-detail")
async def get_vessel_inventory_detail(
    as_of: str | None = Query(None, description="Date in YYYY-MM-DD format"),
    backdate: str | None = Query(None, description="Compare to date in YYYY-MM-DD format"),
    unsold_days_threshold: float = Query(25.0, ge=0, description="Only calculate/show inventory days where unsold_qty > threshold"),
):
    """
    Get vessel-level inventory details.
    Shows raw data at vessel level with optional comparison to previous date.
    """
    engine = get_db_engine()
    as_of_date, backdate_date, available_dates = _resolve_dates(engine, as_of, backdate)
    market_fallback_map = _load_market_price_fallback_map(engine, as_of_date)
    
    current_details = _load_vessel_details(engine, as_of_date)
    previous_details = _load_vessel_details(engine, backdate_date)
    
    # Create dict for quick lookup of previous values
    previous_by_key: dict[tuple, dict] = {}
    for row in previous_details:
        key = (row["vessel_name"], row["product_name"], row["company_name"], row["port_name"])
        previous_by_key[key] = row
    
    # Enrich current details with deltas
    result = []
    for row in current_details:
        key = (row["vessel_name"], row["product_name"], row["company_name"], row["port_name"])
        prev = previous_by_key.get(key)
        
        enhanced = row.copy()

        stock_report_market_price = _to_float(row.get("market_price_inr"))
        fallback_key = (_normalize_key(row.get("product_name")), _normalize_key(row.get("port_name")))
        fallback_market_price = _to_float(market_fallback_map.get(fallback_key))
        avg_sale_price = _to_float(row.get("average_selling_price_inr"))

        if stock_report_market_price > 0:
            effective_market_price = stock_report_market_price
            market_price_source = "stock_report"
        elif fallback_market_price > 0:
            effective_market_price = fallback_market_price
            market_price_source = "market_table_fallback"
        else:
            effective_market_price = avg_sale_price
            market_price_source = "avg_sale_price_fallback"

        enhanced["effective_market_price_inr"] = round(effective_market_price, 6)
        enhanced["market_price_source"] = market_price_source
        enhanced["inventory_days"] = row["inventory_days"] if _to_float(row.get("unsold_qty")) > unsold_days_threshold else None

        if prev:
            enhanced["delta_physical_stock"] = round(row["physical_stock"] - prev["physical_stock"], 2)
            enhanced["delta_unsold_qty"] = round(row["unsold_qty"] - prev["unsold_qty"], 2)
        else:
            enhanced["delta_physical_stock"] = None
            enhanced["delta_unsold_qty"] = None
        
        result.append(enhanced)
    
    return {
        "success": True,
        "as_of_date": str(as_of_date),
        "backdate": str(backdate_date) if backdate_date else None,
        "available_dates": available_dates,
        "unsold_days_threshold": unsold_days_threshold,
        "data": result,
    }


@router.get("/summary")
async def get_summary_view(
    view_type: Literal["product", "company", "port"] = Query("product", description="Aggregation level"),
    as_of: str | None = Query(None, description="Date in YYYY-MM-DD format"),
    backdate: str | None = Query(None, description="Compare to date in YYYY-MM-DD format"),
    unsold_days_threshold: float = Query(25.0, ge=0, description="Only calculate inventory days where unsold_qty > threshold"),
):
    """
    Get aggregated inventory summary.
    
    view_type options:
    - product: Aggregated by product name
    - company: Aggregated by company name
    - port: Aggregated by port name
    
    Includes optional delta comparison to previous date.
    """
    engine = get_db_engine()
    as_of_date, backdate_date, available_dates = _resolve_dates(engine, as_of, backdate)
    
    current_details = _load_vessel_details(engine, as_of_date)
    
    # Aggregate based on view_type
    if view_type == "product":
        current_aggregated = _aggregate_by_product(current_details, unsold_days_threshold)
    elif view_type == "company":
        current_aggregated = _aggregate_by_company(current_details, unsold_days_threshold)
    elif view_type == "port":
        current_aggregated = _aggregate_by_port(current_details, unsold_days_threshold)
    else:
        raise HTTPException(status_code=400, detail="Invalid view_type")
    
    # If backdate provided, also aggregate previous data for deltas
    result = current_aggregated
    if backdate_date:
        previous_details = _load_vessel_details(engine, backdate_date)
        
        if view_type == "product":
            previous_aggregated = _aggregate_by_product(previous_details, unsold_days_threshold)
        elif view_type == "company":
            previous_aggregated = _aggregate_by_company(previous_details, unsold_days_threshold)
        else:  # port
            previous_aggregated = _aggregate_by_port(previous_details, unsold_days_threshold)
        
        # Create lookup dict
        prev_by_key: dict[str, dict] = {}
        if view_type == "product":
            prev_by_key = {row["product_name"]: row for row in previous_aggregated}
        elif view_type == "company":
            prev_by_key = {row["company_name"]: row for row in previous_aggregated}
        else:  # port
            prev_by_key = {row["port_name"]: row for row in previous_aggregated}
        
        # Add deltas
        for row in result:
            key = row.get("product_name" if view_type == "product" else "company_name" if view_type == "company" else "port_name")
            prev = prev_by_key.get(key)
            if prev:
                row["delta_physical_stock"] = round(row["physical_stock"] - prev["physical_stock"], 2)
            else:
                row["delta_physical_stock"] = None
    
    return {
        "success": True,
        "view_type": view_type,
        "as_of_date": str(as_of_date),
        "backdate": str(backdate_date) if backdate_date else None,
        "available_dates": available_dates,
        "unsold_days_threshold": unsold_days_threshold,
        "data": result,
    }
