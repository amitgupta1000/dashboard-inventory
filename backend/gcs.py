"""
GCS utility functions for the inventory upload service.

Bucket is read from the GCS_BUCKET_NAME environment variable
(set in backend/.env, default: dashboard-inventory).

All uploaded files are stored under the  uploads/  prefix.
"""

import os
import io
from datetime import datetime, timezone

from google.cloud import storage

BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "dashboard-inventory")
UPLOAD_PREFIX = "uploads/"


def _client() -> storage.Client:
    return storage.Client()


def upload_file(file_bytes: bytes, original_filename: str) -> str:
    """
    Upload raw bytes to GCS.
    Returns the GCS object path (e.g. 'uploads/2026-05-19T12-00-00_stock.xlsx').
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    safe_name = original_filename.replace(" ", "_")
    gcs_path = f"{UPLOAD_PREFIX}{timestamp}_{safe_name}"

    client = _client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(gcs_path)
    blob.upload_from_file(io.BytesIO(file_bytes), content_type="application/octet-stream")
    return gcs_path


def list_uploaded_files() -> list[dict]:
    """
    Return all files in the uploads/ prefix as a list of dicts:
        { gcs_path, filename, uploaded_at }
    Sorted oldest → newest.
    """
    client = _client()
    bucket = client.bucket(BUCKET_NAME)
    blobs = client.list_blobs(bucket, prefix=UPLOAD_PREFIX)

    files = []
    for blob in blobs:
        if blob.name == UPLOAD_PREFIX:   # skip the prefix "folder" entry
            continue
        files.append({
            "gcs_path": blob.name,
            "filename": blob.name.removeprefix(UPLOAD_PREFIX),
            "uploaded_at": blob.time_created.isoformat() if blob.time_created else None,
        })

    files.sort(key=lambda f: f["gcs_path"])
    return files


def download_file(gcs_path: str) -> bytes:
    """Download a GCS object and return its raw bytes."""
    client = _client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(gcs_path)
    return blob.download_as_bytes()
