"""
Migration script to add monthly_sales_target and target_storage_cap_days columns
to commodity_daily_configs table.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text, create_engine
from database import SYNC_DATABASE_URL


def migrate_add_target_fields():
    """Add new columns to commodity_daily_configs table if they don't exist."""
    engine = create_engine(SYNC_DATABASE_URL)
    
    print("Checking if migration is needed...")
    
    with engine.connect() as connection:
        # Check if columns exist
        result = connection.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='commodity_daily_configs' 
            AND column_name IN ('monthly_sales_target', 'target_storage_cap_days')
        """))
        existing_columns = {row[0] for row in result}
        
        needs_migration = False
        
        # Add monthly_sales_target if it doesn't exist
        if 'monthly_sales_target' not in existing_columns:
            print("Adding monthly_sales_target column...")
            try:
                connection.execute(text("""
                    ALTER TABLE commodity_daily_configs
                    ADD COLUMN monthly_sales_target FLOAT NULL
                """))
                connection.commit()
                print("✓ Added monthly_sales_target")
                needs_migration = True
            except Exception as e:
                print(f"✗ Error adding monthly_sales_target: {e}")
        
        # Add target_storage_cap_days if it doesn't exist
        if 'target_storage_cap_days' not in existing_columns:
            print("Adding target_storage_cap_days column...")
            try:
                connection.execute(text("""
                    ALTER TABLE commodity_daily_configs
                    ADD COLUMN target_storage_cap_days FLOAT NULL
                """))
                connection.commit()
                print("✓ Added target_storage_cap_days")
                needs_migration = True
            except Exception as e:
                print(f"✗ Error adding target_storage_cap_days: {e}")
        
        if not needs_migration:
            print("✓ Migration not needed - columns already exist")
        else:
            print("✓ Migration completed successfully")


if __name__ == "__main__":
    migrate_add_target_fields()
