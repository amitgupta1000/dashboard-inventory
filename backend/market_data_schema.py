"""
Market Data HVB Schema - Daily price reports from Excel
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, create_engine
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class MarketDataHVB(Base):
    """Market data from HVB daily price reports"""
    __tablename__ = "market_data_hvb"

    id = Column(Integer, primary_key=True, index=True)
    report_date = Column(Date, index=True, nullable=False)
    
    # Original columns (lowercase)
    product = Column(String(255), index=True, nullable=False)  # Original PRODUCT value
    company = Column(String(255), nullable=True)
    monthly_volumes = Column(Float, nullable=True)
    ready = Column(Float, nullable=True)
    second_half_may = Column(Float, nullable=True)
    june_1st_half = Column(Float, nullable=True)
    physical_stock = Column(Float, nullable=True)
    pending_lifting = Column(Float, nullable=True)
    port_stock = Column(Float, nullable=True)
    replac_dollar = Column(Float, nullable=True)  # REPLAC. ($)
    replace = Column(Float, nullable=True)  # REPLACE.
    index = Column(Float, nullable=True)
    market_price = Column(Float, nullable=True)
    selling_p = Column(Float, nullable=True)
    may = Column(Float, nullable=True)
    june = Column(Float, nullable=True)
    arrival_date = Column(String(100), nullable=True)
    
    # Extracted columns
    product_name = Column(String(255), index=True, nullable=False)  # Extracted from PRODUCT split
    port = Column(String(100), index=True, nullable=False)  # Extracted from PRODUCT split
    
    # Exchange rate (same for all rows in a report)
    usdinr_rate = Column(Float, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    class Config:
        from_attributes = True


__all__ = ["MarketDataHVB", "Base"]
