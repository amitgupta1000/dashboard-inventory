from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
import sqlalchemy

from backend.database import get_engine


router = APIRouter(prefix="/api/stock-analytics", tags=["stock-analytics"])


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

    if backdate is not None and backdate >= as_of:
        raise HTTPException(status_code=400, detail="backdate must be earlier than as_of")

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
            "cost_price_INR",
            "average_selling_price_INR",
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
    try:
        cfg_columns = {col["name"] for col in inspector.get_columns("commodity_daily_configs")}
    except Exception:
        cfg_columns = set()

    selectable_fields = [
        "desired_stock_level",
        "min_stock_level",
        "max_stock_level",
        "target_inventory_days",
        "target_storage_cap_days",
        "estimated_days_to_sale",
        "expected_gross_margin",
        "annual_cost_of_capital_rate",
    ]

    forced_missing: set[str] = set()

    def cfg_col_expr(name: str) -> str:
        if name in forced_missing:
            return f"NULL AS {name}"
        if cfg_columns and name in cfg_columns:
            return f"cfg.{name}"
        if not cfg_columns:
            return f"cfg.{name}"
        return f"NULL AS {name}"

    def build_query() -> sqlalchemy.sql.elements.TextClause:
        return sqlalchemy.text("""
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

    rows = []
    max_retries = len(selectable_fields)
    for _ in range(max_retries):
        query = build_query()
        try:
            with engine.connect() as conn:
                rows = conn.execute(query, {"as_of": as_of}).mappings().all()
            break
        except sqlalchemy.exc.OperationalError as exc:
            msg = str(exc).lower()
            marker = "no such column: cfg."
            if marker not in msg:
                raise
            missing_col = msg.split(marker, 1)[1].split()[0].strip().strip(",").strip("`").strip('"')
            if missing_col in forced_missing:
                raise
            forced_missing.add(missing_col)
    else:
        raise RuntimeError("Unable to load targets map due to repeated missing columns")

    return {
        _normalize_product_name(row["commodity_name"]): dict(row)
        for row in rows
    }


def _load_market_price_map(engine: sqlalchemy.Engine, as_of: date) -> dict[tuple[str, str], float]:
    """
    Load market price by (product_name, port) from market_data_hvb.
    Uses latest report_date <= as_of, else latest overall snapshot.
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
        return {}

    grouped: dict[tuple[str, str], list[float]] = {}
    for product_name, port, market_price in rows:
        price = _to_float(market_price)
        if price <= 0:
            continue
        key = (_normalize_key(product_name), _normalize_key(port))
        grouped.setdefault(key, []).append(price)

    result: dict[tuple[str, str], float] = {}
    for key, values in grouped.items():
        if values:
            result[key] = sum(values) / len(values)

    return result


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

    market_price = _to_float(row.get("market_price_inr"))
    cost_price = _to_float(row.get("cost_price_inr"))
    sell_price = _to_float(row.get("average_selling_price_inr"))
    if market_price > 0 and cost_price > 0:
        if market_price < cost_price:
            flags.append({
                "type": "market_below_cost",
                "severity": "critical",
                "message": f"Market price below cost ({market_price:.0f} < {cost_price:.0f})",
            })
        elif sell_price > 0 and market_price < sell_price:
            flags.append({
                "type": "market_below_sale",
                "severity": "warning",
                "message": f"Market price below avg sell ({market_price:.0f} < {sell_price:.0f})",
            })

    return flags, variance


def build_stock_analytics(
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
    market_price_map = _load_market_price_map(engine, as_of)

    search_key = (search or "").strip().lower()
    result_rows = []
    all_alerts = []

    for key, current in current_grouped.items():
        previous = previous_grouped.get(key)
        prev_physical = _to_float(previous.get("physical_stock")) if previous else 0.0
        delta_physical = _to_float(current.get("physical_stock")) - prev_physical

        market_key = (
            _normalize_key(current.get("product_name")),
            _normalize_key(current.get("port_name")),
        )
        market_price_inr = _to_float(market_price_map.get(market_key))
        current["market_price_inr"] = round(market_price_inr, 2) if market_price_inr > 0 else None

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
            "market_price_inr": current.get("market_price_inr"),
            "market_vs_cost_per_mt": (
                round(_to_float(current.get("market_price_inr")) - _to_float(current.get("cost_price_inr")), 2)
                if current.get("market_price_inr") is not None
                else None
            ),
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


@router.get('/dates')
async def get_stock_analytics_dates():
    engine = get_db_engine()
    dates = _get_stock_dates(engine)
    return {
        "success": True,
        "data": dates,
    }


@router.get('/summary')
async def get_stock_analytics_summary(
    as_of: str | None = None,
    backdate: str | None = None,
    search: str | None = None,
):
    engine = get_db_engine()
    analytics = build_stock_analytics(engine, as_of, backdate, search)
    return {
        "success": True,
        "as_of_date": analytics["as_of_date"],
        "backdate": analytics["backdate"],
        "available_dates": analytics["available_dates"],
        "summary": analytics["summary"],
        "data": analytics["rows"],
    }


@router.get('/drilldown')
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
