import os
import logging
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

logger = logging.getLogger(__name__)

# SSL certificates configured in main.py - reuse environment variables
USE_SQLITE = os.environ.get("USE_SQLITE", "false").lower() == "true"

if USE_SQLITE:
    DATABASE_URL = "sqlite+aiosqlite:///./jobs.db"
    logger.info("📊 Using SQLite database: ./jobs.db")
else:
    password = os.environ.get("CLOUD_SQL_PASSWORD")
    if not password:
        raise ValueError("CLOUD_SQL_PASSWORD environment variable is required")
    
    host = os.environ.get("CLOUD_SQL_HOST", "35.200.192.16")
    port = os.environ.get("CLOUD_SQL_PORT", "5432")
    user = os.environ.get("CLOUD_SQL_USER", "postgres")
    database = os.environ.get("CLOUD_SQL_DATABASE", "inventory")
    
    DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
    logger.info(f"📊 Using Cloud SQL: postgresql+asyncpg://{user}:***@{host}:{port}/{database}")

# Main engine for API requests
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=not USE_SQLITE,
    **({"connect_args": {"ssl": "prefer", "server_settings": {"application_name": "crystal-email-service"}}} if not USE_SQLITE else {}),
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Scheduler engine: runs in background thread with separate event loop
scheduler_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=False,  # Prevent connection issues across event loops
    poolclass=None,
    **({"connect_args": {"ssl": "prefer", "server_settings": {"application_name": "crystal-email-service-scheduler"}}} if not USE_SQLITE else {}),
)

SchedulerAsyncSessionLocal = async_sessionmaker(
    scheduler_engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

logger.info("✅ Database initialized")

class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = {"schema": "email_service"} if not USE_SQLITE else {}
    
    id = Column(Integer, primary_key=True, index=True)
    chemical_query = Column(String, index=True)
    user_email = Column(String)  # Email for notifications
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String, default="active") # active, closed
    reminders_sent = Column(Boolean, default=False)
    closed_at = Column(DateTime, nullable=True)
    total_responses = Column(Integer, default=0)
    last_summary_sent_at = Column(DateTime, nullable=True)  # For 12-hour summaries
    closure_notification_sent = Column(Boolean, default=False)  # Track closure report
    
    suppliers = relationship("JobSupplierState", back_populates="job", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="job", cascade="all, delete-orphan")
    emails = relationship("SupplierEmail", back_populates="job", cascade="all, delete-orphan")

class JobSupplierState(Base):
    __tablename__ = "job_supplier_states"
    __table_args__ = {"schema": "email_service"} if not USE_SQLITE else {}
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id" if USE_SQLITE else "email_service.jobs.id"), index=True)
    company_name = Column(String)
    email_id = Column(String, index=True)
    domain = Column(String)
    initial_email_sent_at = Column(DateTime, default=datetime.utcnow)
    replied = Column(Boolean, default=False)
    reply_received_at = Column(DateTime, nullable=True)
    reminder_sent_at = Column(DateTime, nullable=True)
    
    job = relationship("Job", back_populates="suppliers")
    emails = relationship("SupplierEmail", back_populates="supplier_state", cascade="all, delete-orphan")

class SupplierEmail(Base):
    __tablename__ = "supplier_emails"
    __table_args__ = {"schema": "email_service"} if not USE_SQLITE else {}
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id" if USE_SQLITE else "email_service.jobs.id"), index=True)
    supplier_state_id = Column(Integer, ForeignKey("job_supplier_states.id" if USE_SQLITE else "email_service.job_supplier_states.id"), nullable=True)
    email_type = Column(String)  # "outbound" or "inbound"
    from_email = Column(String)
    to_email = Column(String)
    subject = Column(String)
    body = Column(Text)
    sent_at = Column(DateTime, default=datetime.utcnow, index=True)
    gmail_message_id = Column(String, nullable=True, unique=True)
    
    job = relationship("Job", back_populates="emails")
    supplier_state = relationship("JobSupplierState", back_populates="emails")

class Insight(Base):
    __tablename__ = "insights"
    __table_args__ = {"schema": "email_service"} if not USE_SQLITE else {}
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id" if USE_SQLITE else "email_service.jobs.id"), index=True)
    supplier = Column(String, index=True)
    contact_person = Column(String, nullable=True)
    product = Column(String, nullable=True)
    quantity = Column(String, nullable=True)
    price = Column(String, nullable=True)
    delivery_date = Column(String, nullable=True)
    email_body = Column(Text, nullable=True)  # Complete email for drilldowns
    extracted_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship("Job", back_populates="insights")
