import sqlite3

conn = sqlite3.connect('./jobs.db')
cursor = conn.cursor()

# Check if inventory_detail table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='inventory_detail'")
if cursor.fetchone():
    print('SUCCESS: inventory_detail table created')
    cursor.execute('PRAGMA table_info(inventory_detail)')
    cols = cursor.fetchall()
    print(f'Columns: {len(cols)}')
    for col in cols[:5]:
        print(f'  {col[1]} - {col[2]}')
    if len(cols) > 5:
        print(f'  ... and {len(cols)-5} more columns')
else:
    print('FAILED: Table not found')

conn.close()
