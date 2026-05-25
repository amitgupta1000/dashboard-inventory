from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel
from backend.database import get_db, Commodity, CommodityDailyConfig

router = APIRouter(prefix="/api/targets", tags=["targets"])


# Pydantic Models
class TargetUpdate(BaseModel):
    desired_stock_level: Optional[float] = None
    min_stock_level: Optional[float] = None
    max_stock_level: Optional[float] = None
    target_inventory_days: Optional[float] = None
    estimated_days_to_sale: Optional[float] = None
    cash_realization_rate: Optional[float] = None
    expected_gross_margin: Optional[float] = None
    annual_cost_of_capital_rate: Optional[float] = None
    is_finalized: Optional[bool] = False
    notes: Optional[str] = None


class TargetResponse(BaseModel):
    id: int
    commodity_id: int
    commodity_name: str
    config_date: date
    desired_stock_level: Optional[float]
    min_stock_level: Optional[float]
    max_stock_level: Optional[float]
    target_inventory_days: Optional[float]
    estimated_days_to_sale: Optional[float]
    cash_realization_rate: Optional[float]
    expected_gross_margin: Optional[float]
    annual_cost_of_capital_rate: Optional[float]
    is_finalized: bool
    notes: Optional[str]

    class Config:
        from_attributes = True


class TargetsListResponse(BaseModel):
    success: bool
    message: str
    data: List[TargetResponse]


class TargetHistoryResponse(BaseModel):
    success: bool
    message: str
    commodity_name: str
    history: List[TargetResponse]


# GET current targets for all commodities
@router.get("", response_model=TargetsListResponse)
async def get_current_targets(db: AsyncSession = Depends(get_db)):
    """Get the most recent targets for all commodities"""
    try:
        # Get latest config_date
        latest_date_query = select(CommodityDailyConfig.config_date).order_by(
            desc(CommodityDailyConfig.config_date)
        ).limit(1)
        result = await db.execute(latest_date_query)
        latest_date = result.scalar()

        if not latest_date:
            return TargetsListResponse(
                success=True,
                message="No targets found",
                data=[]
            )

        # Get all commodities with their latest config
        query = (
            select(CommodityDailyConfig, Commodity.name)
            .join(Commodity, CommodityDailyConfig.commodity_id == Commodity.id)
            .where(CommodityDailyConfig.config_date == latest_date)
            .order_by(Commodity.name)
        )
        result = await db.execute(query)
        configs = result.all()

        targets = [
            TargetResponse(
                id=config[0].id,
                commodity_id=config[0].commodity_id,
                commodity_name=config[1],
                config_date=config[0].config_date,
                desired_stock_level=config[0].desired_stock_level,
                min_stock_level=config[0].min_stock_level,
                max_stock_level=config[0].max_stock_level,
                target_inventory_days=config[0].target_inventory_days,
                estimated_days_to_sale=config[0].estimated_days_to_sale,
                cash_realization_rate=config[0].cash_realization_rate,
                expected_gross_margin=config[0].expected_gross_margin,
                annual_cost_of_capital_rate=config[0].annual_cost_of_capital_rate,
                is_finalized=config[0].is_finalized,
                notes=config[0].notes
            )
            for config in configs
        ]

        return TargetsListResponse(
            success=True,
            message=f"Retrieved {len(targets)} targets as of {latest_date}",
            data=targets
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching targets: {str(e)}")


# PUT update targets (creates new version)
@router.put("/{commodity_id}")
async def update_target(
    commodity_id: int,
    target: TargetUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update target for commodity (creates new version with today's config_date)"""
    try:
        # Verify commodity exists
        commodity_query = select(Commodity).where(Commodity.id == commodity_id)
        result = await db.execute(commodity_query)
        commodity = result.scalar()

        if not commodity:
            raise HTTPException(status_code=404, detail="Commodity not found")

        # Check if already have config for today
        today = date.today()
        existing_query = select(CommodityDailyConfig).where(
            (CommodityDailyConfig.commodity_id == commodity_id) &
            (CommodityDailyConfig.config_date == today)
        )
        result = await db.execute(existing_query)
        existing = result.scalar()

        if existing:
            # Update existing config
            for field, value in target.dict(exclude_unset=True).items():
                setattr(existing, field, value)
            db.add(existing)
        else:
            # Get previous config to inherit values
            prev_query = (
                select(CommodityDailyConfig)
                .where(CommodityDailyConfig.commodity_id == commodity_id)
                .order_by(desc(CommodityDailyConfig.config_date))
                .limit(1)
            )
            result = await db.execute(prev_query)
            prev_config = result.scalar()

            # Create new config version
            new_config = CommodityDailyConfig(
                commodity_id=commodity_id,
                config_date=today,
                desired_stock_level=target.desired_stock_level or (
                    prev_config.desired_stock_level if prev_config else None
                ),
                min_stock_level=target.min_stock_level or (
                    prev_config.min_stock_level if prev_config else None
                ),
                max_stock_level=target.max_stock_level or (
                    prev_config.max_stock_level if prev_config else None
                ),
                target_inventory_days=target.target_inventory_days or (
                    prev_config.target_inventory_days if prev_config else 30
                ),
                estimated_days_to_sale=target.estimated_days_to_sale or (
                    prev_config.estimated_days_to_sale if prev_config else 15
                ),
                cash_realization_rate=target.cash_realization_rate or (
                    prev_config.cash_realization_rate if prev_config else 0.95
                ),
                expected_gross_margin=target.expected_gross_margin or (
                    prev_config.expected_gross_margin if prev_config else None
                ),
                annual_cost_of_capital_rate=target.annual_cost_of_capital_rate or (
                    prev_config.annual_cost_of_capital_rate if prev_config else 0.08
                ),
                is_finalized=target.is_finalized,
                notes=target.notes
            )
            db.add(new_config)

        await db.commit()

        return {
            "success": True,
            "message": f"Target updated for {commodity.name}",
            "commodity_name": commodity.name,
            "config_date": today
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating target: {str(e)}")


# GET target history for a commodity
@router.get("/history/{commodity_id}", response_model=TargetHistoryResponse)
async def get_target_history(
    commodity_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all historical versions of targets for a commodity"""
    try:
        # Verify commodity exists
        commodity_query = select(Commodity).where(Commodity.id == commodity_id)
        result = await db.execute(commodity_query)
        commodity = result.scalar()

        if not commodity:
            raise HTTPException(status_code=404, detail="Commodity not found")

        # Get all configs for this commodity, ordered by date descending
        query = (
            select(CommodityDailyConfig)
            .where(CommodityDailyConfig.commodity_id == commodity_id)
            .order_by(desc(CommodityDailyConfig.config_date))
        )
        result = await db.execute(query)
        configs = result.scalars().all()

        history = [
            TargetResponse(
                id=config.id,
                commodity_id=config.commodity_id,
                commodity_name=commodity.name,
                config_date=config.config_date,
                desired_stock_level=config.desired_stock_level,
                min_stock_level=config.min_stock_level,
                max_stock_level=config.max_stock_level,
                target_inventory_days=config.target_inventory_days,
                estimated_days_to_sale=config.estimated_days_to_sale,
                cash_realization_rate=config.cash_realization_rate,
                expected_gross_margin=config.expected_gross_margin,
                annual_cost_of_capital_rate=config.annual_cost_of_capital_rate,
                is_finalized=config.is_finalized,
                notes=config.notes
            )
            for config in configs
        ]

        return TargetHistoryResponse(
            success=True,
            message=f"Retrieved {len(history)} historical versions",
            commodity_name=commodity.name,
            history=history
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")
