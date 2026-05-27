from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel
from pathlib import Path
from backend.database import get_db, Commodity, CommodityDailyConfig

router = APIRouter(prefix="/api/targets", tags=["targets"])


def _inherit_or_default(value, previous_value, default=None):
    if value is not None:
        return value
    if previous_value is not None:
        return previous_value
    return default


# Pydantic Models
class TargetUpdate(BaseModel):
    desired_stock_level: Optional[float] = None
    min_stock_level: Optional[float] = None
    max_stock_level: Optional[float] = None
    target_inventory_days: Optional[float] = None
    monthly_sales_target: Optional[float] = None
    target_storage_cap_days: Optional[float] = None
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
    monthly_sales_target: Optional[float]
    target_storage_cap_days: Optional[float]
    estimated_days_to_sale: Optional[float]
    cash_realization_rate: Optional[float]
    expected_gross_margin: Optional[float]
    annual_cost_of_capital_rate: Optional[float]
    is_finalized: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

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


class SeedTargetsRequest(BaseModel):
    file_path: str = "data_files/inventory_targets.csv"
    config_date: Optional[date] = None
    allow_reseed: bool = False


class SeedTargetsResponse(BaseModel):
    success: bool
    message: str
    file_path: str
    config_date: date
    commodities_created: int
    commodities_skipped: int
    target_rows_loaded: int
    target_rows_failed: int


# GET current targets for all commodities
@router.get("", response_model=TargetsListResponse)
async def get_current_targets(db: AsyncSession = Depends(get_db)):
    """Get the most recent targets for all commodities"""
    try:
        # Get latest config per commodity so partial-day edits do not hide other commodities.
        latest_per_commodity = (
            select(
                CommodityDailyConfig.commodity_id,
                func.max(CommodityDailyConfig.config_date).label("latest_config_date"),
            )
            .group_by(CommodityDailyConfig.commodity_id)
            .subquery()
        )

        query = (
            select(CommodityDailyConfig, Commodity.commodity_name)
            .join(
                latest_per_commodity,
                (CommodityDailyConfig.commodity_id == latest_per_commodity.c.commodity_id)
                & (CommodityDailyConfig.config_date == latest_per_commodity.c.latest_config_date),
            )
            .join(Commodity, CommodityDailyConfig.commodity_id == Commodity.id)
            .order_by(Commodity.commodity_name)
        )
        result = await db.execute(query)
        configs = result.all()

        if not configs:
            return TargetsListResponse(
                success=True,
                message="No targets found",
                data=[]
            )

        latest_date = max(config[0].config_date for config in configs)

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
                monthly_sales_target=config[0].monthly_sales_target,
                target_storage_cap_days=config[0].target_storage_cap_days,
                estimated_days_to_sale=config[0].estimated_days_to_sale,
                cash_realization_rate=config[0].cash_realization_rate,
                expected_gross_margin=config[0].expected_gross_margin,
                annual_cost_of_capital_rate=config[0].annual_cost_of_capital_rate,
                is_finalized=config[0].is_finalized,
                notes=config[0].notes,
                created_at=config[0].created_at,
                updated_at=config[0].updated_at,
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

        written_config = existing

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
                desired_stock_level=_inherit_or_default(
                    target.desired_stock_level,
                    prev_config.desired_stock_level if prev_config else None,
                ),
                min_stock_level=_inherit_or_default(
                    target.min_stock_level,
                    prev_config.min_stock_level if prev_config else None,
                ),
                max_stock_level=_inherit_or_default(
                    target.max_stock_level,
                    prev_config.max_stock_level if prev_config else None,
                ),
                target_inventory_days=_inherit_or_default(
                    target.target_inventory_days,
                    prev_config.target_inventory_days if prev_config else None,
                    30,
                ),
                monthly_sales_target=_inherit_or_default(
                    target.monthly_sales_target,
                    prev_config.monthly_sales_target if prev_config else None,
                ),
                target_storage_cap_days=_inherit_or_default(
                    target.target_storage_cap_days,
                    prev_config.target_storage_cap_days if prev_config else None,
                ),
                estimated_days_to_sale=_inherit_or_default(
                    target.estimated_days_to_sale,
                    prev_config.estimated_days_to_sale if prev_config else None,
                    15,
                ),
                cash_realization_rate=_inherit_or_default(
                    target.cash_realization_rate,
                    prev_config.cash_realization_rate if prev_config else None,
                    0.95,
                ),
                expected_gross_margin=_inherit_or_default(
                    target.expected_gross_margin,
                    prev_config.expected_gross_margin if prev_config else None,
                ),
                annual_cost_of_capital_rate=_inherit_or_default(
                    target.annual_cost_of_capital_rate,
                    prev_config.annual_cost_of_capital_rate if prev_config else None,
                    0.08,
                ),
                is_finalized=target.is_finalized,
                notes=_inherit_or_default(
                    target.notes,
                    prev_config.notes if prev_config else None,
                )
            )
            db.add(new_config)
            written_config = new_config

        await db.commit()
        if written_config:
            await db.refresh(written_config)

        return {
            "success": True,
            "message": f"Target updated for {commodity.commodity_name}",
            "commodity_name": commodity.commodity_name,
            "config_date": today,
            "config_id": written_config.id if written_config else None,
            "updated_at": written_config.updated_at.isoformat() if written_config and written_config.updated_at else None,
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
                commodity_name=commodity.commodity_name,
                config_date=config.config_date,
                desired_stock_level=config.desired_stock_level,
                min_stock_level=config.min_stock_level,
                max_stock_level=config.max_stock_level,
                target_inventory_days=config.target_inventory_days,
                monthly_sales_target=config.monthly_sales_target,
                target_storage_cap_days=config.target_storage_cap_days,
                estimated_days_to_sale=config.estimated_days_to_sale,
                cash_realization_rate=config.cash_realization_rate,
                expected_gross_margin=config.expected_gross_margin,
                annual_cost_of_capital_rate=config.annual_cost_of_capital_rate,
                is_finalized=config.is_finalized,
                notes=config.notes,
                created_at=config.created_at,
                updated_at=config.updated_at,
            )
            for config in configs
        ]

        return TargetHistoryResponse(
            success=True,
            message=f"Retrieved {len(history)} historical versions",
            commodity_name=commodity.commodity_name,
            history=history
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")


@router.post("/seed-from-csv", response_model=SeedTargetsResponse)
async def seed_targets_from_csv(
    payload: SeedTargetsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Seed commodities and targets from a local CSV file.

    Intended for one-time bootstrap in a new/live environment.
    """
    csv_path = Path(payload.file_path)
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail=f"CSV file not found: {payload.file_path}")

    existing_target = await db.execute(select(CommodityDailyConfig.id).limit(1))
    if existing_target.scalar_one_or_none() is not None and not payload.allow_reseed:
        raise HTTPException(
            status_code=409,
            detail="Targets already exist. Set allow_reseed=true to seed again.",
        )

    try:
        from backend.load_commodities import load_commodities_from_csv
        from backend.load_inventory_targets import load_inventory_targets_from_csv

        commodity_result = load_commodities_from_csv(payload.file_path)
        target_result = await load_inventory_targets_from_csv(payload.file_path, payload.config_date)
        config_date = payload.config_date or date.today()

        return SeedTargetsResponse(
            success=True,
            message="Targets seeded from CSV",
            file_path=payload.file_path,
            config_date=config_date,
            commodities_created=commodity_result.get("created_count", 0),
            commodities_skipped=commodity_result.get("skipped_count", 0),
            target_rows_loaded=target_result.get("loaded_count", 0),
            target_rows_failed=target_result.get("failed_count", 0),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error seeding targets: {str(e)}")
