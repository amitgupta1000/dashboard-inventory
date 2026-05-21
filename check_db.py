import sqlite3

conn = sqlite3.connect('inventory.db')
c = conn.cursor()

# List all tables
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print("Tables in database:")
for table in tables:
    print(f"  - {table[0]}")

# Check inventory_detail columns
print("\ninventory_detail columns:")
c.execute("PRAGMA table_info(inventory_detail)")
cols = c.fetchall()
if cols:
    for col in cols:
        print(f"  - {col[1]} ({col[2]})")
else:
    print("  No columns found or table does not exist")

# Check for required columns
required = ['exchange_rate', 'incoming_stock', 'incoming_stock_date']
col_names = [col[1] for col in cols]
print("\nRequired columns check:")
for req in required:
    status = "✓" if req in col_names else "✗"
    print(f"  {status} {req}")

conn.close()
