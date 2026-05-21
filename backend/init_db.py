"""
Initialize database tables using SQLAlchemy ORM models
"""
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Base, get_engine, InventoryDetail, ProductDailyMetrics

load_dotenv()


def init_db():
    """Create all tables from ORM models."""
    engine = get_engine()
    
    print("Creating database tables from ORM models...")
    print(f"Database URL: {os.environ.get('CLOUD_SQL_DATABASE', 'inventory')}")
    
    try:
        # Create all tables defined in Base
        Base.metadata.create_all(engine)
        
        # Verify tables were created
        inspector = __import__('sqlalchemy').inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"\n✓ Database initialization successful!")
        print(f"✓ Created tables: {', '.join(tables)}")
        
        # Verify InventoryDetail columns
        if 'inventory_detail' in tables:
            columns = [col['name'] for col in inspector.get_columns('inventory_detail')]
            print(f"\n✓ inventory_detail columns: {len(columns)} fields")
            print(f"  - Key fields: {', '.join([c for c in columns if c in ['exchange_rate', 'incoming_stock', 'incoming_stock_date', 'product_name', 'date']])}")
        
        # Verify ProductDailyMetrics columns
        if 'product_daily_metrics' in tables:
            columns = [col['name'] for col in inspector.get_columns('product_daily_metrics')]
            print(f"\n✓ product_daily_metrics columns: {len(columns)} fields")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error initializing database: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = init_db()
    sys.exit(0 if success else 1)
