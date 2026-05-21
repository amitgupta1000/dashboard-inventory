"""
Load product daily metrics from CSV to database
"""
import csv
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_engine, ProductDailyMetrics, Base

load_dotenv()


def parse_csv_value(value: str):
    """Parse CSV value, handling currency formatting (commas)."""
    if not value or value.strip() == '':
        return None
    # Remove commas from numbers like "200,000"
    value = str(value).replace(',', '').strip()
    try:
        return Decimal(value)
    except:
        return None


def parse_date(date_str: str):
    """Parse date from CSV format (e.g., '5/21/2026')."""
    if not date_str or date_str.strip() == '':
        return None
    try:
        return datetime.strptime(date_str.strip(), '%m/%d/%Y').date()
    except:
        print(f"Warning: Could not parse date '{date_str}'")
        return None


def load_product_metrics_from_csv(csv_file_path: str):
    """Load product daily metrics from CSV file into database."""
    
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Create tables if they don't exist
        Base.metadata.create_all(engine)
        
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            rows_loaded = 0
            rows_skipped = 0
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (after header)
                try:
                    product_name = row.get('PRODUCT NAME', '').strip()
                    date_str = row.get('DATE', '').strip()
                    
                    if not product_name:
                        print(f"Row {row_num}: Skipped - missing product name")
                        rows_skipped += 1
                        continue
                    
                    metric_date = parse_date(date_str)
                    if not metric_date:
                        print(f"Row {row_num}: Skipped - invalid date '{date_str}'")
                        rows_skipped += 1
                        continue
                    
                    # Check if record already exists
                    existing = session.query(ProductDailyMetrics).filter(
                        ProductDailyMetrics.product_name == product_name,
                        ProductDailyMetrics.metric_date == metric_date
                    ).first()
                    
                    if existing:
                        print(f"Row {row_num}: Record already exists for {product_name} on {metric_date}")
                        rows_skipped += 1
                        continue
                    
                    # Create new record
                    metric = ProductDailyMetrics(
                        product_name=product_name,
                        metric_date=metric_date,
                        market_price=parse_csv_value(row.get('MARKET PRICE (INR/MT)', '')),
                        replacement_cost=parse_csv_value(row.get('REPLACEMENT COST (INR/MT)', '')),
                        safety_stock_level=parse_csv_value(row.get('SAFETY STOCK LEVEL (MT)', '')),
                        reorder_stock_level=parse_csv_value(row.get('REORDER STOCK LEVEL (MT)', '')),
                        target_monthly_sales=parse_csv_value(row.get('TARGET MONTHLY SALES (MT)', '')),
                        target_storage_cap_days=parse_csv_value(row.get('TARGET STORAGE CAP (DAYS)', '')),
                        target_inventory_days=parse_csv_value(row.get('TARGET INVENTORY HOLDING (DAYS)', '')),
                        target_cash_realization_days=parse_csv_value(row.get('TARGET CASH REALISATION (DAYS)', '')),
                    )
                    
                    session.add(metric)
                    rows_loaded += 1
                    print(f"Row {row_num}: Loaded {product_name} ({metric_date})")
                
                except Exception as e:
                    print(f"Row {row_num}: Error - {str(e)}")
                    rows_skipped += 1
                    continue
            
            # Commit all records
            session.commit()
            print(f"\n✓ Successfully loaded {rows_loaded} records")
            if rows_skipped > 0:
                print(f"⚠ Skipped {rows_skipped} records")
            
    except Exception as e:
        session.rollback()
        print(f"✗ Error loading CSV: {str(e)}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    csv_path = os.path.join(os.path.dirname(__file__), '../daily_product_metrics.csv')
    
    if not os.path.exists(csv_path):
        print(f"✗ CSV file not found: {csv_path}")
        sys.exit(1)
    
    print(f"Loading product metrics from: {csv_path}")
    load_product_metrics_from_csv(csv_path)
