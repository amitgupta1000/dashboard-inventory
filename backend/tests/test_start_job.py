"""
Quick API test for the /api/jobs/start endpoint
"""
import httpx
import json

BASE_URL = "http://localhost:8000"

async def test_start_job():
    """Test the start job endpoint with proper payload."""
    print("\n" + "="*70)
    print("🧪 Testing POST /api/jobs/start")
    print("="*70)
    
    payload = {
        "chemical_query": "Polyester Fabric - 5000 meters",
        "supplier_emails": [
            "supplier1@example.com",
            "supplier2@example.com"
        ],
        "user_email": "amit.gupta@coralbayadvisory.com"
    }
    
    print("\n📤 Payload:")
    print(json.dumps(payload, indent=2))
    
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/jobs/start",
                json=payload
            )
            
            print(f"\n📊 Response Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            if response.status_code in [200, 201]:
                data = response.json()
                print(f"\n✅ SUCCESS!")
                print(f"Response JSON:")
                print(json.dumps(data, indent=2))
                
                if "job_id" in data:
                    print(f"\n🎉 Job Created! ID: {data['job_id']}")
            elif response.status_code == 422:
                print(f"\n❌ VALIDATION ERROR (422)!")
                print("Response JSON:")
                print(json.dumps(response.json(), indent=2))
            else:
                print(f"\n⚠️  Unexpected Status")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_start_job())
