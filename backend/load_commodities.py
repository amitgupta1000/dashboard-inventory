"""
Load commodities from inventory_targets.csv into the Commodity table.

The CSV contains product names that need to be created as commodities first
before targets can be loaded.
"""

import pandas as pd
from sqlalchemy.orm import Session
from backend.database import Commodity, SYNC_DATABASE_URL, create_engine


def load_commodities_from_csv(file_path: str = "data_files/inventory_targets.csv"):
    """
    Load unique product names from CSV as commodities.
    
    Returns:
        dict with keys: created_count, skipped_count, errors
    """
    # Read CSV
    df = pd.read_csv(file_path, encoding='latin-1')
    
    print(f"\n=== Loading Commodities from {file_path} ===")
    
    # Get unique product names
    products = df['product_name'].dropna().unique()
    print(f"Unique products in CSV: {len(products)}")
    
    # Connect to database
    engine = create_engine(SYNC_DATABASE_URL)
    session = Session(engine)
    
    created_count = 0
    skipped_count = 0
    errors = []
    
    try:
        for product_name in sorted(products):
            try:
                # Check if commodity already exists
                existing = session.query(Commodity).filter(
                    Commodity.commodity_name.ilike(product_name)
                ).first()
                
                if existing:
                    print(f"⊘ {product_name} (already exists)")
                    skipped_count += 1
                    continue
                
                # Create new commodity
                commodity = Commodity(
                    commodity_name=product_name.strip().upper(),
                    commodity_code=None,
                    category=None,
                    unit_of_measure=None,
                    is_active=True,
                    notes=f"Loaded from inventory_targets.csv"
                )
                session.add(commodity)
                created_count += 1
                print(f"✓ {product_name}")
                
            except Exception as e:
                errors.append({'product': product_name, 'error': str(e)})
                print(f"✗ {product_name}: {str(e)}")
        
        # Commit all changes
        session.commit()
        print(f"\n=== Load Summary ===")
        print(f"Created: {created_count}")
        print(f"Skipped: {skipped_count}")
        
        if errors:
            print(f"Errors: {len(errors)}")
            for error in errors[:5]:
                print(f"  - {error['product']}: {error['error']}")
        
        return {
            'created_count': created_count,
            'skipped_count': skipped_count,
            'errors': errors
        }
        
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    result = load_commodities_from_csv()
    print(f"\nResult: {result}")
