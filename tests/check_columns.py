import sqlite3

conn = sqlite3.connect('inventory.db')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(inventory_detail)')
columns = cursor.fetchall()

print('All columns in inventory_detail table:')
print('=' * 70)
for col in columns:
    col_id, name, type_, notnull, default, pk = col
    print(f'[{col_id:2}] {name:30} | Type: {type_:15} | PK: {pk}')

print()
print(f'Total columns: {len(columns)}')
conn.close()
