"""Creates the 'inventory' database on the Cloud SQL instance if it doesn't exist."""
import os
import sqlalchemy
from backend.db import get_engine

engine = get_engine()
with engine.connect() as conn:
    conn = conn.execution_options(isolation_level="AUTOCOMMIT")
    exists = conn.execute(
        sqlalchemy.text("SELECT 1 FROM pg_database WHERE datname = 'inventory'")
    ).fetchone()
    if not exists:
        conn.execute(sqlalchemy.text("CREATE DATABASE inventory"))
        print("Database created: inventory")
    else:
        print("Database already exists: inventory")
