"""
API routes for inventory commodity and configuration management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date, datetime, timedelta
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import List, Optional

from backend.database import AsyncSessionLocal
from backend.database import (
    Commodity,
    Terminal,
    CommodityDailyConfig,
    DailyInventoryReport,
    DailyInventoryRecord,
    ProductDailyMetrics
)

router = APIRouter(prefix="/api/inventory", tags=["inventory"])

# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class CommodityCreate(BaseModel):
    commodity_name: str
    commodity_code: Optional[str] = None
    category: Optional[str] = None
    unit_of_measure: str = "MT"
    notes: Optional[str] = None

class CommodityUpdate(BaseModel):
    commodity_name: Optional[str] = None
    commodity_code: Optional[str] = None
    category: Optional[str] = None
    unit_of_measure: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

class CommodityResponse(BaseModel):
    id: int
    commodity_name: str
    commodity_code: Optional[str]
    category: Optional[str]
    unit_of_measure: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TerminalResponse(BaseModel):
    id: int
    terminal_name: str
    terminal_code: Optional[str]
    port: Optional[str]
    region: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True

class CommodityDailyConfigCreate(BaseModel):
    commodity_id: int
    config_date: date = Field(default_factory=date.today)
    cost_price_per_unit: Optional[Decimal] = None
    market_price_per_unit: Optional[Decimal] = None
    replacement_cost_per_unit: Optional[Decimal] = None
    desired_stock_level: Optional[float] = None
    min_stock_level: Optional[float] = None
    max_stock_level: Optional[float] = None
    target_inventory_days: float = 30
    estimated_days_to_sale: float = 15
    cash_realization_rate: float = 0.95
    expected_gross_margin: Optional[float] = None
    annual_cost_of_capital_rate: float = 0.08
    notes: Optional[str] = None

class CommodityDailyConfigUpdate(BaseModel):
    cost_price_per_unit: Optional[Decimal] = None
    market_price_per_unit: Optional[Decimal] = None
    replacement_cost_per_unit: Optional[Decimal] = None
    desired_stock_level: Optional[float] = None
    min_stock_level: Optional[float] = None
    max_stock_level: Optional[float] = None
    target_inventory_days: Optional[float] = None
    estimated_days_to_sale: Optional[float] = None
    cash_realization_rate: Optional[float] = None
    expected_gross_margin: Optional[float] = None
    annual_cost_of_capital_rate: Optional[float] = None
    is_finalized: Optional[bool] = None
    notes: Optional[str] = None

class CommodityDailyConfigResponse(BaseModel):
    id: int
    commodity_id: int
    config_date: date
    cost_price_per_unit: Optional[Decimal]
    market_price_per_unit: Optional[Decimal]
    replacement_cost_per_unit: Optional[Decimal]
    desired_stock_level: Optional[float]
    min_stock_level: Optional[float]
    max_stock_level: Optional[float]
    target_inventory_days: float
    estimated_days_to_sale: float
    cash_realization_rate: float
    expected_gross_margin: Optional[float]
    annual_cost_of_capital_rate: float
    is_finalized: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Product Daily Metrics Schemas
class ProductDailyMetricsCreate(BaseModel):
    product_name: str
    metric_date: date = Field(default_factory=date.today)
    market_price: Optional[Decimal] = None
    replacement_cost: Optional[Decimal] = None
    safety_stock_level: Optional[Decimal] = None
    reorder_stock_level: Optional[Decimal] = None
    target_monthly_sales: Optional[Decimal] = None
    target_storage_cap_days: Optional[Decimal] = None
    target_inventory_days: Optional[Decimal] = None
    target_cash_realization_days: Optional[Decimal] = None

class ProductDailyMetricsUpdate(BaseModel):
    market_price: Optional[Decimal] = None
    replacement_cost: Optional[Decimal] = None
    safety_stock_level: Optional[Decimal] = None
    reorder_stock_level: Optional[Decimal] = None
    target_monthly_sales: Optional[Decimal] = None
    target_storage_cap_days: Optional[Decimal] = None
    target_inventory_days: Optional[Decimal] = None
    target_cash_realization_days: Optional[Decimal] = None

class ProductDailyMetricsResponse(BaseModel):
    id: int
    product_name: str
    metric_date: date
    market_price: Optional[Decimal]
    replacement_cost: Optional[Decimal]
    safety_stock_level: Optional[Decimal]
    reorder_stock_level: Optional[Decimal]
    target_monthly_sales: Optional[Decimal]
    target_storage_cap_days: Optional[Decimal]
    target_inventory_days: Optional[Decimal]
    target_cash_realization_days: Optional[Decimal]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ============================================================================
# DEPENDENCY
# ============================================================================

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# ============================================================================
# COMMODITY MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/commodities", response_model=List[CommodityResponse])
async def list_commodities(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """List all commodities"""
    query = select(Commodity).order_by(Commodity.commodity_name)
    
    if active_only:
        query = query.where(Commodity.is_active == True)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/commodities/{commodity_id}", response_model=CommodityResponse)
async def get_commodity(commodity_id: int, db: AsyncSession = Depends(get_db)):
    """Get specific commodity"""
    result = await db.execute(
        select(Commodity).where(Commodity.id == commodity_id)
    )
    commodity = result.scalar_one_or_none()
    
    if not commodity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commodity {commodity_id} not found"
        )
    return commodity


@router.post("/commodities", response_model=CommodityResponse, status_code=status.HTTP_201_CREATED)
async def create_commodity(
    commodity_data: CommodityCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create new commodity"""
    # Check if already exists
    result = await db.execute(
        select(Commodity).where(Commodity.commodity_name == commodity_data.commodity_name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Commodity '{commodity_data.commodity_name}' already exists"
        )
    
    commodity = Commodity(**commodity_data.dict())
    db.add(commodity)
    await db.commit()
    await db.refresh(commodity)
    return commodity


@router.put("/commodities/{commodity_id}", response_model=CommodityResponse)
async def update_commodity(
    commodity_id: int,
    commodity_data: CommodityUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update commodity"""
    result = await db.execute(
        select(Commodity).where(Commodity.id == commodity_id)
    )
    commodity = result.scalar_one_or_none()
    
    if not commodity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commodity {commodity_id} not found"
        )
    
    update_data = commodity_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(commodity, field, value)
    
    await db.commit()
    await db.refresh(commodity)
    return commodity


# ============================================================================
# DAILY CONFIGURATION ENDPOINTS
# ============================================================================

@router.get("/config/commodities/{config_date}", response_model=List[CommodityDailyConfigResponse])
async def get_daily_configs(
    config_date: date,
    db: AsyncSession = Depends(get_db)
):
    """Get all commodity configs for a specific date"""
    result = await db.execute(
        select(CommodityDailyConfig)
        .where(CommodityDailyConfig.config_date == config_date)
        .order_by(CommodityDailyConfig.commodity_id)
    )
    return result.scalars().all()


@router.get("/config/commodities/latest", response_model=List[CommodityDailyConfigResponse])
async def get_latest_configs(db: AsyncSession = Depends(get_db)):
    """Get latest configuration for each commodity"""
    # Subquery to get max date
    subquery = select(func.max(CommodityDailyConfig.config_date)).correlate(CommodityDailyConfig)
    
    result = await db.execute(
        select(CommodityDailyConfig)
        .where(CommodityDailyConfig.config_date == subquery)
        .order_by(CommodityDailyConfig.commodity_id)
    )
    return result.scalars().all()


@router.get("/config/{config_id}", response_model=CommodityDailyConfigResponse)
async def get_config(config_id: int, db: AsyncSession = Depends(get_db)):
    """Get specific configuration record"""
    result = await db.execute(
        select(CommodityDailyConfig).where(CommodityDailyConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration {config_id} not found"
        )
    return config


@router.post("/config", response_model=CommodityDailyConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_daily_config(
    config_data: CommodityDailyConfigCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create new daily configuration for commodity"""
    # Verify commodity exists
    result = await db.execute(
        select(Commodity).where(Commodity.id == config_data.commodity_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commodity {config_data.commodity_id} not found"
        )
    
    # Check for duplicate config on same date
    result = await db.execute(
        select(CommodityDailyConfig).where(
            (CommodityDailyConfig.commodity_id == config_data.commodity_id) &
            (CommodityDailyConfig.config_date == config_data.config_date)
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Configuration for commodity on {config_data.config_date} already exists"
        )
    
    config = CommodityDailyConfig(**config_data.dict())
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


@router.put("/config/{config_id}", response_model=CommodityDailyConfigResponse)
async def update_daily_config(
    config_id: int,
    config_data: CommodityDailyConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update daily configuration"""
    result = await db.execute(
        select(CommodityDailyConfig).where(CommodityDailyConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration {config_id} not found"
        )
    
    # Prevent updates if finalized
    if config.is_finalized and config_data.is_finalized is not False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update finalized configuration"
        )
    
    update_data = config_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    
    await db.commit()
    await db.refresh(config)
    return config


@router.post("/config/copy-from-previous")
async def copy_configs_from_previous_day(
    config_date: date,
    db: AsyncSession = Depends(get_db)
):
    """
    Auto-populate today's config from yesterday's config
    Called at start of each day in the Configuration Panel
    """
    yesterday = config_date - timedelta(days=1)
    
    # Get all configs from yesterday
    result = await db.execute(
        select(CommodityDailyConfig).where(
            CommodityDailyConfig.config_date == yesterday
        )
    )
    yesterday_configs = result.scalars().all()
    
    if not yesterday_configs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No configurations found for {yesterday}"
        )
    
    created_count = 0
    existing_count = 0
    
    for prev_config in yesterday_configs:
        # Check if today's config already exists
        result = await db.execute(
            select(CommodityDailyConfig).where(
                (CommodityDailyConfig.commodity_id == prev_config.commodity_id) &
                (CommodityDailyConfig.config_date == config_date)
            )
        )
        
        if result.scalar_one_or_none():
            existing_count += 1
            continue
        
        # Create new config by copying from previous day
        new_config = CommodityDailyConfig(
            commodity_id=prev_config.commodity_id,
            config_date=config_date,
            cost_price_per_unit=prev_config.cost_price_per_unit,
            market_price_per_unit=prev_config.market_price_per_unit,
            replacement_cost_per_unit=prev_config.replacement_cost_per_unit,
            desired_stock_level=prev_config.desired_stock_level,
            min_stock_level=prev_config.min_stock_level,
            max_stock_level=prev_config.max_stock_level,
            target_inventory_days=prev_config.target_inventory_days,
            estimated_days_to_sale=prev_config.estimated_days_to_sale,
            cash_realization_rate=prev_config.cash_realization_rate,
            expected_gross_margin=prev_config.expected_gross_margin,
            annual_cost_of_capital_rate=prev_config.annual_cost_of_capital_rate,
            is_finalized=False,  # New configs start unfinialized
            notes=prev_config.notes
        )
        db.add(new_config)
        created_count += 1
    
    await db.commit()
    
    return {
        "message": f"Copied {created_count} configs from {yesterday}, {existing_count} already exist for {config_date}"
    }


# ============================================================================
# PRODUCT DAILY METRICS ENDPOINTS
# ============================================================================

@router.get("/product-metrics/latest", response_model=List[ProductDailyMetricsResponse])
async def get_latest_product_metrics(db: AsyncSession = Depends(get_db)):
    """Get the latest product daily metrics for all products (for form auto-population)."""
    # Get the most recent metric_date
    result = await db.execute(
        select(func.max(ProductDailyMetrics.metric_date)).select_from(ProductDailyMetrics)
    )
    latest_date = result.scalar()
    
    if not latest_date:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No product metrics found in database"
        )
    
    # Get all metrics for that date
    result = await db.execute(
        select(ProductDailyMetrics)
        .where(ProductDailyMetrics.metric_date == latest_date)
        .order_by(ProductDailyMetrics.product_name)
    )
    return result.scalars().all()


@router.get("/product-metrics/{product_name}/latest", response_model=ProductDailyMetricsResponse)
async def get_product_latest_metrics(product_name: str, db: AsyncSession = Depends(get_db)):
    """Get the latest metrics for a specific product."""
    result = await db.execute(
        select(ProductDailyMetrics)
        .where(ProductDailyMetrics.product_name == product_name)
        .order_by(ProductDailyMetrics.metric_date.desc())
        .limit(1)
    )
    metric = result.scalar_one_or_none()
    
    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No metrics found for product: {product_name}"
        )
    
    return metric


@router.get("/product-metrics/{product_name}", response_model=List[ProductDailyMetricsResponse])
async def get_product_metrics_history(product_name: str, db: AsyncSession = Depends(get_db)):
    """Get historical metrics for a specific product."""
    result = await db.execute(
        select(ProductDailyMetrics)
        .where(ProductDailyMetrics.product_name == product_name)
        .order_by(ProductDailyMetrics.metric_date.desc())
    )
    metrics = result.scalars().all()
    
    if not metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No metrics found for product: {product_name}"
        )
    
    return metrics


@router.post("/product-metrics", response_model=ProductDailyMetricsResponse)
async def create_product_metric(
    metric: ProductDailyMetricsCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new product daily metric entry."""
    # Check if entry already exists
    result = await db.execute(
        select(ProductDailyMetrics).where(
            (ProductDailyMetrics.product_name == metric.product_name) &
            (ProductDailyMetrics.metric_date == metric.metric_date)
        )
    )
    
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Metric for {metric.product_name} on {metric.metric_date} already exists"
        )
    
    new_metric = ProductDailyMetrics(**metric.dict())
    db.add(new_metric)
    await db.commit()
    await db.refresh(new_metric)
    
    return new_metric


@router.put("/product-metrics/{metric_id}", response_model=ProductDailyMetricsResponse)
async def update_product_metric(
    metric_id: int,
    updates: ProductDailyMetricsUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing product daily metric entry."""
    result = await db.execute(
        select(ProductDailyMetrics).where(ProductDailyMetrics.id == metric_id)
    )
    metric = result.scalar_one_or_none()
    
    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metric {metric_id} not found"
        )
    
    # Update only provided fields
    update_data = updates.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(metric, field, value)
    
    await db.commit()
    await db.refresh(metric)
    
    return metric


@router.put("/product-metrics/by-date", response_model=List[ProductDailyMetricsResponse])
async def update_product_metrics_bulk(
    new_date: date,
    metrics_updates: List[ProductDailyMetricsUpdate],
    db: AsyncSession = Depends(get_db)
):
    """Bulk update product metrics with a new date for all updated metrics."""
    if not metrics_updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No metrics provided for update"
        )
    
    updated_metrics = []
    
    for idx, updates in enumerate(metrics_updates):
        update_data = updates.dict(exclude_unset=True)
        if not update_data:
            continue
        
        # For each product in the update, create new record with new date
        # Or update existing record
        product_name = update_data.get('product_name')
        
        # Try to find existing metric for new date
        result = await db.execute(
            select(ProductDailyMetrics).where(
                (ProductDailyMetrics.product_name == product_name) &
                (ProductDailyMetrics.metric_date == new_date)
            )
        )
        metric = result.scalar_one_or_none()
        
        if not metric:
            # Create new entry
            metric = ProductDailyMetrics(
                product_name=product_name,
                metric_date=new_date,
                **{k: v for k, v in update_data.items() if k != 'product_name'}
            )
            db.add(metric)
        else:
            # Update existing entry
            for field, value in update_data.items():
                if field != 'product_name':
                    setattr(metric, field, value)
        
        updated_metrics.append(metric)
    
    await db.commit()
    
    # Refresh all metrics
    for metric in updated_metrics:
        await db.refresh(metric)
    
    return updated_metrics
            annual_cost_of_capital_rate=prev_config.annual_cost_of_capital_rate,
            is_finalized=False,  # New configs start unfinialized
            notes=f"Auto-copied from {yesterday}"
        )
        db.add(new_config)
        created_count += 1
    
    await db.commit()
    
    return {
        "status": "success",
        "created": created_count,
        "existing": existing_count,
        "message": f"Copied {created_count} configs from {yesterday}, {existing_count} already exist for {config_date}"
    }


@router.post("/config/{config_id}/finalize")
async def finalize_config(config_id: int, db: AsyncSession = Depends(get_db)):
    """Lock configuration for the day"""
    result = await db.execute(
        select(CommodityDailyConfig).where(CommodityDailyConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration {config_id} not found"
        )
    
    config.is_finalized = True
    await db.commit()
    
    return {
        "status": "finalized",
        "config_id": config_id,
        "config_date": config.config_date
    }
