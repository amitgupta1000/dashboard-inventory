"""
Data loader for market_data_hvb from Excel price reports
"""
import pandas as pd
import openpyxl
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys

# Add parent directory to path for imports
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from backend.database import get_engine
from backend.market_data_schema import MarketDataHVB, Base


def extract_product_info(product_str: str) -> tuple[str, str]:
    """
    Extract product name and port from product string like 'TOLUENE - KANDLA'
    Returns (product_name, port)
    """
    if not product_str or not isinstance(product_str, str):
        return ('', '')
    
    # Split on '-' and strip whitespace
    parts = [p.strip() for p in product_str.split('-')]
    
    if len(parts) >= 2:
        product_name = parts[0].strip()
        port = parts[1].strip()
    elif len(parts) == 1:
        product_name = parts[0].strip()
        port = ''
    else:
        product_name = ''
        port = ''
    
    return (product_name, port)


def load_market_data_from_excel(file_path: str, report_date: datetime.date = None):
    """
    Load market data from Excel file into market_data_hvb table
    
    Args:
        file_path: Path to the Excel file
        report_date: Date for this report (defaults to today)
    
    Returns:
        Number of rows loaded
    """
    if report_date is None:
        report_date = datetime.now().date()
    
    # Read Excel file with openpyxl to get exact cell values
    wb = openpyxl.load_workbook(file_path)
    ws = wb.active
    
    # Extract USD/INR rate from last row, column M (13)
    last_row = ws.max_row
    usdinr_rate = ws.cell(last_row, 13).value  # Column M
    
    # Read data with pandas (excluding last row which is TOTAL)
    df = pd.read_excel(file_path, sheet_name=0)
    
    # Remove the last row (TOTAL)
    df = df.iloc[:-1]
    
    # Standardize column names (lowercase, replace spaces and special chars)
    df.columns = [
        'product',               # 0
        'company',               # 1
        'monthly_volumes',       # 2
        'ready',                 # 3
        'second_half_may',       # 4
        'june_1st_half',         # 5
        'physical_stock',        # 6 (note: PHYSCIAL in original has typo)
        'pending_lifting',       # 7
        'port_stock',            # 8
        'replac_dollar',         # 9
        'replace',               # 10
        'index',                 # 11
        'market_price',          # 12
        'selling_p',             # 13
        'may',                   # 14
        'june',                  # 15
        'arrival_date',          # 16
        'unnamed_17',            # 17 (ignore)
        'unnamed_18',            # 18 (ignore)
        'unnamed_19'             # 19 (ignore)
    ]
    
    # Extract product info
    df[['product_name', 'port']] = df['product'].apply(
        lambda x: pd.Series(extract_product_info(str(x)))
    )
    
    # Convert arrival_date to string, replacing NaN with None
    df['arrival_date'] = df['arrival_date'].apply(
        lambda x: str(x).strip() if pd.notna(x) and str(x).strip().lower() != 'nan' else None
    )
    
    # Add report metadata
    df['report_date'] = report_date
    df['usdinr_rate'] = usdinr_rate
    
    # Get database engine and create session
    engine = get_engine()
    
    # Create table if it doesn't exist
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Load data
        row_count = 0
        for idx, row in df.iterrows():
            market_data = MarketDataHVB(
                report_date=report_date,
                product=row['product'],
                company=row['company'],
                monthly_volumes=_to_float(row['monthly_volumes']),
                ready=_to_float(row['ready']),
                second_half_may=_to_float(row['second_half_may']),
                june_1st_half=_to_float(row['june_1st_half']),
                physical_stock=_to_float(row['physical_stock']),
                pending_lifting=_to_float(row['pending_lifting']),
                port_stock=_to_float(row['port_stock']),
                replac_dollar=_to_float(row['replac_dollar']),
                replace=_to_float(row['replace']),
                index=_to_float(row['index']),
                market_price=_to_float(row['market_price']),
                selling_p=_to_float(row['selling_p']),
                may=_to_float(row['may']),
                june=_to_float(row['june']),
                arrival_date=row['arrival_date'],
                product_name=row['product_name'],
                port=row['port'],
                usdinr_rate=_to_float(usdinr_rate),
            )
            session.add(market_data)
            row_count += 1
        
        session.commit()
        print(f"✅ Loaded {row_count} rows from {file_path}")
        print(f"   Report Date: {report_date}")
        print(f"   USD/INR Rate: {usdinr_rate}")
        return row_count
    
    except Exception as e:
        session.rollback()
        print(f"❌ Error loading data: {str(e)}")
        raise
    
    finally:
        session.close()


def _to_float(value):
    """Convert value to float, handling None and string values"""
    if value is None:
        return None
    if isinstance(value, float):
        if pd.isna(value):
            return None
        return value
    if isinstance(value, int):
        return float(value)
    if isinstance(value, str):
        s = str(value).strip()
        if s.lower() in ['nan', '', 'none']:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


if __name__ == '__main__':
    # Example usage
    file_path = 'data_files/DAILY PRICE REPORT 22-05-2026.xlsx'
    
    if not Path(file_path).exists():
        print(f"❌ File not found: {file_path}")
        sys.exit(1)
    
    # Extract date from filename (22-05-2026)
    filename = Path(file_path).stem
    try:
        date_str = filename.split()[-1]  # Get '22-05-2026'
        day, month, year = date_str.split('-')
        report_date = datetime(int(year), int(month), int(day)).date()
    except:
        report_date = None
    
    load_market_data_from_excel(file_path, report_date)
