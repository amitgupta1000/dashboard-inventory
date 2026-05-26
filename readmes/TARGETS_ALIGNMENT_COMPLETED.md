# Inventory Targets CSV Alignment - Completed

## Summary

Successfully aligned `data_files/inventory_targets.csv` with the targets system:
- ✅ 34 commodities created
- ✅ 34 inventory targets loaded into CommodityDailyConfig table
- ✅ CSV column names mapped and fixed
- ✅ Data loaders created and tested

## What Was Done

### 1. CSV Structure Analysis

**File**: `data_files/inventory_targets.csv`
- **Encoding**: Latin-1 (Excel export, not UTF-8)
- **Shape**: 34 rows × 14 columns
- **Format Issues Fixed**:
  - Typo in column: "desired_stock_leve" → "desired_stock_level"
  - Corrupted columns removed: last 3 columns contained garbage text

### 2. Column Mapping

CSV columns mapped to TargetUpdate Pydantic model:

| CSV Column | Target Field | Conversion |
|---|---|---|
| product_name | commodity lookup | Exact matching |
| desired_stock_leve | desired_stock_level | Float conversion |
| min_stock_level | min_stock_level | Float conversion |
| max_stock_level | max_stock_level | Float conversion |
| target_inventory_holding_days | target_inventory_days | Float conversion |
| target_cash_realisation_days | estimated_days_to_sale | Float conversion |
| expected_gross_margin | expected_gross_margin | Float % → decimal |
| annual_cost_of_capital | annual_cost_of_capital_rate | Float % → decimal |
| product_name_alias | fallback for fuzzy matching | N/A |

### 3. Data Loaders Created

#### `backend/load_commodities.py` (50 lines)
- **Purpose**: Load unique product names from CSV as Commodity records
- **Result**: Created 34 commodities with is_active=True
- **Key Feature**: Normalizes names to uppercase before storing

#### `backend/load_inventory_targets.py` (220 lines)
- **Purpose**: Load target values from CSV into CommodityDailyConfig
- **Features**:
  - Exact commodity matching (no substring mismatches)
  - Percentage value handling ("12%" → 0.12)
  - Versioning via config_date (defaults to today)
  - Updates existing config if same date exists
  - Fuzzy matching fallback for close mismatches
- **Result**: 34/34 targets loaded successfully

### 4. Database Impact

**Commodity Table**:
- Created 34 records with product names from CSV
- All uppercase, normalized names
- is_active = true
- commodity_code and category = null (can be updated later)

**CommodityDailyConfig Table**:
- Created 34 records (one per commodity)
- config_date = 2026-05-26 (today's date)
- Populated fields:
  - desired_stock_level
  - min_stock_level
  - max_stock_level
  - target_inventory_days
  - estimated_days_to_sale
  - expected_gross_margin
  - annual_cost_of_capital_rate
- Default fields:
  - is_finalized = false
  - notes = null
  - cash_realization_rate = null (available via API update)

## Commodity List Loaded

1. 2-ETHYLHEXANOL
2. ACETIC ACID
3. BUTYL ACETATE
4. BUTYL DI GLYCOL
5. BUTYL GLYCOL
6. C-9
7. CYCLOHEXANE
8. CYCLOHEXANONE
9. DEG
10. EDC
11. HEXANE
12. IBA
13. IBAC
14. IPA
15. MEK
16. MEG
17. METHANOL
18. MIX XYLENE
19. MIX XYLENE ISOMER
20. MIXED HEPTANE
21. MMA
22. N-PROPANOL
23. NORMAL BUTANOL
24. ORTHO XYLENE
25. PHENOL-M
26. POLYLOL 0434
27. POLYLOL 0656
28. POLYOL 1127
29. PROPIONIC ACID
30. PROPYLENE GLYCOL
31. SH BA (TPU GRADE)
32. STYRENE MONOMER
33. TOLUENE
34. TOLUENE TDI

## API Access

Targets are now accessible via the existing API endpoints:

```bash
# Get all targets
GET /api/targets

# Update a single target
PUT /api/targets/{commodity_id}

# View target history
GET /api/targets/history/{commodity_id}
```

## File References

- [readmes/TARGETS_CSV_MAPPING.md](TARGETS_CSV_MAPPING.md) - Detailed mapping documentation
- [backend/load_commodities.py](../backend/load_commodities.py) - Commodity loader
- [backend/load_inventory_targets.py](../backend/load_inventory_targets.py) - Target loader
- [backend/routes/targets.py](../backend/routes/targets.py) - API endpoints

## Next Steps (Optional)

1. **Enhance commodity data**: Add category, unit_of_measure, and commodity_code via API or CSV
2. **Update config_date**: Load targets for different dates if historical data exists in separate CSVs
3. **Add more targets**: Can continue loading additional targets from other CSV files with same structure
4. **API integration**: Frontend can now call /api/targets to display/edit targets in TargetEditor component

## Lessons Learned

1. **CSV Encoding**: Excel exports often use latin-1, not UTF-8 (use `encoding='latin-1'` parameter)
2. **Exact Matching**: Use exact case-insensitive matching before fuzzy matching to avoid substring collisions
3. **Product Naming**: Multiple commodities can have similar names (e.g., "TOLUENE" vs "TOLUENE TDI") - exact matching essential
4. **Percentage Values**: Format percentages as decimals in database ("12%" → 0.12) for calculations
5. **Versioning Strategy**: Using config_date for versioning enables easy history tracking without explicit version numbers

## Testing Commands

```bash
# Load commodities
python -c "from backend.load_commodities import load_commodities_from_csv; result = load_commodities_from_csv()"

# Load targets
python -c "import asyncio; from backend.load_inventory_targets import load_inventory_targets_from_csv; asyncio.run(load_inventory_targets_from_csv())"

# Verify in database
python -c "
from sqlalchemy.orm import Session
from backend.database import Commodity, CommodityDailyConfig, SYNC_DATABASE_URL, create_engine
engine = create_engine(SYNC_DATABASE_URL)
session = Session(engine)
print(f'Commodities: {session.query(Commodity).count()}')
print(f'Targets: {session.query(CommodityDailyConfig).count()}')
session.close()
"
```
