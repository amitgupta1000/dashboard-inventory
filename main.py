from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sqlalchemy
import io
import pandas as pd
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv('backend/.env')

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


@app.get('/health')
async def health_check():
    """Health check endpoint"""
    return {'status': 'healthy'}


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
