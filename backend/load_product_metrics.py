"""
Load product daily metrics from CSV to database
"""
import csv
import pandas as pd
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


def normalize_product_name(name: str) -> str:
    """Normalize product name for matching (uppercase, no extra spaces)."""
    if not name:
        return ""
    return " ".join(name.upper().strip().split())


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
    """Parse date from CSV format (e.g., '5/21/2026' or '5/22/26')."""
    if not date_str or date_str.strip() == '':
        return None
    try:
        # Try full year first (5/21/2026)
        try:
            return datetime.strptime(date_str.strip(), '%m/%d/%Y').date()
        except:
            # Try 2-digit year (5/22/26)
            return datetime.strptime(date_str.strip(), '%m/%d/%y').date()
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
        
        if not os.path.exists(csv_file_path):
            print(f"✗ CSV file not found: {csv_file_path}")
            return 0
        
        # Read CSV with pandas to validate column names
        df = pd.read_csv(csv_file_path)
        print(f"Columns in CSV: {df.columns.tolist()}\n")
        
        rows_loaded = 0
        rows_skipped = 0
        
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (after header)
                try:
                    product_name = row.get('PRODUCT NAME', '').strip()
                    date_str = row.get('UPDATION DATE', '').strip()  # Use UPDATION DATE
                    
                    if not product_name:
                        print(f"Row {row_num}: Skipped - missing product name")
                        rows_skipped += 1
                        continue
                    
                    metric_date = parse_date(date_str)
                    if not metric_date:
                        print(f"Row {row_num}: Skipped - invalid date '{date_str}'")
                        rows_skipped += 1
                        continue
                    
                    # Normalize product name
                    normalized_product = normalize_product_name(product_name)
                    
                    # Check if record already exists for this product on this date
                    existing = session.query(ProductDailyMetrics).filter(
                        ProductDailyMetrics.product_name == normalized_product,
                        ProductDailyMetrics.metric_date == metric_date
                    ).first()
                    
                    if existing:
                        print(f"Row {row_num}: Record already exists for {normalized_product} on {metric_date}")
                        rows_skipped += 1
                        continue
                    
                    # Create new record with available columns
                    metric = ProductDailyMetrics(
                        product_name=normalized_product,
                        metric_date=metric_date,
                        market_price=parse_csv_value(row.get('MARKET PRICE (INR/MT)', '')),
                        replacement_cost=parse_csv_value(row.get('REPLACEMENT COST (INR/MT)', '')),
                        # Note: CSV has additional fields (IMPORT PRICE, EXCHANGE RATE, etc.) 
                        # but ProductDailyMetrics table only has market_price and replacement_cost
                    )
                    
                    session.add(metric)
                    rows_loaded += 1
                    print(f"Row {row_num}: Loaded {normalized_product} ({metric_date})")
                
                except Exception as e:
                    print(f"Row {row_num}: Error - {str(e)}")
                    rows_skipped += 1
                    continue
            
            # Commit all records
            session.commit()
            print(f"\n✅ Successfully loaded {rows_loaded} records")
            if rows_skipped > 0:
                print(f"⚠️  Skipped {rows_skipped} records")
            
            return rows_loaded
    
    except Exception as e:
        session.rollback()
        print(f"✗ Error loading CSV: {str(e)}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    # Try multiple possible CSV file locations
    possible_paths = [
        'data_files/product_pricing.csv',
        'data_files/daily_product_metrics.csv',
        'daily_product_metrics.csv',
    ]
    
    csv_path = None
    for path in possible_paths:
        if os.path.exists(path):
            csv_path = path
            break
    
    if not csv_path:
        print(f"✗ CSV file not found. Tried:")
        for path in possible_paths:
            print(f"  - {path}")
        sys.exit(1)
    
    print(f"Loading product metrics from: {csv_path}\n")
    load_product_metrics_from_csv(csv_path)
