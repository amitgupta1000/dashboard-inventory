import openpyxl
from collections import defaultdict

file_path = '12-5-26.xlsx'
wb = openpyxl.load_workbook(file_path)
ws = wb['12-05-2026']

# Extract unique commodities
commodities = set()
commodity_details = defaultdict(lambda: {'terminals': set(), 'ports': set(), 'count': 0})

for row in ws.iter_rows(min_row=3, max_row=ws.max_row, values_only=True):
    if row[3]:  # Column D - PRODUCT NAME
        commodity_name = str(row[3]).strip()
        terminal = str(row[10]).strip() if row[10] else 'Unknown'
        port = str(row[4]).strip() if row[4] else 'Unknown'
        
        commodities.add(commodity_name)
        commodity_details[commodity_name]['terminals'].add(terminal)
        commodity_details[commodity_name]['ports'].add(port)
        commodity_details[commodity_name]['count'] += 1

print('🏷️  Unique Commodities Found:', len(commodities))
print()
for commodity in sorted(commodities):
    details = commodity_details[commodity]
    count = details['count']
    terminals = sorted(details['terminals'])
    ports = sorted(details['ports'])
    print(f"{commodity}:")
    print(f"  Records: {count}")
    print(f"  Terminals: {terminals}")
    print(f"  Ports: {ports}")
    print()
