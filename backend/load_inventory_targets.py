"""
Load inventory targets from CSV into CommodityDailyConfig table.

This loader maps CSV columns to the TargetUpdate/CommodityDailyConfig schema:

CSV Column Mapping:
- product_name → commodity lookup by name
- desired_stock_leve → desired_stock_level (note: CSV has typo, fixed in reader)
- min_stock_level → min_stock_level
- max_stock_level → max_stock_level
- target_inventory_holding_days → target_inventory_days
- monthly_sales_target → monthly_sales_target (new field)
- target_storage_cap_days → target_storage_cap_days (new field)
- target_cash_realisation_days → estimated_days_to_sale
- expected_gross_margin → expected_gross_margin
- annual_cost_of_capital → annual_cost_of_capital_rate
- product_name_alias → used for fuzzy matching if product_name lookup fails

Generated fields:
- config_date → today's date
- is_finalized → default False
- notes → null
- cash_realization_rate → null
"""

import pandas as pd
import asyncio
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, create_engine
from backend.database import Commodity, CommodityDailyConfig, Base, DATABASE_URL, SYNC_DATABASE_URL
from difflib import SequenceMatcher


def normalize_product_name(name):
    """Normalize product name for matching: uppercase, trim, collapse spaces."""
    if not name:
        return ""
    return " ".join(name.upper().strip().split())


def find_matching_commodity(product_name, session_sync, aliases=None):
    """
    Find commodity by product_name using exact match first, then fallback to fuzzy matching.
    """
    normalized = normalize_product_name(product_name)
    
    # Try exact match first (case-insensitive, whole name match)
    result = session_sync.execute(
        select(Commodity).filter(
            Commodity.commodity_name.ilike(normalized)
        )
    )
    commodity = result.scalar_one_or_none()
    
    if commodity:
        return commodity
    
    # If no exact match and alias provided, try exact alias match
    if aliases and isinstance(aliases, str):
        alias_normalized = normalize_product_name(aliases)
        result = session_sync.execute(
            select(Commodity).filter(
                Commodity.commodity_name.ilike(alias_normalized)
            )
        )
        commodity = result.scalar_one_or_none()
        if commodity:
            return commodity
    
    # Fuzzy matching as last resort (only if no exact match found)
    result = session_sync.execute(select(Commodity).filter(Commodity.is_active == True))
    commodities = result.scalars().all()
    
    if commodities:
        best_match = max(
            commodities,
            key=lambda c: SequenceMatcher(None, normalized, normalize_product_name(c.commodity_name)).ratio()
        )
        ratio = SequenceMatcher(None, normalized, normalize_product_name(best_match.commodity_name)).ratio()
        if ratio > 0.7:  # Require 70%+ similarity
            return best_match
    
    return None


def _to_float(value):
    """Convert value to float, handling NaN, None, strings, and percentages."""
    if value is None or pd.isna(value):
        return None
    
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        value = value.strip()
        
        # Handle percentage values (e.g., "12%")
        if "%" in value:
            try:
                return float(value.replace("%", "")) / 100
            except ValueError:
                return None
        
        try:
            return float(value)
        except ValueError:
            return None
    
    return None


async def load_inventory_targets_from_csv(file_path: str, config_date: date = None):
    """
    Load inventory targets from CSV into CommodityDailyConfig.
    
    Args:
        file_path: Path to CSV file
        config_date: Date to use for config_date (default: today)
    
    Returns:
        dict with keys: loaded_count, failed_count, errors (list of error dicts)
    """
    if config_date is None:
        config_date = date.today()
    
    # Read CSV with latin-1 encoding and fix column name typo
    df = pd.read_csv(file_path, encoding='latin-1')
    
    # Fix the typo in column name
    if 'desired_stock_leve' in df.columns:
        df.rename(columns={'desired_stock_leve': 'desired_stock_level'}, inplace=True)
    
    # Remove corrupted columns
    df = df[[col for col in df.columns if not col.startswith('Unnamed') and ':' not in col]]
    
    print(f"\n=== Loading Inventory Targets from {file_path} ===")
    print(f"Rows to process: {len(df)}")
    print(f"Config date: {config_date}")
    
    # Setup database connection (using sync session for commodity lookup)
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    loaded_count = 0
    failed_count = 0
    errors = []
    
    async with async_session() as session:
        for idx, row in df.iterrows():
            try:
                # Get commodity
                product_name = row.get('product_name')
                if not product_name or pd.isna(product_name):
                    errors.append({
                        'row': idx + 2,  # +2 for header and 0-indexing
                        'error': 'Missing product_name'
                    })
                    failed_count += 1
                    continue
                
                # Create a sync context just for commodity lookup
                # Note: This is a workaround since we need to query Commodity synchronously
                sync_engine = create_engine(SYNC_DATABASE_URL)
                from sqlalchemy.orm import Session as SyncSession
                sync_session = SyncSession(sync_engine)
                
                commodity = find_matching_commodity(
                    product_name,
                    sync_session,
                    aliases=row.get('product_name_alias')
                )
                sync_session.close()
                
                if not commodity:
                    errors.append({
                        'row': idx + 2,
                        'product_name': product_name,
                        'error': f'No matching commodity found'
                    })
                    failed_count += 1
                    continue
                
                # Check if config already exists for this date
                existing = await session.execute(
                    select(CommodityDailyConfig).filter(
                        (CommodityDailyConfig.commodity_id == commodity.id) &
                        (CommodityDailyConfig.config_date == config_date)
                    )
                )
                config = existing.scalar_one_or_none()
                
                # Parse values
                desired_stock_level = _to_float(row.get('desired_stock_level'))
                min_stock_level = _to_float(row.get('min_stock_level'))
                max_stock_level = _to_float(row.get('max_stock_level'))
                target_inventory_days = _to_float(row.get('target_inventory_holding_days'))
                monthly_sales_target = _to_float(row.get('monthly_sales_target'))
                target_storage_cap_days = _to_float(row.get('target_storage_cap_days'))
                estimated_days_to_sale = _to_float(row.get('target_cash_realisation_days'))
                expected_gross_margin = _to_float(row.get('expected_gross_margin'))
                annual_cost_of_capital_rate = _to_float(row.get('annual_cost_of_capital'))
                
                if config:
                    # Update existing config
                    config.desired_stock_level = desired_stock_level
                    config.min_stock_level = min_stock_level
                    config.max_stock_level = max_stock_level
                    config.target_inventory_days = target_inventory_days
                    config.monthly_sales_target = monthly_sales_target
                    config.target_storage_cap_days = target_storage_cap_days
                    config.estimated_days_to_sale = estimated_days_to_sale
                    config.expected_gross_margin = expected_gross_margin
                    config.annual_cost_of_capital_rate = annual_cost_of_capital_rate
                    config.is_finalized = False
                    config.notes = None
                else:
                    # Create new config
                    config = CommodityDailyConfig(
                        commodity_id=commodity.id,
                        config_date=config_date,
                        desired_stock_level=desired_stock_level,
                        min_stock_level=min_stock_level,
                        max_stock_level=max_stock_level,
                        target_inventory_days=target_inventory_days,
                        monthly_sales_target=monthly_sales_target,
                        target_storage_cap_days=target_storage_cap_days,
                        estimated_days_to_sale=estimated_days_to_sale,
                        cash_realization_rate=None,
                        expected_gross_margin=expected_gross_margin,
                        annual_cost_of_capital_rate=annual_cost_of_capital_rate,
                        is_finalized=False,
                        notes=None
                    )
                    session.add(config)
                
                await session.flush()
                loaded_count += 1
                print(f"✓ Row {idx + 2}: {commodity.commodity_name}")
                
            except Exception as e:
                errors.append({
                    'row': idx + 2,
                    'error': str(e)
                })
                failed_count += 1
                print(f"✗ Row {idx + 2}: {str(e)}")
        
        # Commit all changes
        await session.commit()
    
    await engine.dispose()
    
    print(f"\n=== Load Summary ===")
    print(f"Loaded: {loaded_count}")
    print(f"Failed: {failed_count}")
    
    if errors:
        print(f"\n=== Errors ===")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  Row {error['row']}: {error.get('error', 'Unknown error')}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")
    
    return {
        'loaded_count': loaded_count,
        'failed_count': failed_count,
        'errors': errors
    }


if __name__ == "__main__":
    # Test loading
    result = asyncio.run(
        load_inventory_targets_from_csv("data_files/inventory_targets.csv")
    )
    print(f"\nResult: {result}")
