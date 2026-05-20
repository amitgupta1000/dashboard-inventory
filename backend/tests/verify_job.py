"""
Verify job and email records in the SQLite database
"""
import asyncio
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Enable SQLite
os.environ["USE_SQLITE"] = "true"

from backend.database import AsyncSessionLocal, Job, JobSupplierState, SupplierEmail

async def verify_job():
    """Verify job was created and emails were recorded."""
    print("\n" + "="*70)
    print("📊 Verifying Job and Email Records in Database")
    print("="*70)
    
    async with AsyncSessionLocal() as db:
        # Get all jobs
        result = await db.execute(select(Job))
        jobs = result.scalars().all()
        
        print(f"\n📋 Total Jobs: {len(jobs)}")
        
        for job in jobs:
            print(f"\n🔍 Job ID: {job.id}")
            print(f"   Chemical Query: {job.chemical_query}")
            print(f"   User Email: {job.user_email}")
            print(f"   Status: {job.status}")
            print(f"   Created At: {job.created_at}")
            
            # Get suppliers for this job
            suppliers_result = await db.execute(
                select(JobSupplierState).where(JobSupplierState.job_id == job.id)
            )
            suppliers = suppliers_result.scalars().all()
            print(f"\n   📧 Suppliers ({len(suppliers)}):")
            for supplier in suppliers:
                print(f"      • {supplier.email_id} ({supplier.company_name})")
            
            # Get emails for this job
            emails_result = await db.execute(
                select(SupplierEmail).where(SupplierEmail.job_id == job.id)
            )
            emails = emails_result.scalars().all()
            print(f"\n   📨 Emails Sent ({len(emails)}):")
            for email in emails:
                print(f"      • To: {email.to_email}")
                print(f"        Subject: {email.subject}")
                print(f"        Type: {email.email_type}")
                print(f"        Sent At: {email.sent_at}")
    
    print("\n" + "="*70)
    print("✅ Database verification complete!")
    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(verify_job())
