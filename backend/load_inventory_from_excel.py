"""
Load inventory data from Excel file to inventory_detail database table
"""
import pandas as pd
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_engine, InventoryDetail, Base

load_dotenv()


def parse_numeric(value):
    """Convert value to Decimal, handling None and non-numeric values."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return Decimal(str(value))
    except:
        return None


def parse_date(value):
    """Convert value to date, handling various date formats."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        if isinstance(value, str):
            # Try common date formats
            for fmt in ['%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d', '%d/%m/%Y']:
                try:
                    return datetime.strptime(value.strip(), fmt).date()
                except:
                    continue
        # If it's a Timestamp object from pandas
        return pd.Timestamp(value).date()
    except Exception as e:
        print(f"Warning: Could not parse date '{value}': {e}")
        return None


def load_inventory_from_excel(excel_file_path: str, sheet_name: str = 0):
    """Load inventory detail data from Excel file into database."""
    
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Create tables if they don't exist
        Base.metadata.create_all(engine)
        
        # Read Excel file - header is in first row, data starts from row 1
        df = pd.read_excel(excel_file_path, sheet_name=sheet_name)
        
        print(f"Loaded Excel file with {len(df)} rows and {len(df.columns)} columns")
        print(f"Columns: {df.columns.tolist()}\n")
        print(f"First row sample data:")
        if len(df) > 0:
            print(df.iloc[0])
        
        rows_loaded = 0
        rows_skipped = 0
        
        for row_num, (idx, row) in enumerate(df.iterrows(), start=2):
            try:
                # Extract and clean column values
                date_val = parse_date(row.get('DATE'))
                vessel_date_val = parse_date(row.get('VESSEL DATE'))
                vessel_name = str(row.get('VESSEL NAME', '')).strip() if row.get('VESSEL NAME') else None
                product_name = str(row.get('PRODUCT NAME', '')).strip()
                port_name = str(row.get('PORT', '')).strip() if row.get('PORT') else None
                company_terminal = str(row.get('TERMINAL', '')).strip() if row.get('TERMINAL') else None
                
                # Validate required fields
                if not product_name:
                    print(f"Row {row_num}: Skipped - missing product name")
                    rows_skipped += 1
                    continue
                
                if not date_val:
                    print(f"Row {row_num}: Skipped - invalid date")
                    rows_skipped += 1
                    continue
                
                # Check for duplicate
                existing = session.query(InventoryDetail).filter(
                    InventoryDetail.date == date_val,
                    InventoryDetail.vessel_name == vessel_name,
                    InventoryDetail.product_name == product_name,
                    InventoryDetail.company_terminal_name == company_terminal,
                    InventoryDetail.port_name == port_name
                ).first()
                
                if existing:
                    print(f"Row {row_num}: Duplicate record skipped - {product_name} on {date_val}")
                    rows_skipped += 1
                    continue
                
                # Extract quantities - handle column names with newlines
                unsold_qty = parse_numeric(row.get('UNSOLD \nQTY'))
                sold_qty_pending = parse_numeric(row.get('SOLD QTY /\nPENDING LIFTING'))
                physical_stock = parse_numeric(row.get('PHYSICAL STOCK'))
                otr_qty = parse_numeric(row.get('OTR QTY'))
                
                # Pricing & Costs
                purchase_price_usd = parse_numeric(row.get('IMPORT PRICE ($ /MT)'))
                cost_price_inr = parse_numeric(row.get('COST PRICE (INR /MT)'))
                avg_selling_price_inr = parse_numeric(row.get('AVERAGE SALE PRICE (INR/ MT)'))
                exchange_rate = parse_numeric(row.get('EXCHANGE RATE'))
                cif_duty = parse_numeric(row.get('CIF + DUTY COST'))
                
                # Incoming stock
                incoming_stock = parse_numeric(row.get('INCOMING STOCK'))
                incoming_stock_date_val = parse_date(row.get('INCOMING STOCK DATE'))
                
                # Metrics
                no_of_days_stock = None
                try:
                    no_of_days_stock = int(row.get('NO OF DAYS OF STOCK', 0)) if row.get('NO OF DAYS OF STOCK') else None
                except:
                    pass
                
                # Create new inventory detail record
                inventory_detail = InventoryDetail(
                    date=date_val,
                    vessel_date=vessel_date_val,
                    vessel_name=vessel_name,
                    product_name=product_name,
                    port_name=port_name,
                    company_terminal_name=company_terminal,
                    
                    unsold_qty=unsold_qty,
                    sold_qty_pending_lifting=sold_qty_pending,
                    physical_stock=physical_stock,
                    otr_qty=otr_qty,
                    
                    purchase_price_USD=purchase_price_usd,
                    cif_duty=cif_duty,
                    cost_price_INR=cost_price_inr,
                    average_selling_price_INR=avg_selling_price_inr,
                    exchange_rate=exchange_rate,
                    
                    incoming_stock=incoming_stock,
                    incoming_stock_date=incoming_stock_date_val,
                    
                    no_of_days_of_stock=no_of_days_stock
                )
                
                session.add(inventory_detail)
                rows_loaded += 1
                
                if rows_loaded % 10 == 0:
                    print(f"Processed {rows_loaded} rows...")
                
            except Exception as e:
                print(f"Row {row_num}: Error - {str(e)}")
                rows_skipped += 1
                session.rollback()
                continue
        
        # Commit all records
        session.commit()
        print(f"\n✓ Successfully loaded {rows_loaded} inventory records")
        if rows_skipped > 0:
            print(f"⚠ Skipped {rows_skipped} records")
        
        return rows_loaded, rows_skipped
        
    except Exception as e:
        session.rollback()
        print(f"✗ Error loading Excel: {str(e)}")
        raise
    finally:
        session.close()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Load inventory data from Excel to database')
    parser.add_argument('--file', default='12-5-26.xlsx', help='Excel file path (default: 12-5-26.xlsx)')
    parser.add_argument('--sheet', default='12-05-2026', help='Sheet name or number (default: 12-05-2026)')
    
    args = parser.parse_args()
    
    excel_path = args.file
    
    if not os.path.exists(excel_path):
        print(f"✗ Excel file not found: {excel_path}")
        # Try looking in root directory
        root_excel = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), args.file)
        if os.path.exists(root_excel):
            excel_path = root_excel
            print(f"✓ Found at: {excel_path}")
        else:
            sys.exit(1)
    
    print(f"Loading inventory from: {excel_path}")
    print(f"Sheet: {args.sheet}\n")
    
    try:
        rows_loaded, rows_skipped = load_inventory_from_excel(excel_path, args.sheet)
        print(f"\n📊 Load Summary:")
        print(f"   Total loaded: {rows_loaded}")
        print(f"   Total skipped: {rows_skipped}")
        print(f"   Success rate: {(rows_loaded / (rows_loaded + rows_skipped) * 100):.1f}%" if rows_loaded + rows_skipped > 0 else "")
    except Exception as e:
        print(f"\n✗ Failed to load inventory data: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
