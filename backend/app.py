from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import uvicorn
from typing import List, Dict, Any

app = FastAPI(title="Inventory Management API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_inventory_data():
    """Load and process inventory data from Excel file"""
    try:
        # Read Excel file, row 0 has the headers
        df = pd.read_excel('../stock_report.xlsx', header=0)
        
        # Clean column names
        df.columns = [
            'company_name',
            'port_name',
            'product_name',
            'physical_stock',
            'total_sold_qty',
            'total_unsold_qty',
            'incoming_vessel_qty',
            'avg_import_price_usd',
            'avg_price_inr',
            'current_market_price',
            'replacement_cost',
            'stock_value'
        ]
        
        # Remove the last row if it's a total row (contains NaN in company_name)
        df = df[df['company_name'].notna()]
        
        # Convert numeric columns
        numeric_columns = [
            'physical_stock', 'total_sold_qty', 'total_unsold_qty',
            'incoming_vessel_qty', 'avg_import_price_usd', 'avg_price_inr',
            'current_market_price', 'replacement_cost', 'stock_value'
        ]
        
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        return None

@app.get('/api/inventory')
async def get_inventory():
    """Get all inventory data"""
    df = load_inventory_data()
    
    if df is None:
        raise HTTPException(status_code=500, detail='Failed to load inventory data')
    
    # Convert to dict and handle NaN values
    data = df.fillna('').to_dict(orient='records')
    
    return {
        'success': True,
        'data': data,
        'total': len(data)
    }

@app.get('/api/inventory/summary')
async def get_summary():
    """Get inventory summary statistics"""
    df = load_inventory_data()
    
    if df is None:
        raise HTTPException(status_code=500, detail='Failed to load inventory data')
    
    summary = {
        'total_products': len(df),
        'total_physical_stock': float(df['physical_stock'].sum()),
        'total_stock_value': float(df['stock_value'].sum()),
        'total_sold_qty': float(df['total_sold_qty'].sum()),
        'total_unsold_qty': float(df['total_unsold_qty'].sum()),
    }
    
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
