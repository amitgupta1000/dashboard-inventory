"""
Comprehensive Inventory Management Schema
Supports multi-company, multi-commodity analysis with financial insights
"""

import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, Date, Numeric
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
Base = declarative_base()

# ============================================================================
# MASTER DATA TABLES
# ============================================================================

class Company(Base):
    """
    Top-level entity: represents a company with multiple terminals/warehouses
    Example: Company A might operate AEGIS, GBL, RKT+AHIR terminals
    """
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(255), unique=True, index=True)
    company_code = Column(String(50), unique=True, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    terminals = relationship("Terminal", back_populates="company", cascade="all, delete-orphan")
    commodities = relationship("CommoditySetting", back_populates="company", cascade="all, delete-orphan")
    inventory_reports = relationship("InventoryReport", back_populates="company", cascade="all, delete-orphan")


class Terminal(Base):
    """
    Warehouse/Storage location for a company
    Example: AEGIS, GBL (SELORD), RKT+AHIR, ADANI
    """
    __tablename__ = "terminals"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    terminal_name = Column(String(255), index=True)
    terminal_code = Column(String(50), index=True)
    port = Column(String(100))  # MUMBAI, JNPT, KANDLA, HAZIRA
    location = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="terminals")
    inventory_records = relationship("InventoryRecord", back_populates="terminal", cascade="all, delete-orphan")
    
    __table_args__ = (
        # Composite index for company + terminal lookup
    )


class Commodity(Base):
    """
    Product/Chemical commodity master data
    Example: ACETIC ACID, 2-ETHYLHEXANOL, etc.
    """
    __tablename__ = "commodities"
    
    id = Column(Integer, primary_key=True, index=True)
    commodity_name = Column(String(255), unique=True, index=True)
    commodity_code = Column(String(50), unique=True, index=True)
    category = Column(String(100))  # e.g., "Chemicals", "Polymers"
    unit_of_measure = Column(String(50), default="MT")  # MT, Liters, Kg, etc.
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    commodity_settings = relationship("CommoditySetting", back_populates="commodity", cascade="all, delete-orphan")
    inventory_records = relationship("InventoryRecord", back_populates="commodity", cascade="all, delete-orphan")
    price_history = relationship("PriceHistory", back_populates="commodity", cascade="all, delete-orphan")


class CommoditySetting(Base):
    """
    Company-specific settings for each commodity (thresholds, targets, etc.)
    This allows each company to have different targets for the same commodity
    """
    __tablename__ = "commodity_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    commodity_id = Column(Integer, ForeignKey("commodities.id"), index=True)
    
    # Stock Level Management
    desired_stock_level = Column(Float)  # Target minimum stock quantity
    min_stock_level = Column(Float)  # Critical low level for alert
    max_stock_level = Column(Float)  # Maximum optimal stock
    
    # Inventory Days Target
    target_inventory_days = Column(Float, default=30)  # Days of stock to maintain
    
    # Financial Parameters
    cost_price_per_unit = Column(Numeric(12, 4))  # Cost basis for COGS
    replacement_cost_per_unit = Column(Numeric(12, 4))  # Current replacement cost
    estimated_days_to_sale = Column(Float, default=15)  # Expected days to complete sale
    cash_realization_rate = Column(Float, default=1.0)  # % of expected price realized
    
    # Margins
    expected_gross_margin = Column(Float)  # Expected % margin
    
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="commodities")
    commodity = relationship("Commodity", back_populates="commodity_settings")


# ============================================================================
# DAILY INVENTORY DATA TABLES
# ============================================================================

class InventoryReport(Base):
    """
    Daily inventory report submission (one per company per day)
    Contains metadata about the report as a whole
    """
    __tablename__ = "inventory_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    report_date = Column(Date, index=True)  # Date of inventory snapshot
    
    submission_date = Column(DateTime, default=datetime.utcnow)
    submitted_by = Column(String(255), nullable=True)
    file_name = Column(String(255), nullable=True)  # e.g., "12-5-26.xlsx"
    
    total_records = Column(Integer, default=0)
    total_value = Column(Numeric(15, 2), default=0)  # Total inventory value
    
    is_verified = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", back_populates="inventory_reports")
    inventory_records = relationship("InventoryRecord", back_populates="report", cascade="all, delete-orphan")


class InventoryRecord(Base):
    """
    Individual inventory line item
    One record = one commodity at one terminal on one report date
    Aggregates all vessels of that commodity at that location
    """
    __tablename__ = "inventory_records"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relationships to master data
    report_id = Column(Integer, ForeignKey("inventory_reports.id"), index=True)
    terminal_id = Column(Integer, ForeignKey("terminals.id"), index=True)
    commodity_id = Column(Integer, ForeignKey("commodities.id"), index=True)
    
    # Stock Quantities
    physical_stock = Column(Float, index=True)  # Total quantity on hand
    unsold_qty = Column(Float, nullable=True)  # Available for sale
    sold_qty_pending = Column(Float, nullable=True)  # Sold but not lifted
    
    # Vessel/Movement Info
    num_vessels = Column(Integer, default=1)  # How many vessel batches
    earliest_vessel_date = Column(Date, nullable=True)  # Oldest inventory in this lot
    latest_vessel_date = Column(Date, nullable=True)  # Newest inventory
    
    # Cost & Pricing Data
    import_price_per_unit = Column(Numeric(12, 4), nullable=True)  # Cost price from sheet
    
    # Calculated Fields
    inventory_age_days = Column(Integer, nullable=True)  # Days since oldest vessel arrival
    days_of_stock = Column(Float, nullable=True)  # Calculated based on target days/turnover
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    report = relationship("InventoryReport", back_populates="inventory_records")
    terminal = relationship("Terminal", back_populates="inventory_records")
    commodity = relationship("Commodity", back_populates="inventory_records")
    vessels = relationship("Vessel", back_populates="inventory_record", cascade="all, delete-orphan")


class Vessel(Base):
    """
    Individual vessel/shipment breakdown
    Multiple vessels can supply the same commodity to the same terminal
    """
    __tablename__ = "vessels"
    
    id = Column(Integer, primary_key=True, index=True)
    inventory_record_id = Column(Integer, ForeignKey("inventory_records.id"), index=True)
    
    vessel_name = Column(String(255), index=True)
    vessel_date = Column(Date)  # Vessel arrival/loading date
    
    unsold_qty = Column(Float)
    sold_qty = Column(Float, nullable=True)
    physical_stock = Column(Float)
    
    other_qty = Column(Float, nullable=True)  # OTR QTY from report
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    inventory_record = relationship("InventoryRecord", back_populates="vessels")


# ============================================================================
# MARKET PRICING & FINANCIAL DATA TABLES
# ============================================================================

class PriceHistory(Base):
    """
    Daily market price tracking for each commodity
    Supports historical analysis and mark-to-market calculations
    """
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True, index=True)
    commodity_id = Column(Integer, ForeignKey("commodities.id"), index=True)
    price_date = Column(Date, index=True)
    
    # Three price points for mark-to-market analysis
    cost_price = Column(Numeric(12, 4))  # COGS basis
    market_price = Column(Numeric(12, 4))  # Current market/selling price
    replacement_cost = Column(Numeric(12, 4))  # Cost to replace inventory
    
    # Source & verification
    source = Column(String(100))  # "MANUAL", "API", "IMPORT"
    is_verified = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    commodity = relationship("Commodity", back_populates="price_history")


# ============================================================================
# INSIGHTS & ANALYSIS TABLES
# ============================================================================

class StockLevelInsight(Base):
    """
    Stock level warning insights
    Identifies commodities at each terminal that fall below target levels
    """
    __tablename__ = "stock_level_insights"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("inventory_reports.id"), index=True)
    inventory_record_id = Column(Integer, ForeignKey("inventory_records.id"), index=True)
    
    # Comparison data
    current_stock = Column(Float)
    desired_stock = Column(Float)
    stock_variance = Column(Float)  # current - desired
    variance_pct = Column(Float)  # (current - desired) / desired * 100
    
    # Alert level
    alert_level = Column(String(50))  # "CRITICAL", "WARNING", "CAUTION", "OK"
    alert_message = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class MarkToMarketInsight(Base):
    """
    Mark-to-market analysis: compare valuations at different prices
    Shows unrealized gains/losses and margin implications
    """
    __tablename__ = "mark_to_market_insights"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("inventory_reports.id"), index=True)
    inventory_record_id = Column(Integer, ForeignKey("inventory_records.id"), index=True)
    
    # Inventory metrics
    quantity = Column(Float)
    
    # Three valuations
    value_at_cost = Column(Numeric(15, 4))  # At cost price
    value_at_market = Column(Numeric(15, 4))  # At current market price
    value_at_replacement = Column(Numeric(15, 4))  # At replacement cost
    
    # Realized/Unrealized
    gain_at_market = Column(Numeric(15, 4))  # value_at_market - value_at_cost
    gain_pct_market = Column(Float)  # % gain at market
    
    loss_vs_replacement = Column(Numeric(15, 4))  # value_at_cost - value_at_replacement
    replacement_impact = Column(Float)  # % impact
    
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkingCapitalInsight(Base):
    """
    Working capital analysis: inventory days vs target days
    Shows excess capital tied up and opportunity cost
    """
    __tablename__ = "working_capital_insights"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("inventory_reports.id"), index=True)
    inventory_record_id = Column(Integer, ForeignKey("inventory_records.id"), index=True)
    
    # Current state
    current_inventory_days = Column(Float)  # Days of stock on hand
    target_inventory_days = Column(Float)  # Company target
    excess_days = Column(Float)  # current - target
    
    # Capital impact
    inventory_value = Column(Numeric(15, 4))  # Current inventory value at cost
    excess_capital_tied_up = Column(Numeric(15, 4))  # Value of excess inventory
    
    # Opportunity cost
    annual_cost_of_capital_rate = Column(Float, default=0.08)  # 8% or configurable
    annual_opportunity_cost = Column(Numeric(15, 4))  # excess_value * rate
    daily_opportunity_cost = Column(Numeric(10, 4))  # annual / 365
    
    created_at = Column(DateTime, default=datetime.utcnow)


class GrossProfitInsight(Base):
    """
    Estimated gross profit projection for current inventory
    Based on market price, estimated sale timeline, and cash realization
    """
    __tablename__ = "gross_profit_insights"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("inventory_reports.id"), index=True)
    inventory_record_id = Column(Integer, ForeignKey("inventory_records.id"), index=True)
    
    # Base metrics
    quantity = Column(Float)
    cost_per_unit = Column(Numeric(12, 4))
    market_price_per_unit = Column(Numeric(12, 4))
    
    # Sales assumptions
    estimated_days_to_sale = Column(Float)  # Days to complete sale
    cash_realization_rate = Column(Float, default=1.0)  # % of expected price realized
    
    # Calculations
    total_cogs = Column(Numeric(15, 4))  # quantity * cost
    expected_revenue = Column(Numeric(15, 4))  # quantity * market_price * realization_rate
    estimated_gross_profit = Column(Numeric(15, 4))  # expected_revenue - total_cogs
    gross_profit_margin_pct = Column(Float)  # (gross_profit / total_cogs) * 100
    
    # Timing
    estimated_sale_date = Column(Date)  # Projected completion date
    
    created_at = Column(DateTime, default=datetime.utcnow)


class SummaryByCompany(Base):
    """
    Aggregated view: summary metrics at company level
    One record per company per report date
    """
    __tablename__ = "summary_by_company"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    report_date = Column(Date, index=True)
    
    # Stock metrics
    total_inventory_value = Column(Numeric(15, 4))
    total_quantity_by_unit = Column(Float)
    num_commodities = Column(Integer)
    num_terminals = Column(Integer)
    
    # Alerts summary
    critical_alerts = Column(Integer, default=0)
    warning_alerts = Column(Integer, default=0)
    
    # Financial summary
    total_unrealized_gain = Column(Numeric(15, 4))
    total_opportunity_cost = Column(Numeric(15, 4))
    total_estimated_gross_profit = Column(Numeric(15, 4))
    
    created_at = Column(DateTime, default=datetime.utcnow)


class SummaryByCommodity(Base):
    """
    Aggregated view: summary metrics at commodity level across all terminals
    One record per commodity per report date
    """
    __tablename__ = "summary_by_commodity"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    commodity_id = Column(Integer, ForeignKey("commodities.id"), index=True)
    report_date = Column(Date, index=True)
    
    # Stock metrics
    total_quantity = Column(Float)
    total_inventory_value = Column(Numeric(15, 4))
    num_terminals = Column(Integer)
    
    # Insights summary
    stock_alert_level = Column(String(50))  # Overall alert
    avg_inventory_days = Column(Float)
    
    # Financial summary
    total_unrealized_gain = Column(Numeric(15, 4))
    total_opportunity_cost = Column(Numeric(15, 4))
    total_estimated_gross_profit = Column(Numeric(15, 4))
    
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# AUDIT & TRACKING
# ============================================================================

class DataImportLog(Base):
    """
    Track all data imports for audit trail and troubleshooting
    """
    __tablename__ = "data_import_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    import_date = Column(DateTime, default=datetime.utcnow)
    file_name = Column(String(255))
    file_size = Column(Integer)
    
    num_records_imported = Column(Integer)
    num_records_skipped = Column(Integer)
    import_status = Column(String(50))  # "SUCCESS", "PARTIAL", "FAILED"
    
    error_messages = Column(Text, nullable=True)
    imported_by = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
