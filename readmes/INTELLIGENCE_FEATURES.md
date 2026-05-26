# Intelligence & Trading Analytics Features

## Overview
The dashboard intelligence layer is generated from Python analytics over trading positions in `inventory_detail`, with operating target overlays from `commodity_daily_configs` and `commodities`.

There are no required SQL intelligence views in the active architecture.

## Active Data Flow
1. Trade-book position rows are loaded into `inventory_detail`.
2. `no_of_days_of_stock` is treated as a derived field: `report_date - vessel_date`.
3. Operating targets are read from `commodity_daily_configs` (latest by commodity/date).
4. Backend analytics compute lane summary, vessel drilldown, risk alerts, and executive narrative in `main.py`.

## API Endpoints

### Trading Analytics Endpoints
```
GET /api/stock-analytics/dates
- Returns available as-of dates from inventory_detail

GET /api/stock-analytics/summary
- Returns grouped trading analytics (Product + Port + Company)
- Supports as_of, backdate, and search parameters

GET /api/stock-analytics/drilldown
- Returns vessel-level drilldown for a selected grouped key
```

### Intelligence Endpoints (Derived from Trading Analytics)
```
GET /api/intelligence/alerts
- Returns prioritized trading-risk alert cards from computed analytics

GET /api/intelligence/narrative
- Returns executive narrative generated from computed analytics
```

## Frontend Notes
The main analytics UX is integrated in `frontend/src/App.tsx`.
It supports:
- As-of date and backdate comparison
- Searchable grouped summary rows
- Vessel drilldown panel
- Cost/selling/margin visibility where pricing is available

## Database Setup

Run these SQL scripts in order:
1. `schema_product_settings.sql` (legacy support if used)
2. `schema_inventory_dashboard.sql` (legacy support if used)
3. `schema_stock_analytics_bootstrap.sql` (current stock analytics schema)

If you run only the current analytics stack, the required script is:
- `schema_stock_analytics_bootstrap.sql`

## Legacy Notes
- `schema_intelligence_views.sql` was removed as obsolete.
- Intelligence views/functions based on the old inventory pipeline are no longer used by runtime endpoints.
