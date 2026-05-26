from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import date
from typing import Optional, List
from pydantic import BaseModel

from backend.database import get_db
from backend.market_data_schema import MarketDataHVB

router = APIRouter(prefix="/api/market-data", tags=["market-data"])


# Pydantic Models
class MarketDataResponse(BaseModel):
    id: int
    report_date: date
    product: str
    product_name: str
    port: str
    company: Optional[str]
    market_price: Optional[float]
    selling_p: Optional[float]
    replac_dollar: Optional[float]
    replace: Optional[float]
    physical_stock: Optional[float]
    port_stock: Optional[float]
    ready: Optional[float]
    usdinr_rate: Optional[float]
    arrival_date: Optional[str]

    class Config:
        from_attributes = True


class MarketDataListResponse(BaseModel):
    success: bool
    message: str
    report_date: date
    count: int
    usdinr_rate: Optional[float]
    data: List[MarketDataResponse]


class MarketDataSummary(BaseModel):
    success: bool
    message: str
    latest_report_date: Optional[date]
    total_records: int
    unique_products: int
    unique_ports: int


# GET latest market data
@router.get("", response_model=MarketDataListResponse)
async def get_market_data(
    db: AsyncSession = Depends(get_db),
    product: Optional[str] = Query(None, description="Filter by product name"),
    port: Optional[str] = Query(None, description="Filter by port"),
    report_date: Optional[date] = Query(None, description="Filter by report date"),
):
    """Get market data with optional filters"""
    try:
        # Build query
        query = select(MarketDataHVB)
        
        if report_date:
            query = query.where(MarketDataHVB.report_date == report_date)
        else:
            # Get latest report date if not specified
            date_query = select(MarketDataHVB.report_date).order_by(
                MarketDataHVB.report_date.desc()
            ).limit(1)
            result = await db.execute(date_query)
            latest_date = result.scalar()
            if latest_date:
                query = query.where(MarketDataHVB.report_date == latest_date)
                report_date = latest_date
        
        if product:
            query = query.where(MarketDataHVB.product_name.ilike(f"%{product}%"))
        
        if port:
            query = query.where(MarketDataHVB.port.ilike(f"%{port}%"))
        
        query = query.order_by(MarketDataHVB.product_name, MarketDataHVB.port)
        
        result = await db.execute(query)
        market_data = result.scalars().all()
        
        # Get USD/INR rate from first record if available
        usdinr_rate = market_data[0].usdinr_rate if market_data else None
        
        data = [
            MarketDataResponse(
                id=md.id,
                report_date=md.report_date,
                product=md.product,
                product_name=md.product_name,
                port=md.port,
                company=md.company,
                market_price=md.market_price,
                selling_p=md.selling_p,
                replac_dollar=md.replac_dollar,
                replace=md.replace,
                physical_stock=md.physical_stock,
                port_stock=md.port_stock,
                ready=md.ready,
                usdinr_rate=md.usdinr_rate,
                arrival_date=md.arrival_date,
            )
            for md in market_data
        ]
        
        filters = []
        if product:
            filters.append(f"product='{product}'")
        if port:
            filters.append(f"port='{port}'")
        
        message = f"Retrieved {len(data)} market data records"
        if filters:
            message += f" ({', '.join(filters)})"
        
        return MarketDataListResponse(
            success=True,
            message=message,
            report_date=report_date,
            count=len(data),
            usdinr_rate=usdinr_rate,
            data=data
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching market data: {str(e)}")


# GET market data summary
@router.get("/summary", response_model=MarketDataSummary)
async def get_market_data_summary(db: AsyncSession = Depends(get_db)):
    """Get summary statistics of market data"""
    try:
        # Get latest report date
        date_query = select(MarketDataHVB.report_date).order_by(
            MarketDataHVB.report_date.desc()
        ).limit(1)
        result = await db.execute(date_query)
        latest_date = result.scalar()
        
        # Get total count
        count_query = select(MarketDataHVB)
        result = await db.execute(count_query)
        total_records = len(result.scalars().all())
        
        # Get unique products
        product_query = select(MarketDataHVB.product_name).distinct()
        result = await db.execute(product_query)
        unique_products = len(result.scalars().all())
        
        # Get unique ports
        port_query = select(MarketDataHVB.port).distinct()
        result = await db.execute(port_query)
        unique_ports = len(result.scalars().all())
        
        return MarketDataSummary(
            success=True,
            message="Market data summary retrieved",
            latest_report_date=latest_date,
            total_records=total_records,
            unique_products=unique_products,
            unique_ports=unique_ports,
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching summary: {str(e)}")


# GET market data by product
@router.get("/product/{product_name}", response_model=MarketDataListResponse)
async def get_market_data_by_product(
    product_name: str,
    db: AsyncSession = Depends(get_db),
):
    """Get market data for a specific product across all ports"""
    try:
        query = select(MarketDataHVB).where(
            MarketDataHVB.product_name.ilike(f"%{product_name}%")
        ).order_by(MarketDataHVB.port)
        
        result = await db.execute(query)
        market_data = result.scalars().all()
        
        if not market_data:
            return MarketDataListResponse(
                success=True,
                message=f"No data found for product '{product_name}'",
                report_date=None,
                count=0,
                usdinr_rate=None,
                data=[]
            )
        
        report_date = market_data[0].report_date
        usdinr_rate = market_data[0].usdinr_rate
        
        data = [
            MarketDataResponse(
                id=md.id,
                report_date=md.report_date,
                product=md.product,
                product_name=md.product_name,
                port=md.port,
                company=md.company,
                market_price=md.market_price,
                selling_p=md.selling_p,
                replac_dollar=md.replac_dollar,
                replace=md.replace,
                physical_stock=md.physical_stock,
                port_stock=md.port_stock,
                ready=md.ready,
                usdinr_rate=md.usdinr_rate,
                arrival_date=md.arrival_date,
            )
            for md in market_data
        ]
        
        return MarketDataListResponse(
            success=True,
            message=f"Retrieved {len(data)} records for {product_name}",
            report_date=report_date,
            count=len(data),
            usdinr_rate=usdinr_rate,
            data=data
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")
