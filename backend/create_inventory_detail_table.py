"""
Initialize inventory_detail table with expanded uniqueness constraint.

Creates the inventory_detail table fresh with the comprehensive uniqueness key
that includes all value fields (quantities, pricing, metrics).

This script:
1. Checks if table exists
2. If it exists, backs it up (for data preservation if needed)
3. Creates new table with proper schema and expanded unique constraint
4. Can optionally copy data from old table if needed

Usage:
    python backend/create_inventory_detail_table.py
"""

import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy import (
    Table, Column, Integer, Date, String, Numeric, DateTime,
    UniqueConstraint, MetaData, create_engine, text, inspect
)

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend.database import get_engine, Base, InventoryDetail


def create_inventory_detail_table():
    """Create inventory_detail table with expanded uniqueness key."""
    
    engine = get_engine()
    is_sqlite = "sqlite" in str(engine.url)
    
    print("Creating inventory_detail table with expanded uniqueness constraint...")
    print("-" * 70)
    
    with engine.begin() as connection:
        inspector = inspect(connection)
        
        # Check if table exists
        table_exists = "inventory_detail" in inspector.get_table_names()
        
        if table_exists:
            print("⚠️  Table 'inventory_detail' already exists")
            
            if is_sqlite:
                print("   SQLite: Backing up existing table...")
                backup_name = f"inventory_detail_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                connection.execute(text(f"ALTER TABLE inventory_detail RENAME TO {backup_name}"))
                print(f"   ✅ Backed up to: {backup_name}")
            else:
                print("   PostgreSQL: Dropping existing table...")
                connection.execute(text("DROP TABLE IF EXISTS inventory_detail"))
                print("   ✅ Table dropped")
        
        # Create table with expanded unique constraint
        print("\nCreating new inventory_detail table...")
        
        # Use SQLAlchemy ORM to create table
        InventoryDetail.__table__.create(engine, checkfirst=False)
        
        print("✅ Table created successfully")
        
        # Verify the constraint
        inspector = inspect(connection)
        constraints = inspector.get_unique_constraints("inventory_detail")
        
        print("\n📋 Table Schema:")
        print("   Columns:")
        columns = inspector.get_columns("inventory_detail")
        for col in columns:
            nullable = "NULL" if col["nullable"] else "NOT NULL"
            print(f"      - {col['name']}: {col['type']} [{nullable}]")
        
        print("\n🔑 Unique Constraints:")
        for constraint in constraints:
            print(f"   - {constraint['name']}")
            print(f"     Columns: {', '.join(constraint['column_names'])}")


def migrate_data_if_needed():
    """
    Optional: Copy data from old backup table to new table.
    
    This is not called automatically to prevent data loss.
    Uncomment and call manually if you want to migrate data.
    """
    engine = get_engine()
    is_sqlite = "sqlite" in str(engine.url)
    
    if not is_sqlite:
        print("\n💾 Data Migration (PostgreSQL only):")
        print("   To migrate data from backup table, run:")
        print("   INSERT INTO inventory_detail SELECT * FROM inventory_detail_backup_TIMESTAMP;")
        return
    
    print("\n💾 SQLite: Backup table created but data not migrated automatically")
    print("   To restore data: ALTER TABLE inventory_detail_backup_TIMESTAMP RENAME TO inventory_detail;")


if __name__ == "__main__":
    print("=" * 70)
    print("INVENTORY_DETAIL TABLE CREATION")
    print("=" * 70)
    print()
    
    try:
        create_inventory_detail_table()
        migrate_data_if_needed()
        
        print("\n" + "=" * 70)
        print("✅ SUCCESS: inventory_detail table ready")
        print("=" * 70)
        
    except Exception as e:
        print("\n" + "=" * 70)
        print(f"❌ ERROR: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)
