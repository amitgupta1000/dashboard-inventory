"""
Database connection for inventory management system.

Supports:
- SQLite (local development)
- PostgreSQL via Cloud SQL (production)

Environment variables for SQLite:
    DB_TYPE=sqlite
    DB_PATH=./inventory.db

Environment variables for PostgreSQL:
    DB_TYPE=postgresql (or omit for default)
    DB_NAME   - database name  (e.g. crystal-inventory-dash)
    DB_USER   - database user  (e.g. postgres)
    DB_PASS   - password for DB_USER
    DB_HOST   - server host (default: 35.200.192.16)
    DB_PORT   - server port (default: 5432)

For Cloud SQL production, set USE_CLOUD_SQL_CONNECTOR=true
"""

import os
import sqlalchemy

DB_TYPE = os.environ.get("DB_TYPE", "postgresql").lower()
DB_HOST = os.environ.get("DB_HOST", "35.200.192.16")
DB_PORT = os.environ.get("DB_PORT", "5432")


def get_engine() -> sqlalchemy.Engine:
    """Create SQLAlchemy engine for SQLite or PostgreSQL."""
    
    if DB_TYPE == "sqlite":
        # SQLite for local development
        db_path = os.environ.get("DB_PATH", "./inventory.db")
        url = f"sqlite:///{db_path}"
        engine = sqlalchemy.create_engine(
            url,
            echo=False,
            pool_pre_ping=True,
        )
        # Create tables if they don't exist
        _init_sqlite_schema(engine)
        return engine
    
    # PostgreSQL (default)
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


def _init_sqlite_schema(engine: sqlalchemy.Engine):
    """Initialize SQLite schema for development."""
    with engine.connect() as conn:
        # Create inventory_dashboard table
        conn.execute(sqlalchemy.text("""
            CREATE TABLE IF NOT EXISTS inventory_dashboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_date TEXT,
                company_name TEXT,
                port_name TEXT,
                product_name TEXT,
                physical_stock REAL,
                total_unsold_qty REAL,
                total_sold_qty REAL,
                incoming_vessel_qty REAL,
                avg_import_price_usd REAL,
                avg_price_inr REAL,
                current_market_price REAL,
                replacement_cost REAL,
                stock_value REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Create product_settings table
        conn.execute(sqlalchemy.text("""
            CREATE TABLE IF NOT EXISTS product_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item TEXT UNIQUE NOT NULL,
                safety_stock REAL,
                reorder_point REAL,
                max_storage_days INTEGER,
                max_inventory_days INTEGER,
                monthly_target_volume REAL,
                notes TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        conn.commit()

