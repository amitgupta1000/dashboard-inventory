"""
Database connection for Cloud SQL PostgreSQL.

Instance : gen-lang-client-0665888431:asia-south1:crystal-inventory-dash
Public IP: 35.200.192.16   Port: 5432

Required environment variables:
    DB_NAME   - database name  (e.g. crystal-inventory-dash)
    DB_USER   - database user  (e.g. postgres)
    DB_PASS   - password for DB_USER

Optional:
    DB_HOST   - overrides the default public IP (default: 35.200.192.16)
    DB_PORT   - overrides the default port      (default: 5432)

For production (Cloud Run / GKE), set USE_CLOUD_SQL_CONNECTOR=true and
ensure the service account has the "Cloud SQL Client" role.
"""

import os
import sqlalchemy

DB_HOST = os.environ.get("DB_HOST", "35.200.192.16")
DB_PORT = os.environ.get("DB_PORT", "5432")


def get_engine() -> sqlalchemy.Engine:
    use_connector = os.environ.get("USE_CLOUD_SQL_CONNECTOR", "false").lower() == "true"

    if use_connector:
        from google.cloud.sql.connector import Connector, IPTypes

        _connector = Connector()

        def _get_connection():
            return _connector.connect(
                "gen-lang-client-0665888431:asia-south1:crystal-inventory-dash",
                "pg8000",
                user=os.environ["DB_USER"],
                password=os.environ["DB_PASS"],
                db=os.environ["DB_NAME"],
                ip_type=IPTypes.PUBLIC,
            )

        engine = sqlalchemy.create_engine(
            "postgresql+pg8000://",
            creator=_get_connection,
            pool_size=5,
            max_overflow=2,
            pool_timeout=30,
            pool_recycle=1800,
        )
    else:
        url = sqlalchemy.engine.URL.create(
            drivername="postgresql+psycopg2",
            username=os.environ["DB_USER"],
            password=os.environ["DB_PASS"],
            host=DB_HOST,
            port=int(DB_PORT),
            database=os.environ["DB_NAME"],
        )
        engine = sqlalchemy.create_engine(
            url,
            pool_size=5,
            max_overflow=2,
            pool_timeout=30,
            pool_recycle=1800,
        )

    return engine
