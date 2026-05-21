"""
Simple GCP Connectivity & Database Setup Test using psycopg2
"""

import os
import sys
from datetime import datetime

try:
    import psycopg2
    print("✅ psycopg2 installed")
except ImportError:
    print("❌ psycopg2 not installed - installing...")
    os.system("pip install psycopg2-binary -q")
    import psycopg2

def test_cloud_sql_with_psycopg2():
    """Test Cloud SQL connectivity and create tables using psycopg2"""
    print("\n" + "="*70)
    print("🔌 TESTING CLOUD SQL WITH PSYCOPG2")
    print("="*70)
    
    # Cloud SQL Instance Details
    HOST = "35.200.192.16"
    DATABASE = "inventory"
    USER = "postgres"
    PASSWORD = os.environ.get("CLOUD_SQL_PASSWORD", "Crystal12345")  # Default for testing - replace with env variable in production
    
    if not PASSWORD:
        print("❌ CLOUD_SQL_PASSWORD not set in environment")
        return False
    
    try:
        # Connect to PostgreSQL
        print(f"Connecting to: {HOST}/{DATABASE}")
        
        conn = psycopg2.connect(
            host=HOST,
            database=DATABASE,
            user=USER,
            password=PASSWORD,
            sslmode="require",
            connect_timeout=10
        )
        
        cursor = conn.cursor()
        
        print(f"✅ Cloud SQL Connected Successfully")
        print(f"   Host: {HOST}")
        print(f"   Database: {DATABASE}")
        print(f"   User: {USER}")
        
        # Create tables
        print("\n📋 Creating Email Service Tables...")
        
        # Jobs table
        cursor.execute("""
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
        cursor.execute("""
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
        cursor.execute("""
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
        cursor.execute("""
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
        cursor.execute("SELECT COUNT(*) FROM jobs")
        result = cursor.fetchone()
        print(f"\n✅ Database Operations Successful")
        print(f"   Total Jobs in Database: {result[0]}")
        
        # List all tables created
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        print(f"\n📊 Tables in 'inventory' database:")
        for table in tables:
            print(f"   - {table[0]}")
        
        # Commit changes
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.Error as e:
        print(f"❌ PostgreSQL Error: {e}")
        print(f"   Error Code: {e.pgcode}")
        return False
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False


def main():
    """Run database test"""
    print("\n" + "🚀 " * 20)
    print("CLOUD SQL CONNECTIVITY TEST")
    print("🚀 " * 20 + "\n")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Python Version: {sys.version.split()[0]}")
    
    success = test_cloud_sql_with_psycopg2()
    
    print("\n" + "="*70)
    if success:
        print("✅ CLOUD SQL SETUP COMPLETE!")
        print("\nNext Steps:")
        print("1. Update .env with DATABASE_URL and credentials")
        print("2. Test your application with: python main.py")
        print("3. Deploy to Cloud Run or App Engine")
    else:
        print("❌ Cloud SQL setup failed - check credentials and network access")
    print("="*70 + "\n")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
