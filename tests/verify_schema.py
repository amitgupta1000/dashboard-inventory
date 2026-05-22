import sqlite3

conn = sqlite3.connect('inventory.db')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(inventory_detail)")
columns = cursor.fetchall()

print('inventory_detail table columns:')
print('=' * 70)
for col in columns:
    col_id, name, type_, notnull, default, pk = col
    print(f'{name:30} | Type: {type_:15} | PK: {pk}')

# Verify required columns exist
required_cols = ['exchange_rate', 'incoming_stock', 'incoming_stock_date']
existing_cols = [col[1] for col in columns]

print()
print('Verification of required columns:')
print('=' * 70)
for req_col in required_cols:
    status = '✓' if req_col in existing_cols else '✗'
    print(f'{status} {req_col}')

conn.close()
