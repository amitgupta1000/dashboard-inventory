from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sqlalchemy
import io
import pandas as pd
from typing import List, Dict, Any
from dotenv import load_dotenv
import os
from pathlib import Path

# Load .env from backend/ directory (robust to any cwd)
env_path = Path(__file__).parent / 'backend' / '.env'
load_dotenv(env_path, override=True)

# Remove service-account key override so the Cloud SQL connector
# uses Application Default Credentials (gcloud auth application-default login)
os.environ.pop('GOOGLE_APPLICATION_CREDENTIALS', None)

from backend.db import get_engine
from backend import gcs

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


# =========================================================================
# Intelligence & Analytics Endpoints
# =========================================================================

@app.get('/api/intelligence/summary')
async def get_intelligence_summary():
    """Get product-wise intelligence summary with threshold analysis"""
    engine = get_db_engine()
    query = sqlalchemy.text("""
        SELECT
            item, total_stock_all_locations, total_unsold_all_locations,
            total_incoming_all_locations, overall_avg_market_price,
            overall_avg_selling_price, overall_avg_purchase_price,
            safety_stock, reorder_point, max_storage_days,
            max_inventory_days, monthly_target_volume,
            days_of_stock_remaining, stock_status,
            shortage_qty, excess_qty, profit_margin_percent,
            target_fulfillment_percent, company_count, port_count
        FROM v_product_intelligence_summary
        ORDER BY 
            CASE stock_status
                WHEN 'CRITICAL' THEN 1
                WHEN 'WARNING' THEN 2
                WHEN 'EXCESS' THEN 3
                ELSE 4
            END,
            item
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


@app.get('/api/intelligence/shipments')
async def get_shipment_intelligence():
    """Get shipment-level intelligence with aging analysis"""
    engine = get_db_engine()
    query = sqlalchemy.text("""
        SELECT
            id, record_date, item, port, company,
            physical_stock, ready_unsold, incoming_qty, arrival_date,
            purchase_price, selling_price, market_price,
            system_status, safety_stock, reorder_point,
            max_storage_days, max_inventory_days, monthly_target_volume,
            days_in_stock, aging_status, days_to_deplete,
            price_variance_percent, recommended_action, risk_flags
        FROM v_shipment_intelligence
        ORDER BY 
            CASE recommended_action
                WHEN 'URGENT_REORDER' THEN 1
                WHEN 'LIQUIDATE_AGED_STOCK' THEN 2
                WHEN 'REORDER_RECOMMENDED' THEN 3
                WHEN 'REDUCE_PROCUREMENT' THEN 4
                ELSE 5
            END,
            record_date
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
async def get_critical_alerts():
    """Get prioritized critical alerts"""
    engine = get_db_engine()
    query = sqlalchemy.text("""
        SELECT
            priority, alert_type, item, company, port,
            physical_stock, safety_stock, reorder_point,
            days_old, max_storage_days, alert_message
        FROM v_critical_alerts
        ORDER BY priority, item
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


@app.get('/api/intelligence/narrative')
async def get_inventory_narrative():
    """Get natural language summary of inventory status"""
    engine = get_db_engine()
    query = sqlalchemy.text("""
        SELECT
            overall_health, executive_summary,
            total_products, critical_count, warning_count,
            excess_count, normal_count, avg_days_stock,
            total_shortage, total_excess, avg_profit_margin,
            aged_count, aging_soon_count, recommended_actions
        FROM v_inventory_narrative
    """)
    
    with engine.connect() as conn:
        row = conn.execute(query).mappings().first()

    if not row:
        return {
            'success': True,
            'data': {
                'overall_health': 'UNKNOWN',
                'executive_summary': 'No inventory data available',
                'recommended_actions': []
            }
        }

    data = {}
    for k, v in row.items():
        if hasattr(v, 'isoformat'):
            data[k] = str(v)
        elif isinstance(v, (list, tuple)):
            data[k] = list(v)
        else:
            data[k] = v
    
    return {
        'success': True,
        'data': data
    }


@app.get('/api/intelligence/product/{product_name}')
async def get_product_narrative(product_name: str):
    """Get natural language narrative for a specific product"""
    engine = get_db_engine()
    query = sqlalchemy.text("""
        SELECT narrative, status, actions
        FROM get_product_narrative(:product_name)
    """)
    
    with engine.connect() as conn:
        row = conn.execute(query, {'product_name': product_name}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail='Product not found')

    data = {
        'narrative': row['narrative'],
        'status': row['status'],
        'actions': list(row['actions']) if row['actions'] else []
    }
    
    return {
        'success': True,
        'data': data
    }


@app.get('/health')
async def health_check():
    """Health check endpoint"""
    return {'status': 'healthy'}


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
