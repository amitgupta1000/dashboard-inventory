"""
Database connection for Cloud SQL PostgreSQL.

Instance : gen-lang-client-0665888431:asia-south1:crystal-inventory-dash
Public IP: 35.200.192.16   Port: 5432

Required environment variables:
    DB_NAME   - database name  (e.g. inventory)
    DB_USER   - database user  (e.g. app_user)
    DB_PASS   - password for DB_USER

CLOUD_SQL_INSTANCE defaults to the project instance above but can be
overridden via env var for other environments.

Authentication: uses Application Default Credentials (ADC).
Run `gcloud auth application-default login` locally, or assign a
service account with the "Cloud SQL Client" role in production.
"""

import os
from google.cloud.sql.connector import Connector, IPTypes
import sqlalchemy

CLOUD_SQL_INSTANCE = os.environ.get(
    "CLOUD_SQL_INSTANCE",
    "gen-lang-client-0665888431:asia-south1:crystal-inventory-dash",
)


def _get_connection():
    connector = Connector()
    conn = connector.connect(
        CLOUD_SQL_INSTANCE,
        "pg8000",
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASS"],
        db=os.environ["DB_NAME"],
        ip_type=IPTypes.PUBLIC,
    )
    return conn


def get_engine() -> sqlalchemy.Engine:
    engine = sqlalchemy.create_engine(
        "postgresql+pg8000://",
        creator=_get_connection,
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800,
    )
    return engine
