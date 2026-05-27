import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    inspect,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, relationship

import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

logger = logging.getLogger(__name__)

# Connection setup
USE_SQLITE = os.environ.get("USE_SQLITE", "false").lower() == "true"

if USE_SQLITE:
    DATABASE_URL = "sqlite+aiosqlite:///./jobs.db"
    SYNC_DATABASE_URL = "sqlite:///./jobs.db"
    logger.info("Using SQLite database: ./jobs.db")
else:
    password = os.environ.get("CLOUD_SQL_PASSWORD")
    if not password:
        raise ValueError("CLOUD_SQL_PASSWORD environment variable is required")

    host = os.environ.get("CLOUD_SQL_HOST", "35.200.192.16")
    port = os.environ.get("CLOUD_SQL_PORT", "5432")
    user = os.environ.get("CLOUD_SQL_USER", "postgres")
    database = os.environ.get("CLOUD_SQL_DATABASE", "inventory")

    DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
    SYNC_DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    logger.info(f"Using Cloud SQL: postgresql+asyncpg://{user}:***@{host}:{port}/{database}")


# Async engine/session for API routes
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=not USE_SQLITE,
    **(
        {"connect_args": {"ssl": "prefer", "server_settings": {"application_name": "inventory-api"}}}
        if not USE_SQLITE
        else {}
    ),
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """FastAPI dependency that provides an async DB session per request."""
    async with AsyncSessionLocal() as session:
        yield session

# Background scheduler async engine/session
scheduler_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=False,
    poolclass=None,
    **(
        {"connect_args": {"ssl": "prefer", "server_settings": {"application_name": "inventory-scheduler"}}}
        if not USE_SQLITE
        else {}
    ),
)

SchedulerAsyncSessionLocal = async_sessionmaker(
    scheduler_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


def get_engine():
    """Return a sync SQLAlchemy engine for existing sync code paths."""
    connect_args = {}
    if not USE_SQLITE:
        connect_args = {"sslmode": "require"}
    return create_engine(SYNC_DATABASE_URL, future=True, connect_args=connect_args)


def init_db_schema() -> list[str]:
    """Create all ORM tables and return discovered table names."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    return inspect(engine).get_table_names()


logger.info("Database initialized")


class Commodity(Base):
    __tablename__ = "commodities"

    id = Column(Integer, primary_key=True, index=True)
    commodity_name = Column(String(255), unique=True, index=True, nullable=False)
    commodity_code = Column(String(50), nullable=True)
    category = Column(String(100), nullable=True)
    unit_of_measure = Column(String(50), default="MT")
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    daily_configs = relationship("CommodityDailyConfig", back_populates="commodity", cascade="all, delete-orphan")
    inventory_records = relationship("DailyInventoryRecord", back_populates="commodity", cascade="all, delete-orphan")


class Terminal(Base):
    __tablename__ = "terminals"

    id = Column(Integer, primary_key=True, index=True)
    terminal_name = Column(String(255), index=True, nullable=False)
    terminal_code = Column(String(50), nullable=True)
    port = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    inventory_records = relationship("DailyInventoryRecord", back_populates="terminal", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("terminal_name", "port", name="uq_terminal_port"),
    )


class CommodityDailyConfig(Base):
    __tablename__ = "commodity_daily_configs"

    id = Column(Integer, primary_key=True, index=True)
    commodity_id = Column(Integer, ForeignKey("commodities.id"), index=True, nullable=False)
    config_date = Column(Date, index=True, nullable=False)

    cost_price_per_unit = Column(Numeric(12, 4), nullable=True)
    market_price_per_unit = Column(Numeric(12, 4), nullable=True)
    replacement_cost_per_unit = Column(Numeric(12, 4), nullable=True)

    desired_stock_level = Column(Float, nullable=True)
    min_stock_level = Column(Float, nullable=True)
    max_stock_level = Column(Float, nullable=True)
    target_inventory_days = Column(Float, default=30)
    monthly_sales_target = Column(Float, nullable=True)
    target_storage_cap_days = Column(Float, nullable=True)

    estimated_days_to_sale = Column(Float, default=15)
    cash_realization_rate = Column(Float, default=0.95)
    expected_gross_margin = Column(Float, nullable=True)
    annual_cost_of_capital_rate = Column(Float, default=0.08)

    is_finalized = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    commodity = relationship("Commodity", back_populates="daily_configs")

    __table_args__ = (
        UniqueConstraint("commodity_id", "config_date", name="uq_commodity_date_config"),
    )


class DailyInventoryReport(Base):
    __tablename__ = "daily_inventory_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_date = Column(Date, index=True, nullable=False, unique=True)
    file_name = Column(String(255), nullable=True)
    submitted_by = Column(String(255), nullable=True)
    total_records = Column(Integer, default=0)
    total_value_at_cost = Column(Numeric(15, 2), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    inventory_records = relationship("DailyInventoryRecord", back_populates="report", cascade="all, delete-orphan")


class DailyInventoryRecord(Base):
    __tablename__ = "daily_inventory_records"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("daily_inventory_reports.id"), index=True, nullable=False)
    commodity_id = Column(Integer, ForeignKey("commodities.id"), index=True, nullable=False)
    terminal_id = Column(Integer, ForeignKey("terminals.id"), index=True, nullable=False)
    record_date = Column(Date, index=True, nullable=False)

    physical_stock = Column(Float, nullable=False)
    unsold_qty = Column(Float, nullable=True)
    sold_qty_pending = Column(Float, nullable=True)

    num_vessels = Column(Integer, default=1)
    earliest_vessel_date = Column(Date, nullable=True)
    latest_vessel_date = Column(Date, nullable=True)
    inventory_age_days = Column(Integer, nullable=True)

    cost_price_per_unit = Column(Numeric(12, 4), nullable=True)
    market_price_per_unit = Column(Numeric(12, 4), nullable=True)
    value_at_cost = Column(Numeric(15, 4), nullable=True)
    value_at_market = Column(Numeric(15, 4), nullable=True)
    days_of_stock = Column(Float, nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    report = relationship("DailyInventoryReport", back_populates="inventory_records")
    commodity = relationship("Commodity", back_populates="inventory_records")
    terminal = relationship("Terminal", back_populates="inventory_records")

    __table_args__ = (
        UniqueConstraint("report_id", "commodity_id", "terminal_id", name="uq_report_commodity_terminal"),
    )


class InsightSnapshot(Base):
    __tablename__ = "insight_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("daily_inventory_records.id"), index=True)
    snapshot_date = Column(Date, index=True)
    insight_type = Column(String(50))
    insight_data = Column(Text, nullable=True)
    alert_level = Column(String(50), nullable=True)
    alert_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DataImportLog(Base):
    __tablename__ = "data_import_logs"

    id = Column(Integer, primary_key=True, index=True)
    import_date = Column(DateTime, default=datetime.utcnow, index=True)
    file_name = Column(String(255))
    file_size = Column(Integer)
    num_records_imported = Column(Integer, default=0)
    num_records_skipped = Column(Integer, default=0)
    import_status = Column(String(50))
    error_messages = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class InventoryDetail(Base):
    """Tracks vessel-level inventory details with pricing and stock quantities."""
    __tablename__ = "inventory_detail"

    id = Column(Integer, primary_key=True, index=True)

    # Import & Vessel Information
    date = Column(Date, nullable=False, index=True)
    vessel_date = Column(Date, nullable=True)
    vessel_name = Column(String(255), nullable=True, index=True)

    # Product & Location
    product_name = Column(String(255), nullable=False, index=True)
    port_name = Column(String(255), nullable=True, index=True)
    company_terminal_name = Column(String(255), nullable=True, index=True)
    company_name = Column(String(255), nullable=True, index=True)

    # Stock Quantities (in metric tons or relevant unit)
    unsold_qty = Column(Numeric(15, 3), nullable=True)
    sold_qty_pending_lifting = Column(Numeric(15, 3), nullable=True)
    physical_stock = Column(Numeric(15, 3), nullable=True)
    otr_qty = Column(Numeric(15, 3), nullable=True)  # Over The Road Quantity

    # Pricing & Cost Information
    purchase_price_USD = Column(Numeric(15, 4), nullable=True)
    cif_duty = Column(Numeric(15, 4), nullable=True)  # CIF + Duty cost
    cost_price_INR = Column(Numeric(15, 4), nullable=True)
    average_selling_price_INR = Column(Numeric(15, 4), nullable=True)
    exchange_rate = Column(Numeric(10, 4), nullable=True)  # USD to INR exchange rate

    # Incoming Stock
    incoming_stock = Column(Numeric(15, 3), nullable=True)  # Incoming stock (MT)
    incoming_stock_date = Column(Date, nullable=True)  # Expected arrival date

    # Metrics
    no_of_days_of_stock = Column(Integer, nullable=True)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("date", "vessel_name", "product_name", "company_terminal_name", "company_name", "port_name", 
                        name="uq_inventory_detail_record"),
    )


class MarketDataHVB(Base):
    """Market data from daily price reports."""
    __tablename__ = "market_data_hvb"

    id = Column(Integer, primary_key=True, index=True)
    report_date = Column(Date, index=True, nullable=False)

    product = Column(String(255), index=True, nullable=False)
    company = Column(String(255), nullable=True)
    monthly_volumes = Column(Float, nullable=True)
    ready = Column(Float, nullable=True)
    incoming_period_1 = Column(Float, nullable=True)
    incoming_period_2 = Column(Float, nullable=True)
    physical_stock = Column(Float, nullable=True)
    pending_lifting = Column(Float, nullable=True)
    port_stock = Column(Float, nullable=True)
    replac_dollar = Column(Float, nullable=True)
    replace = Column(Float, nullable=True)
    index = Column(Float, nullable=True)
    market_price = Column(Float, nullable=True)
    selling_p = Column(Float, nullable=True)
    current_month = Column(Float, nullable=True)
    next_month = Column(Float, nullable=True)
    arrival_date = Column(String(100), nullable=True)

    product_name = Column(String(255), index=True, nullable=False)
    port = Column(String(100), index=True, nullable=False)
    usdinr_rate = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
