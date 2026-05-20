import os
import json
import csv
from io import StringIO
import logging

try:
    from google.cloud import storage
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False

logger = logging.getLogger(__name__)
BUCKET_NAME = "crystal-supplier-email-data"

def upload_job_summary(job_id: int, summary_data: dict, insights: list):
    if not GCS_AVAILABLE:
        logger.error("google-cloud-storage is not installed.")
        return False
        
    try:
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        
        # Upload summary JSON
        summary_blob = bucket.blob(f"jobs/{job_id}/summary.json")
        summary_blob.upload_from_string(json.dumps(summary_data, indent=2), content_type="application/json")
        
        # Upload insights CSV
        if insights:
            csv_buffer = StringIO()
            fieldnames = ["Supplier", "Contact_Person", "Product", "Quantity", "Price", "Delivery_Date"]
            writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
            writer.writeheader()
            for row in insights:
                writer.writerow(row)
                
            csv_blob = bucket.blob(f"jobs/{job_id}/insights.csv")
            csv_blob.upload_from_string(csv_buffer.getvalue(), content_type="text/csv")
            
        logger.info(f"Successfully uploaded job {job_id} data to GCS bucket {BUCKET_NAME}")
        return True
    except Exception as e:
        logger.error(f"Failed to upload to GCS: {e}")
        return False
        
def fetch_past_jobs():
    if not GCS_AVAILABLE:
        return []
        
    try:
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        blobs = bucket.list_blobs(prefix="jobs/")
        
        jobs = {}
        for blob in blobs:
            parts = blob.name.split("/")
            if len(parts) >= 3:
                job_id = parts[1]
                if job_id not in jobs:
                    jobs[job_id] = {"id": job_id, "summary": None, "has_insights": False}
                
                if blob.name.endswith("summary.json"):
                    jobs[job_id]["summary"] = json.loads(blob.download_as_string())
                elif blob.name.endswith("insights.csv"):
                    jobs[job_id]["has_insights"] = True
                    
        return list(jobs.values())
    except Exception as e:
        logger.error(f"Failed to fetch past jobs: {e}")
        return []
