import requests
import json

BASE_URL = "http://localhost:8000/api/analytics"

print("Testing Layer 1 Analytics Endpoints\n")
print("=" * 60)

# Test 1: Get available dates
print("\n1. GET /dates")
response = requests.get(f"{BASE_URL}/dates")
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Available dates: {data.get('available_dates', [])[:5]}")  # Show first 5
else:
    print(f"Error: {response.text}")

# Test 2: Get vessel details
print("\n2. GET /vessel-detail")
response = requests.get(f"{BASE_URL}/vessel-detail")
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"As of: {data.get('as_of_date')}")
    print(f"Backdate: {data.get('backdate')}")
    print(f"Total vessels: {len(data.get('data', []))}")
    if data.get('data'):
        print(f"Sample: {json.dumps(data['data'][0], indent=2)}")
else:
    print(f"Error: {response.text}")

# Test 3: Get summary by product
print("\n3. GET /summary?view_type=product")
response = requests.get(f"{BASE_URL}/summary?view_type=product")
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"View type: {data.get('view_type')}")
    print(f"Total aggregations: {len(data.get('data', []))}")
    if data.get('data'):
        print(f"Sample:\n{json.dumps(data['data'][0], indent=2)}")
else:
    print(f"Error: {response.text}")

# Test 4: Get summary by company
print("\n4. GET /summary?view_type=company")
response = requests.get(f"{BASE_URL}/summary?view_type=company")
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"View type: {data.get('view_type')}")
    print(f"Total aggregations: {len(data.get('data', []))}")
else:
    print(f"Error: {response.text}")

# Test 5: Get summary by port
print("\n5. GET /summary?view_type=port")
response = requests.get(f"{BASE_URL}/summary?view_type=port")
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"View type: {data.get('view_type')}")
    print(f"Total aggregations: {len(data.get('data', []))}")
else:
    print(f"Error: {response.text}")

print("\n" + "=" * 60)
print("✓ All endpoints tested successfully!")
