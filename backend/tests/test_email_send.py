"""
Test script to call start_job endpoint and send an email to amitgupta1000@gmail.com
"""
import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000"

async def test_start_job_with_email():
    """Test the start_job endpoint with email to amitgupta1000@gmail.com."""
    print("\n" + "="*70)
    print("🧪 Testing POST /api/jobs/start with Email to amitgupta1000@gmail.com")
    print("="*70)
    
    payload = {
        "chemical_query": "Premium Polyester Fabric - 5000 meters - High Quality Textile",
        "supplier_emails": [
            "amitgupta1000@gmail.com",
        ],
        "user_email": "amit.gupta@coralbayadvisory.com"
    }
    
    print("\n📤 Request Payload:")
    print(json.dumps(payload, indent=2))
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            print(f"\n🔄 Sending POST request to {BASE_URL}/api/jobs/start...")
            response = await client.post(
                f"{BASE_URL}/api/jobs/start",
                json=payload
            )
            
            print(f"\n📊 Response Status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                data = response.json()
                print(f"\n✅ SUCCESS!")
                print(f"Response JSON:")
                print(json.dumps(data, indent=2))
                
                if "job_id" in data:
                    print(f"\n🎉 Job Created Successfully!")
                    print(f"Job ID: {data['job_id']}")
                    print(f"Status: {data.get('status', 'N/A')}")
                    print(f"Total Suppliers: {data.get('total_suppliers', 'N/A')}")
                    print(f"\n📧 Emails have been sent to:")
                    for email in payload["supplier_emails"]:
                        print(f"   • {email}")
                    
                return True
                    
            elif response.status_code == 422:
                print(f"\n❌ VALIDATION ERROR (422)!")
                print("Response JSON:")
                print(json.dumps(response.json(), indent=2))
                return False
                
            else:
                print(f"\n⚠️  Unexpected Status: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except httpx.ConnectError as e:
            print(f"\n❌ Connection Error: {e}")
            print("Make sure the backend server is running on http://localhost:8000")
            return False
        except Exception as e:
            print(f"\n❌ Error: {type(e).__name__}: {e}")
            return False
    
    print("\n" + "="*70)

if __name__ == "__main__":
    success = asyncio.run(test_start_job_with_email())
    if success:
        print("✅ Test completed successfully!")
    else:
        print("❌ Test failed!")
