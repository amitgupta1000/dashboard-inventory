"""
GCP Connectivity Test and Database Setup Script

This script:
1. Tests GCP authentication (Service Account & User)
2. Tests Cloud Storage (GCS) access
3. Tests Gmail API access
4. Tests Generative AI (Gemini) API access
5. Creates email service tables in Cloud SQL
6. Tests database connectivity
"""
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__))) 
import json
import asyncio
from datetime import datetime

from dotenv import load_dotenv
# Explicitly point to the .env file in the parent directory (project root)
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test imports
try:
    from google.oauth2 import service_account
    from google.cloud import storage
    import google.generativeai as genai
    from googleapiclient.discovery import build
    print("✅ Google Cloud Python libraries installed")
except ImportError as e:
    print(f"❌ Missing library: {e}")
    sys.exit(1)

try:
    import asyncpg
    import sqlalchemy
    print("✅ Database libraries installed")
except ImportError as e:
    print(f"❌ Missing library: {e}")
    sys.exit(1)


# ============================================================================
# 1. TEST GOOGLE CLOUD AUTHENTICATION
# ============================================================================
def test_gcp_auth():
    """Test GCP service account authentication"""
    print("\n" + "="*70)
    print("1️⃣  TESTING GCP AUTHENTICATION")
    print("="*70)
    
    # Prefer environment variable, fallback to hardcoded path
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", os.path.expanduser(r"C:\gen-lang-client-0665888431-038f11096cad.json"))
    
    if not os.path.exists(creds_path):
        print(f"❌ Credentials file not found: {creds_path}")
        return False
    
    try:
        creds = service_account.Credentials.from_service_account_file(creds_path)
        print(f"✅ Service Account Loaded")
        print(f"   Project: {creds.project_id}")
        print(f"   Email: {creds.service_account_email}")
        return True, creds, creds.project_id
    except Exception as e:
        print(f"❌ Failed to load credentials: {e}")
        return False


# ============================================================================
# 2. TEST CLOUD STORAGE (GCS)
# ============================================================================
def test_gcs(creds, project_id):
    """Test Cloud Storage access"""
    print("\n" + "="*70)
    print("2️⃣  TESTING CLOUD STORAGE (GCS)")
    print("="*70)
    
    bucket_name = "crystal-supplier-email-data"
    
    try:
        client = storage.Client(credentials=creds, project=project_id)
        bucket = client.bucket(bucket_name)
        
        if bucket.exists():
            print(f"✅ Cloud Storage Bucket Accessible")
            print(f"   Bucket: {bucket_name}")
            
            # List objects
            blobs = list(client.list_blobs(bucket_name, max_results=5))
            if blobs:
                print(f"   Objects: {len(blobs)} items found (showing first 5)")
                for blob in blobs:
                    print(f"      - {blob.name}")
            else:
                print(f"   Objects: Empty bucket")
            return True
        else:
            print(f"❌ Cloud Storage Bucket not accessible: {bucket_name}")
            return False
    except Exception as e:
        print(f"❌ Cloud Storage test failed: {e}")
        return False


# ============================================================================
# 3. TEST GMAIL API
# ============================================================================
def test_gmail_api(creds):
    """Test Gmail API access"""
    print("\n" + "="*70)
    print("3️⃣  TESTING GMAIL API")
    print("="*70)
    
    try:
        gmail_creds = creds
        
        # For Domain-Wide Delegation, impersonate a user and define required scopes
        impersonate_user = os.environ.get("GMAIL_IMPERSONATE_USER")
        if impersonate_user:
            print(f"   Impersonating user: {impersonate_user}")
            scopes = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.modify']
            gmail_creds = creds.with_scopes(scopes).with_subject(impersonate_user)
        else:
            print("   ⚠️  GMAIL_IMPERSONATE_USER env var not set. Service account will try to access its own mailbox.")

        # Build Gmail service
        service = build("gmail", "v1", credentials=gmail_creds, cache_discovery=False)
        
        # Get user profile
        profile = service.users().getProfile(userId="me").execute()
        
        print(f"✅ Gmail API Accessible")
        print(f"   Email Address: {profile.get('emailAddress')}")
        print(f"   Messages Total: {profile.get('messagesTotal')}")
        print(f"   Unread Messages: {profile.get('messagesUnread')}")
        return True
    except Exception as e:
        print(f"⚠️  Gmail API test failed (may need domain-wide delegation): {e}")
        return False

# ============================================================================
# 4. TEST GENERATIVE AI (GEMINI)
# ============================================================================
def test_gemini_api():
    """Test Google Generative AI (Gemini) API"""
    print("\n" + "="*70)
    print("4️⃣  TESTING GENERATIVE AI (GEMINI) API")
    print("="*70)
    try:
        from google import genai
    except ImportError:
        logger.warning("google-genai library not found. Insight extraction will be disabled.")
        print("❌ google-genai library not found.")
        return False
    
    try:
        # Initialize Generative AI
        # Try GOOGLE_API_KEY first, then fall back to GOOGLE_GENAI_API_KEY
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_GENAI_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY or GOOGLE_GENAI_API_KEY not set. Insight extraction will be disabled.")
            print("❌ GOOGLE_API_KEY or GOOGLE_GENAI_API_KEY not set.")
            return False
        
        client = genai.Client(api_key=api_key)
        
        # Test with a simple prompt
        model_name = "gemini-2.5-flash-lite"
        response = client.models.generate_content(
            model=model_name,
            contents="what is the capital of France?"
        )
        
        if response.text:
            print(f"✅ Generative AI (Gemini) API Accessible")
            print(f"   Model: {model_name}")
            print(f"   Test Response: {response.text.strip()[:50]}")
            return True
        else:
            print("❌ Gemini API returned empty response")
            return False
    except Exception as e:
        print(f"❌ Gemini API test failed: {e}")
        return False

# ============================================================================
# 5. TEST CLOUD SQL CONNECTIVITY & CREATE TABLES
# ============================================================================
async def test_cloud_sql_and_create_tables():
    """Test Cloud SQL connectivity and create tables for email service"""
    print("\n" + "="*70)
    print("5️⃣  TESTING CLOUD SQL & CREATING TABLES")
    print("="*70)
    
    # Cloud SQL Instance Details
    PROJECT_ID = "gen-lang-client-0665888431"
    INSTANCE_NAME = "crystal-inventory-dash"
    DATABASE = "inventory"
    USER = "postgres"
    PASSWORD = os.environ.get("CLOUD_SQL_PASSWORD", "")
    HOST = "35.200.192.16"  # Public IP
    
    if not PASSWORD:
        print("⚠️  CLOUD_SQL_PASSWORD not set in environment")
        print("   Falling back to default test password...")
        PASSWORD = "Crystal12345" # Default used in other test scripts
    
    try:
        # Connect using asyncpg
        print(f"Connecting to: {HOST}/{DATABASE}")
        
        masked_pwd = f"{PASSWORD[:2]}...{PASSWORD[-2:]}" if len(PASSWORD) > 4 else "***"
        print(f"   Using password: {masked_pwd} (Length: {len(PASSWORD)})")
        
        conn = await asyncpg.connect(
            host=HOST,
            database=DATABASE,
            user=USER,
            password=PASSWORD,
            ssl="require"
        )
        
        print(f"✅ Cloud SQL Connected")
        print(f"   Instance: {INSTANCE_NAME}")
        print(f"   Database: {DATABASE}")
        print(f"   Host: {HOST}")
        
        # Create tables for email service
        print("\n📋 Creating Email Service Tables...")
        
        # Jobs table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id SERIAL PRIMARY KEY,
                user_email VARCHAR(255) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Table 'jobs' created/verified")
        
        # Suppliers table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                id SERIAL PRIMARY KEY,
                job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                email_id VARCHAR(255) NOT NULL,
                email_address VARCHAR(255) NOT NULL,
                company_name VARCHAR(255),
                response_received BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Table 'suppliers' created/verified")
        
        # Insights table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS insights (
                id SERIAL PRIMARY KEY,
                supplier_id INTEGER NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
                supplier_name VARCHAR(255),
                contact_person VARCHAR(255),
                product VARCHAR(255),
                quantity VARCHAR(255),
                price DECIMAL(12, 2),
                delivery_date DATE,
                email_body TEXT,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Table 'insights' created/verified")
        
        # Emails table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS supplier_emails (
                id SERIAL PRIMARY KEY,
                supplier_id INTEGER NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
                email_id VARCHAR(255) NOT NULL,
                subject VARCHAR(255),
                body TEXT,
                received_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Table 'supplier_emails' created/verified")
        
        # Test query
        result = await conn.fetchval("SELECT COUNT(*) FROM jobs")
        print(f"\n✅ Database Operations Successful")
        print(f"   Total Jobs in Database: {result}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Cloud SQL test failed: {e}")
        return False


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================
def main():
    """Run all connectivity tests"""
    print("\n" + "🚀 " * 20)
    print("GCP CONNECTIVITY & DATABASE SETUP TEST")
    print("🚀 " * 20 + "\n")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Python Version: {sys.version.split()[0]}")
    print(f"Working Directory: {os.getcwd()}")
    
    results = {}
    
    # Test 1: GCP Auth
    auth_result = test_gcp_auth()
    if auth_result and len(auth_result) == 3:
        results["GCP Auth"] = True
        _, creds, project_id = auth_result
    else:
        results["GCP Auth"] = False
        return
    
    # Test 2: GCS
    results["Cloud Storage"] = test_gcs(creds, project_id)
    
    # Test 3: Gmail API
    results["Gmail API"] = test_gmail_api(creds)
    
    # Test 4: Gemini API
    results["Gemini API"] = test_gemini_api()
    
    # Test 5: Cloud SQL
    try:
        results["Cloud SQL"] = asyncio.run(test_cloud_sql_and_create_tables())
    except Exception as e:
        print(f"\n❌ Cloud SQL test error: {e}")
        results["Cloud SQL"] = False
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All GCP connectivity tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
