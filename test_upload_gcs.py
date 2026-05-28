import requests
import json
from pathlib import Path

print('=== Testing Uploads with GCS ===\n')

# Test 1: Stock Report Upload
print('1. Testing Stock Report Upload...')
API_URL = 'http://localhost:8000/api/uploads/inventory'
file_path = Path('data_files/stock_report.csv')

if file_path.exists():
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(API_URL, files=files, timeout=30)
        print(f'   Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.json()
            print(f'   GCS Path: {data.get("gcs_path", "N/A")}')
            
            ingestion = data.get('ingestion', {})
            print(f'   Ingestion Status: {ingestion.get("status")}')
            print(f'   Rows Inserted: {ingestion.get("rows_inserted")}')
            print(f'   Rows Updated: {ingestion.get("rows_updated")}')
            commodity_match = ingestion.get('commodity_match', {})
            if commodity_match:
                print(f'   Commodity Match: {commodity_match.get("match_percentage")}%')
        else:
            print(f'   Error: {response.text}')
else:
    print(f'   File not found: {file_path}')

# Test 2: Prices Upload
print('\n2. Testing Prices Upload...')
API_URL = 'http://localhost:8000/api/uploads/prices'
file_path = Path('data_files/product_pricing.csv')

if file_path.exists():
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(API_URL, files=files, timeout=30)
        print(f'   Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.json()
            print(f'   GCS Path: {data.get("gcs_path", "N/A")}')
            
            ingestion = data.get('ingestion', {})
            print(f'   Ingestion Status: {ingestion.get("status")}')
            print(f'   Rows Inserted: {ingestion.get("rows_inserted")}')
        else:
            print(f'   Error: {response.text}')
else:
    print(f'   File not found: {file_path}')

print('\n✓ Upload tests complete!')
