import requests
from pathlib import Path

print('Testing Market Prices Upload with daily_price_report.xlsx...\n')
API_URL = 'http://localhost:8000/api/uploads/prices'
file_path = Path('data_files/daily_price_report.xlsx')

if file_path.exists():
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(API_URL, files=files, timeout=30)
        print(f'Status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.json()
            print(f'GCS Path: {data.get("gcs_path")}')
            
            ingestion = data.get('ingestion', {})
            print(f'Status: {ingestion.get("status")}')
            print(f'Rows Inserted: {ingestion.get("rows_inserted")}')
            print(f'Rows Updated: {ingestion.get("rows_updated")}')
        else:
            print(f'Error: {response.text}')
else:
    print(f'File not found: {file_path}')
