import os, sys
from pathlib import Path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # Ensure current directory is
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

# Load .env from backend/ directory FIRST - before any other imports
env_path = Path(__file__).parent / 'backend' / '.env'
load_dotenv(env_path, override=True)

# DB mode is controlled via USE_SQLITE in environment.
# For Cloud SQL migration set USE_SQLITE=false and provide CLOUD_SQL_* vars.

# GCS credentials can be configured via:
# 1. GOOGLE_APPLICATION_CREDENTIALS env var (path to service account JSON)
# 2. gcloud CLI default credentials (from 'gcloud auth application-default login')
# 3. Cloud Run service account (in production)
# We do NOT remove GOOGLE_APPLICATION_CREDENTIALS - let it work if configured

# Now we can safely import
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sqlalchemy
from datetime import datetime
from typing import Dict, Any

from backend.database import get_engine
from backend.routes.inventory import router as inventory_router
from backend.routes.uploads import router as uploads_router
from backend.routes.targets import router as targets_router
from backend.routes.market_data import router as market_data_router
from backend.routes.stock_analytics import (
    router as stock_analytics_router,
    build_stock_analytics,
)
from backend.routes.analytics_layer1 import router as analytics_layer1_router

app = FastAPI(title="Inventory Management API")
app.include_router(inventory_router)
app.include_router(uploads_router)
app.include_router(targets_router)
app.include_router(market_data_router)
app.include_router(stock_analytics_router)
app.include_router(analytics_layer1_router)

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
    analytics = build_stock_analytics(engine, as_of, backdate)
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
    analytics = build_stock_analytics(engine, as_of, backdate)
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
