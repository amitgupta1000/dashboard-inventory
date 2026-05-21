# Inventory Management App - Implementation Roadmap

## 📊 Executive Summary

You're building a sophisticated inventory analytics platform with multi-company, multi-commodity support and financial insights. We've analyzed your sample data (12-5-26.xlsx) and designed a complete database schema.

**Key Stats:**
- ✅ 14 database tables designed
- ✅ 4 insight types architected
- ✅ 2-3 tier hierarchical grouping (Company → Terminal → Commodity → Vessel)
- ⏳ Ready to start implementing import & API logic

---

## 🏗️ Architecture Overview

```
Excel File (Daily Report)
    ↓
Data Import Service (Python)
    ↓
Database (Companies, Terminals, Commodities, Daily Records, Prices)
    ↓
Insight Calculation Engine (4 types)
    ↓
API Endpoints (FastAPI)
    ↓
Frontend Panels (Analytics, Insights, Configuration)
```

---

## 📦 What We've Created

### 1. **inventory_schema.py** - SQLAlchemy Models
14 fully-documented ORM classes covering:
- **Master Data:** Company, Terminal, Commodity, CommoditySetting
- **Daily Data:** InventoryReport, InventoryRecord, Vessel, PriceHistory
- **Insights:** StockLevelInsight, MarkToMarketInsight, WorkingCapitalInsight, GrossProfitInsight
- **Summaries:** SummaryByCompany, SummaryByCommodity
- **Audit:** DataImportLog

### 2. **001_create_inventory_schema.sql** - PostgreSQL Migration
- Complete table definitions with indexes
- 3 pre-built views for common queries
- Constraint definitions (foreign keys, unique constraints)
- Ready to run in your Cloud SQL database

### 3. **SCHEMA_DESIGN.md** - Detailed Documentation
- Table descriptions with examples
- Calculation formulas for each insight type
- Data flow & processing workflow
- Sample queries for frontend integration

### 4. **EXCEL_TO_DB_MAPPING.md** - Import Guidelines
- Column-by-column mapping from Excel to database
- Identified data quality issues (missing cost price, implicit company mapping)
- Aggregation strategy (how to group vessels)
- SQL insert examples
- Python import logic pseudo-code

---

## 🚀 Implementation Phases

### Phase 1: Database Setup (1-2 hours)

**Goal:** Get the schema running in your database

**Tasks:**
1. Run the migration script in PostgreSQL:
   ```sql
   -- In your Cloud SQL database:
   psql -U postgres -d inventory < 001_create_inventory_schema.sql
   ```

2. Verify tables created:
   ```sql
   SELECT table_name FROM information_schema.tables 
   WHERE table_schema = 'public';
   ```

3. Add initial master data:
   ```sql
   INSERT INTO companies (company_name, company_code) 
   VALUES ('Company A', 'COMP_A');
   
   INSERT INTO terminals (company_id, terminal_name, terminal_code, port)
   VALUES 
     (1, 'AEGIS', 'AEGIS_MUM', 'MUMBAI'),
     (1, 'GBL (SELORD)', 'GBL_MUM', 'MUMBAI'),
     (2, 'RKT+AHIR', 'RKT_KANDLA', 'KANDLA'),
     (3, 'ADANI', 'ADANI_HAZ', 'HAZIRA');
   ```

**Files:** `001_create_inventory_schema.sql`

---

### Phase 2: Data Import Service (2-3 hours)

**Goal:** Load Excel file data into database

**Tasks:**
1. Create `backend/services/inventory_import.py`:
   ```python
   from openpyxl import load_workbook
   from backend.inventory_schema import *
   from datetime import datetime
   
   class InventoryImporter:
       def __init__(self, excel_file_path):
           self.file_path = excel_file_path
           self.wb = load_workbook(excel_file_path)
           
       async def import_data(self, company_id):
           """
           1. Parse Excel rows
           2. Group by (terminal, commodity)
           3. Create InventoryReport
           4. Create InventoryRecord (aggregated)
           5. Create Vessel records (detailed)
           6. Log import results
           """
   ```

2. Handle data quality issues:
   - Map terminals to companies (see EXCEL_TO_DB_MAPPING.md)
   - Validate inventory ages, quantities, dates
   - Handle missing cost prices (flag for manual entry)
   - Calculate formulas (inventory_age_days = today - vessel_date)

3. Create API endpoint:
   ```python
   @app.post("/api/inventory/import")
   async def import_inventory_file(file: UploadFile, company_id: int):
       """
       Accepts Excel file upload
       Returns: {success: bool, records_imported: int, errors: []}
       """
   ```

**Files to Create:**
- `backend/services/inventory_import.py`
- `backend/routes/inventory_import.py` (FastAPI endpoint)

---

### Phase 3: Insight Calculation Engine (2-3 hours)

**Goal:** Generate the 4 insight types from inventory data

**Tasks:**
1. Create `backend/services/insight_calculator.py`:

   ```python
   class InsightCalculator:
       def __init__(self, report_id: int, session: AsyncSession):
           self.report_id = report_id
           self.session = session
       
       async def calculate_stock_level_insights(self):
           """
           For each InventoryRecord:
           - Get CommoditySetting (desired_stock_level, min_stock_level)
           - Compare to physical_stock
           - Create StockLevelInsight with alert_level
           """
       
       async def calculate_mark_to_market_insights(self):
           """
           For each InventoryRecord:
           - Fetch latest PriceHistory
           - value_at_cost = qty * cost_price
           - value_at_market = qty * market_price
           - value_at_replacement = qty * replacement_cost
           - Calculate gains and losses
           """
       
       async def calculate_working_capital_insights(self):
           """
           For each InventoryRecord:
           - current_inventory_days = inventory_age_days / target_days
           - excess_days = current - target
           - excess_value = excess_days * daily_holding_cost
           - annual_opportunity_cost = excess_value * 0.08 (cost of capital)
           """
       
       async def calculate_gross_profit_insights(self):
           """
           For each InventoryRecord:
           - total_cogs = qty * cost_price
           - expected_revenue = qty * market_price * realization_rate
           - gross_profit = revenue - cogs
           - margin% = profit / cogs
           """
       
       async def calculate_all_insights(self):
           """Run all 4 calculations for given report_id"""
           
       async def aggregate_summaries(self):
           """Create SummaryByCompany and SummaryByCommodity"""
   ```

2. Create calculation functions for each insight type
3. Add background task to auto-calculate when new report imported
4. Create API endpoints to retrieve insights

**Files to Create:**
- `backend/services/insight_calculator.py`
- `backend/routes/insights.py` (API endpoints)

---

### Phase 4: API Endpoints (1-2 hours)

**Goal:** Serve data to frontend panels

**Key Endpoints:**

```python
# Analytics Panel
GET /api/analytics/summary/{company_id}
  → Returns: SummaryByCompany (total value, alerts, metrics)

GET /api/analytics/by-commodity/{company_id}/{report_date}
  → Returns: List of SummaryByCommodity

# Stock Warnings
GET /api/insights/stock-warnings/{company_id}
  → Returns: StockLevelInsight records sorted by alert_level

# Mark-to-Market
GET /api/insights/mark-to-market/{company_id}
  → Returns: MarkToMarketInsight with gains/losses

# Working Capital
GET /api/insights/working-capital/{company_id}
  → Returns: WorkingCapitalInsight with opportunity costs

# Gross Profit
GET /api/insights/gross-profit/{company_id}
  → Returns: GrossProfitInsight with estimated profits

# Configuration
GET /api/config/commodity-settings/{company_id}
  → Returns: All CommoditySetting for company

PUT /api/config/commodity-settings/{setting_id}
  → Update desired stock, target days, margins, etc.

# Drill-down Detail
GET /api/inventory/records/{inventory_record_id}
  → Returns: InventoryRecord with related Vessel details
```

**Files to Create/Modify:**
- `backend/routes/analytics.py` (new)
- `backend/routes/insights.py` (new)
- `backend/routes/configuration.py` (update existing)
- `backend/main.py` (add new routes)

---

### Phase 5: Frontend UI Components (3-4 hours)

**Goal:** Display insights in the React dashboard

**New Components Needed:**

```typescript
// Column 1: Analytics Panel
<AnalyticsPanel>
  <CompanySummary>  // Total value, commodity count, alert counts
  <TopCommodities>  // Bar chart of top 5 by value
  <AlertSummary>    // Critical/Warning gauge
  
// Column 2: Insights Panels (tabbed)
<InsightsTabs>
  <StockWarningsTab>      // Table of low-stock items
  <MarkToMarketTab>       // Unrealized gains/losses
  <WorkingCapitalTab>     // Excess inventory costs
  <GrossProfitTab>        // Projected profit
  
// Configuration Panel (left drawer - existing)
<ConfigurationPanel>
  <ProductSearch>
  <DesiredStockInput>
  <TargetInventoryDays>
  <CostPriceInput>
  <MarginTargetInput>
```

**Data Flow:**
```
Frontend Component
  ↓ useEffect
  ↓ fetch /api/insights/{type}/{company_id}
  ↓
API returns JSON
  ↓
Transform & Format Data
  ↓
Render with Charts/Tables
```

**Files to Create/Modify:**
- `frontend/src/components/AnalyticsPanel.tsx` (update)
- `frontend/src/components/InsightsPanels.tsx` (new)
- `frontend/src/components/StockWarnings.tsx` (new)
- `frontend/src/components/MarkToMarketChart.tsx` (new)
- `frontend/src/components/WorkingCapitalAnalysis.tsx` (new)
- `frontend/src/components/GrossProfitProjection.tsx` (new)
- `frontend/src/App.tsx` (update to call new APIs)

---

## 📋 Phase Dependencies

```
Phase 1 (Database)
    ↓
Phase 2 (Data Import) + Phase 4 (API)
    ↓
Phase 3 (Insights)
    ↓
Phase 5 (Frontend)
```

You can do Phase 2 & 4 in parallel, but Phase 3 depends on both.

---

## ⚠️ Data Quality Decisions Required

Before starting Phase 2, decide on these:

1. **Company Mapping:** How does terminal → company relationship work?
   - Option A: Hard-code mapping (see EXCEL_TO_DB_MAPPING.md)
   - Option B: Add "Company" column to Excel
   - Option C: Configuration UI to manually map

2. **Missing Cost Prices:**
   - Option A: User manually enters in Configuration Panel (Phase 5)
   - Option B: Import from external price feed API
   - Option C: Use last known historical price

3. **Excel Formula Evaluation:**
   - Option A: Pre-calculate in Excel, paste values
   - Option B: Recalculate on import:
     ```python
     inventory_age_days = (report_date - vessel_date).days
     sold_qty_pending = physical_stock - unsold_qty
     ```

---

## 💾 Estimated Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| 1: Database Setup | 1-2h | None |
| 2: Data Import | 2-3h | Phase 1 ✓ |
| 3: Insights Engine | 2-3h | Phase 1, 2 ✓ |
| 4: API Endpoints | 1-2h | Phase 1, 2, 3 ✓ |
| 5: Frontend UI | 3-4h | Phase 1, 4 ✓ |
| **Total** | **9-14h** | — |

---

## ✅ Success Criteria

Phase 1 Complete:
- [ ] All 14 tables created in PostgreSQL
- [ ] Can insert test data without errors
- [ ] Views work and return correct results

Phase 2 Complete:
- [ ] Can parse Excel file (12-5-26.xlsx)
- [ ] Data imported successfully
- [ ] InventoryRecord aggregation works correctly
- [ ] Vessel-level detail preserved

Phase 3 Complete:
- [ ] All 4 insight types calculate correctly
- [ ] Summary tables populated
- [ ] Results mathematically accurate

Phase 4 Complete:
- [ ] All endpoints return proper JSON
- [ ] Data is filtered correctly by company_id
- [ ] Configuration endpoints save successfully

Phase 5 Complete:
- [ ] All 3 insight panels display
- [ ] Data updates when report imported
- [ ] Configuration changes reflected immediately
- [ ] Charts render correctly

---

## 🔗 File References

| File | Purpose | Status |
|------|---------|--------|
| `inventory_schema.py` | SQLAlchemy ORM | ✅ Created |
| `001_create_inventory_schema.sql` | PostgreSQL migration | ✅ Created |
| `SCHEMA_DESIGN.md` | Documentation | ✅ Created |
| `EXCEL_TO_DB_MAPPING.md` | Import guidelines | ✅ Created |
| `inventory_import.py` | Import service | ⏳ To create |
| `insight_calculator.py` | Calculation engine | ⏳ To create |
| `insights.py` (route) | API endpoints | ⏳ To create |
| Frontend components | UI panels | ⏳ To create |

---

## 📞 Questions to Answer

Before implementing, clarify:

1. **Company Structure:** How many companies will use this system? How many terminals per company?
2. **Reporting Frequency:** Daily Excel files? Real-time API? Batch uploads?
3. **Price Source:** Where do market prices come from? Updated daily?
4. **Thresholds:** What are typical desired stock levels by commodity? Do they vary by company?
5. **Cost of Capital:** What discount rate to use (8% assumed)?
6. **Realization Rate:** Typically, what % of market price is actually realized? (95% assumed)

---

## 🎯 Next Immediate Step

**Recommendation:** Start with Phase 1 (Database)
1. Run the migration script
2. Test with manual inserts
3. Verify 3 views return expected results
4. Then move to Phase 2 (import logic)

Ready to proceed? Let me know which phase you'd like to tackle first!

