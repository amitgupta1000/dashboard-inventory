import sqlite3

conn = sqlite3.connect('./jobs.db')
cursor = conn.cursor()

cursor.execute('PRAGMA table_info(inventory_detail)')
cols = cursor.fetchall()
print('Complete column list for inventory_detail:')
print()
for i, col in enumerate(cols, 1):
    print(f'{i:2}. {col[1]:35} - {col[2]}')

conn.close()
