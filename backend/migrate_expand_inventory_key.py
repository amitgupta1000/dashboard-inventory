"""
Database migration: Expand inventory_detail unique constraint to include all value fields.

This migration updates the unique constraint from only identifying attributes
(vessel, product, location) to include ALL fields (quantities, pricing, metrics).

Before:
  UNIQUE (date, vessel_name, product_name, company_terminal_name, company_name, port_name)
  
After:
  UNIQUE (date, vessel_name, vessel_date, product_name, port_name, company_terminal_name,
          company_name, unsold_qty, sold_qty_pending_lifting, physical_stock, otr_qty,
          cost_price_INR, average_selling_price_INR, no_of_days_of_stock)

Effect:
- Same vessel with DIFFERENT quantities → INSERT new record
- Same vessel with SAME quantities → Deduplicated (no duplicate)
- Enables tracking all inventory snapshots with different values
"""

import sys
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.inspection import inspect

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend.database import get_engine

def migrate():
    """Execute the unique constraint migration."""
    engine = get_engine()
    
    # Check current database type
    is_sqlite = "sqlite" in str(engine.url)
    
    with engine.begin() as connection:
        inspector = inspect(connection)
        
        # Check if table exists
        if "inventory_detail" not in inspector.get_table_names():
            print("❌ inventory_detail table does not exist. Creating schema first...")
            from backend.database import Base
            Base.metadata.create_all(engine)
            print("✅ Schema created")
            return
        
        # Get existing constraints
        constraints = {c["name"]: c for c in inspector.get_unique_constraints("inventory_detail")}
        
        if is_sqlite:
            print("ℹ️  SQLite detected: Renaming table to rebuild constraints...")
            
            # SQLite doesn't support DROP CONSTRAINT, so we need to:
            # 1. Rename existing table
            # 2. Create new table with updated constraint
            # 3. Copy data
            # 4. Drop old table
            
            try:
                # Drop old constraint by recreating table
                # SQLite requires full table recreation for constraint changes
                
                # First, check if the new constraint name already exists
                if "uq_inventory_detail_complete_record" in constraints:
                    print("✅ New unique constraint already exists")
                    return
                
                # For SQLite, we'll use the ORM to recreate
                from backend.database import Base, InventoryDetail
                
                # The constraint will be applied when we call create_all with checkfirst=False
                # But since SQLite doesn't support altering constraints easily,
                # we'll just note this and let the app create it if needed
                print("⚠️  SQLite unique constraint update requires table recreation")
                print("    Drop and recreate the database to apply this migration:")
                print("    1. Delete jobs.db")
                print("    2. Run: python backend/init_db.py")
                
            except Exception as e:
                print(f"❌ SQLite migration error: {e}")
                raise
        
        else:
            # PostgreSQL: Drop old constraint and create new one
            print("ℹ️  PostgreSQL detected: Updating constraints...")
            
            # Drop old constraint if it exists
            if "uq_inventory_detail_record" in constraints:
                print("  Dropping old constraint: uq_inventory_detail_record")
                connection.execute(text(
                    "ALTER TABLE inventory_detail DROP CONSTRAINT uq_inventory_detail_record"
                ))
            
            # Create new constraint
            if "uq_inventory_detail_complete_record" not in constraints:
                print("  Creating new constraint: uq_inventory_detail_complete_record")
                connection.execute(text("""
                    ALTER TABLE inventory_detail ADD CONSTRAINT uq_inventory_detail_complete_record
                    UNIQUE (date, vessel_name, vessel_date, product_name, port_name,
                            company_terminal_name, company_name,
                            unsold_qty, sold_qty_pending_lifting, physical_stock, otr_qty,
                            cost_price_INR, average_selling_price_INR, no_of_days_of_stock)
                """))
                print("✅ New constraint created")
            else:
                print("✅ New constraint already exists")

if __name__ == "__main__":
    print("Starting migration: Expand inventory_detail unique constraint")
    print("-" * 70)
    
    try:
        migrate()
        print("-" * 70)
        print("✅ Migration completed successfully")
    except Exception as e:
        print("-" * 70)
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
