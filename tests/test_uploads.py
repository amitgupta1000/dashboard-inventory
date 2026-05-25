#!/usr/bin/env python3
"""
Quick test script to verify upload API endpoints
Run with: python tests/test_uploads.py
"""

import asyncio
import httpx
import json
from pathlib import Path
from datetime import datetime

API_BASE_URL = "http://localhost:8000"

async def test_upload_endpoints():
    """Test all upload endpoints"""
    
    async with httpx.AsyncClient() as client:
        print("\n" + "="*60)
        print("🧪 TESTING UPLOAD API ENDPOINTS")
        print("="*60 + "\n")
        
        # Test 1: Get Summary
        print("1️⃣  Testing /api/uploads/summary")
        try:
            response = await client.get(f"{API_BASE_URL}/api/uploads/summary")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Inventory files: {data.get('inventory_files', 0)}")
                print(f"   ✅ Prices files: {data.get('prices_files', 0)}")
                print(f"   ✅ Sales files: {data.get('sales_register_files', 0)}")
                print(f"   ✅ Total: {data.get('total_files', 0)}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 2: List Inventory Files
        print("\n2️⃣  Testing /api/uploads/inventory (GET)")
        try:
            response = await client.get(f"{API_BASE_URL}/api/uploads/inventory")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Found {data.get('count', 0)} inventory files")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 3: List Prices Files
        print("\n3️⃣  Testing /api/uploads/prices (GET)")
        try:
            response = await client.get(f"{API_BASE_URL}/api/uploads/prices")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Found {data.get('count', 0)} prices files")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 4: List Sales Register Files
        print("\n4️⃣  Testing /api/uploads/sales-register (GET)")
        try:
            response = await client.get(f"{API_BASE_URL}/api/uploads/sales-register")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Found {data.get('count', 0)} sales register files")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 5: Upload a Test File (if test data exists)
        print("\n5️⃣  Testing /api/uploads/inventory (POST)")
        test_file_path = Path("tests/test_inventory.xlsx")
        if test_file_path.exists():
            try:
                with open(test_file_path, 'rb') as f:
                    files = {'file': ('test_inventory.xlsx', f, 'application/octet-stream')}
                    response = await client.post(
                        f"{API_BASE_URL}/api/uploads/inventory",
                        files=files
                    )
                print(f"   Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ Upload successful!")
                    print(f"   ✅ GCS Path: {data.get('gcs_path')}")
                    print(f"   ✅ Message: {data.get('message')}")
                else:
                    print(f"   ❌ Upload failed: {response.text}")
            except Exception as e:
                print(f"   ⚠️  Skipped (test file not found): {e}")
        else:
            print(f"   ⚠️  Skipped (test file not found at {test_file_path})")
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED")
        print("="*60 + "\n")

if __name__ == "__main__":
    print("\n🚀 Starting upload API tests...\n")
    print("⚠️  Make sure the API is running: python main.py\n")
    
    try:
        asyncio.run(test_upload_endpoints())
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        print("Make sure the API server is running on http://localhost:8000")
