from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sqlalchemy
from typing import List, Dict, Any

from backend.db import get_engine

app = FastAPI(title="Inventory Management API")

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


@app.get('/api/inventory')
async def get_inventory():
    """Get all inventory data"""
    engine = get_db_engine()
    query = sqlalchemy.text("""
        SELECT
            id, company_name, port_name, product_name,
            physical_stock, total_sold_qty, total_unsold_qty,
            incoming_vessel_qty, avg_import_price_usd, avg_price_inr,
            current_market_price, replacement_cost, stock_value
        FROM inventory
        ORDER BY company_name, product_name
    """)
    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()

    data = [dict(row) for row in rows]
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
            COUNT(*)                    AS total_products,
            COALESCE(SUM(physical_stock),   0) AS total_physical_stock,
            COALESCE(SUM(stock_value),      0) AS total_stock_value,
            COALESCE(SUM(total_sold_qty),   0) AS total_sold_qty,
            COALESCE(SUM(total_unsold_qty), 0) AS total_unsold_qty
        FROM inventory
    """)
    with engine.connect() as conn:
        row = conn.execute(query).mappings().one()

    summary = {k: float(v) for k, v in row.items()}
    return {
        'success': True,
        'summary': summary
    }


@app.get('/health')
async def health_check():
    """Health check endpoint"""
    return {'status': 'healthy'}


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
