"""
Diagnostic script to test Cloud SQL Connector setup
"""
import asyncio
import os
from cloud_sql_python_connector import AsyncConnector

async def test_connector():
    """Test the Cloud SQL Connector connection."""
    print("\n" + "="*70)
    print("🧪 Testing Cloud SQL Python Connector Setup")
    print("="*70)
    
    # Environment variables
    print("\n📋 Environment Configuration:")
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0665888431")
    region = os.environ.get("CLOUD_SQL_REGION", "asia-south1")
    instance_name = os.environ.get("CLOUD_SQL_INSTANCE", "crystal-inventory-dash")
    user = os.environ.get("CLOUD_SQL_USER", "postgres")
    password = os.environ.get("CLOUD_SQL_PASSWORD")
    database = os.environ.get("CLOUD_SQL_DATABASE", "inventory")
    
    print(f"  Project ID: {project_id}")
    print(f"  Region: {region}")
    print(f"  Instance: {instance_name}")
    print(f"  User: {user}")
    print(f"  Database: {database}")
    print(f"  Password: {'***' if password else '❌ MISSING!'}")
    
    if not password:
        print("\n❌ CLOUD_SQL_PASSWORD environment variable not set!")
        return False
    
    connection_name = f"{project_id}:{region}:{instance_name}"
    print(f"\n🔗 Connection Name: {connection_name}")
    
    # Test connector
    print("\n🔄 Initializing AsyncConnector...")
    try:
        connector = AsyncConnector()
        print("✅ AsyncConnector created")
    except Exception as e:
        print(f"❌ Failed to create AsyncConnector: {e}")
        return False
    
    # Test connection
    print(f"\n🔄 Attempting to connect to {connection_name}...")
    try:
        conn = await connector.connect(
            connection_name,
            driver="asyncpg",
            user=user,
            password=password,
            db=database,
            enable_iam_auth=False,
        )
        print("✅ Connected successfully!")
        
        # Try a simple query
        print("\n🔄 Running test query: SELECT 1...")
        result = await conn.fetchval("SELECT 1")
        print(f"✅ Query result: {result}")
        
        await conn.close()
        await connector.close()
        print("\n✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Connection failed: {type(e).__name__}: {e}")
        print(f"\n💡 Note: If you're on a local machine:")
        print("   1. Cloud SQL Connector requires internet access to GCP")
        print("   2. Make sure your GCP credentials are properly configured")
        print("   3. Run: gcloud auth application-default login")
        print("   4. Verify your GCP project and Cloud SQL instance are accessible")
        await connector.close()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connector())
    if success:
        print("\n" + "="*70)
        print("✅ Cloud SQL Connector is working correctly!")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("❌ Cloud SQL Connector test failed")
        print("="*70)
