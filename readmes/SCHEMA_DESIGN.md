# Inventory Management Database Schema Design

## 📋 Overview

This schema supports a multi-company, multi-commodity inventory management system with financial insights capabilities. It ingests daily inventory reports and generates four types of insights:

1. **Stock Level Warnings** - Alert when inventory falls below desired levels
2. **Mark-to-Market Analysis** - Compare valuations at cost, market, and replacement prices
3. **Working Capital Impact** - Track excess inventory and opportunity costs
4. **Gross Profit Projection** - Estimate profitability based on current holdings

---

## 🏗️ Architecture

### Three-Tier Structure

```
┌─────────────────────────────────────────────────┐
│           MASTER DATA (Static)                  │
│  Companies → Terminals → Commodities            │
│         + CommoditySettings (Targets)           │
├─────────────────────────────────────────────────┤
│     DAILY INVENTORY DATA (Time-Series)          │
│  InventoryReport → InventoryRecord → Vessel     │
│         + PriceHistory (Market Data)            │
├─────────────────────────────────────────────────┤
│        INSIGHTS (Calculated/Analytical)         │
│  StockLevel / MarkToMarket / WorkingCapital     │
│         / GrossProfit + Summaries               │
└─────────────────────────────────────────────────┘
```

---

## 📊 Entity Relationship Diagram

```
┌──────────────┐
│   Company    │────────┐
└──────────────┘        │
       │                │
       │            ┌──────────────┐
       │            │  Terminal    │
       │            └──────────────┘
       │                   │
       │                   └─────────────────┐
       │                                     │
┌──────────────────┐              ┌──────────────────┐
│ CommoditySetting │              │InventoryReport   │
└──────────────────┘              └──────────────────┘
       │                                  │
       │                                  │
┌──────────────┐              ┌──────────────────┐
│  Commodity   │              │InventoryRecord   │
└──────────────┘              └──────────────────┘
       │                              │
       │                             │
┌─────────────────┐            ┌──────────┐
│  PriceHistory   │            │  Vessel  │
└─────────────────┘            └──────────┘


INSIGHTS (based on InventoryRecord):
├─ StockLevelInsight
├─ MarkToMarketInsight
├─ WorkingCapitalInsight
└─ GrossProfitInsight

SUMMARIES:
├─ SummaryByCompany (per day)
└─ SummaryByCommodity (per day, per commodity)
```

---

## 📖 Table Descriptions

### Master Data Tables

#### 1. **Company**
Top-level entity representing a business organization.
- **Key Fields:** company_name, company_code, is_active
- **Purpose:** Groups all operations and financial settings for a single entity
- **Example:** "Company A" operates multiple terminals and trades multiple commodities

#### 2. **Terminal**
Warehouse/storage location operated by a company.
- **Key Fields:** terminal_name, terminal_code, port, location
- **Purpose:** Identifies physical storage locations (AEGIS, GBL, RKT+AHIR, ADANI)
- **Note:** Multiple terminals can store the same commodity for one company

#### 3. **Commodity**
Product/chemical commodity master record.
- **Key Fields:** commodity_name, commodity_code, category, unit_of_measure
- **Purpose:** Master list of all tradeable items (ACETIC ACID, 2-ETHYLHEXANOL, etc.)
- **Note:** Shared across all companies; each company has its own pricing/targets

#### 4. **CommoditySetting**
Company-specific configuration for each commodity.
- **Key Fields:**
  - `desired_stock_level` - Target minimum inventory
  - `min_stock_level` - Critical low-level alert threshold
  - `target_inventory_days` - Optimal days to maintain in stock
  - `cost_price_per_unit` - Internal cost basis
  - `replacement_cost_per_unit` - Current replacement cost
  - `estimated_days_to_sale` - Expected time to complete sale
  - `cash_realization_rate` - % of expected price actually received
  - `expected_gross_margin` - Target profit margin %
- **Purpose:** Allows each company to have different targets for the same commodity
- **Example:** Company A might want 50MT of ACETIC ACID while Company B wants 100MT

---

### Daily Inventory Data Tables

#### 5. **InventoryReport**
Represents one daily inventory submission from a company.
- **Key Fields:**
  - `report_date` - Date of inventory snapshot (e.g., 2026-05-12)
  - `submission_date` - When the report was submitted
  - `file_name` - Original file (e.g., "12-5-26.xlsx")
  - `total_records` - Number of commodities/records in report
  - `total_value` - Aggregate inventory value
  - `is_verified` - QA flag
- **Purpose:** Metadata container for all inventory records in one submission
- **Frequency:** One record per company per day

#### 6. **InventoryRecord**
Individual line item within a daily report.
- **Key Fields:**
  - `physical_stock` - Quantity on hand at terminal
  - `unsold_qty` - Available for sale
  - `sold_qty_pending` - Sold but not yet lifted
  - `num_vessels` - How many vessel batches comprise this lot
  - `earliest_vessel_date` / `latest_vessel_date` - Age of inventory
  - `import_price_per_unit` - Cost from import documentation
  - `inventory_age_days` - Calculated days since oldest vessel
  - `days_of_stock` - Calculated based on target consumption
- **Purpose:** Atomic inventory unit: one commodity at one terminal on one date
- **Example:** "ACETIC ACID at AEGIS terminal on 2026-05-12"
- **Note:** Aggregates multiple vessels into one record

#### 7. **Vessel**
Breakdown of inventory by individual shipment/vessel.
- **Key Fields:**
  - `vessel_name` - Ship identifier
  - `vessel_date` - Arrival/loading date
  - `unsold_qty`, `sold_qty`, `physical_stock` - By vessel
- **Purpose:** Detailed vessel-level tracking for age analysis and drilldowns
- **Example:** "F-6243 BOW ENDEAVOR" arrived 2025-11-22 with 1573.43 MT

#### 8. **PriceHistory**
Daily market price tracking for all commodities.
- **Key Fields:**
  - `price_date` - Date of price snapshot
  - `cost_price` - COGS basis
  - `market_price` - Current selling price
  - `replacement_cost` - Cost to replace inventory
- **Purpose:** Enables mark-to-market analysis and historical trending
- **Frequency:** One record per commodity per day (ideally)

---

### Insights & Analysis Tables

#### 9. **StockLevelInsight**
Stock level warning analysis.
- **Calculation:**
  - `stock_variance = current_stock - desired_stock`
  - `variance_pct = (stock_variance / desired_stock) * 100`
  - `alert_level = "CRITICAL"` if < min_level, `"WARNING"` if below desired, etc.
- **Purpose:** Identifies low-stock items requiring action
- **Example:** ACETIC ACID at AEGIS has 500MT on hand vs 1000MT desired → 50% below target

#### 10. **MarkToMarketInsight**
Valuation analysis at three price points.
- **Calculations:**
  - `value_at_cost = quantity × cost_price`
  - `value_at_market = quantity × market_price`
  - `value_at_replacement = quantity × replacement_cost`
  - `gain_at_market = value_at_market - value_at_cost`
  - `gain_pct_market = (gain_at_market / value_at_cost) × 100`
  - `loss_vs_replacement = value_at_cost - value_at_replacement`
- **Purpose:** Shows unrealized gains/losses and replacement risks
- **Example:** 1000MT at cost $500/MT ($500K) but market is $550/MT → $50K unrealized gain

#### 11. **WorkingCapitalInsight**
Inventory holding cost analysis.
- **Calculations:**
  - `excess_days = current_inventory_days - target_inventory_days`
  - `excess_capital = excess_days × daily_holding_cost`
  - `annual_opportunity_cost = excess_capital × cost_of_capital_rate` (e.g., 8%)
  - `daily_opportunity_cost = annual_opportunity_cost / 365`
- **Purpose:** Quantifies cost of excess inventory
- **Example:** Holding 60 days when target is 30 days → 30 days excess × $500/day = $15K opportunity cost

#### 12. **GrossProfitInsight**
Estimated profitability projection for current inventory.
- **Calculations:**
  - `total_cogs = quantity × cost_per_unit`
  - `expected_revenue = quantity × market_price × cash_realization_rate`
  - `estimated_gross_profit = expected_revenue - total_cogs`
  - `gross_profit_margin_pct = (gross_profit / total_cogs) × 100`
  - `estimated_sale_date = today + estimated_days_to_sale`
- **Purpose:** Projects profit if all current inventory sells at market prices
- **Example:** 1000MT @ $500 cost, $550 market, 15 days to sell, 95% realization
  - COGS: $500K
  - Revenue: 1000 × $550 × 0.95 = $522.5K
  - GP: $22.5K (4.5% margin)

#### 13. **SummaryByCompany**
Aggregated metrics at company level.
- **Purpose:** Dashboard summary showing total company position
- **Updated:** Once per day when InventoryReport is processed
- **Contains:**
  - Total inventory value
  - Alert counts (critical, warning)
  - Aggregate financial metrics

#### 14. **SummaryByCommodity**
Aggregated metrics at commodity level.
- **Purpose:** Show how much each commodity contributes to company position
- **Updated:** Once per day
- **Contains:**
  - Total quantity across all terminals
  - Overall alert status for commodity
  - Financial impact by commodity

---

## 🔄 Data Flow & Processing

### Daily Workflow

```
1. IMPORT EXCEL FILE (e.g., "12-5-26.xlsx")
   ↓
2. CREATE InventoryReport record (date, file_name, etc.)
   ↓
3. FOR EACH ROW IN EXCEL:
   - Identify Company → Terminal → Commodity
   - Create/Update CommoditySetting (first time only)
   - Create InventoryRecord (aggregated by terminal + commodity)
   - Create Vessel records (one per vessel in report)
   ↓
4. FETCH PriceHistory (or prompt for prices if not available)
   ↓
5. CALCULATE INSIGHTS:
   - StockLevelInsight (current vs desired)
   - MarkToMarketInsight (cost vs market vs replacement)
   - WorkingCapitalInsight (excess days × holding cost)
   - GrossProfitInsight (projected profit at current prices)
   ↓
6. AGGREGATE SUMMARIES:
   - SummaryByCompany (total position)
   - SummaryByCommodity (per commodity breakdown)
   ↓
7. FRONTNED DISPLAYS:
   - Analytics panel: summaries + key metrics
   - Insights panel: details of all four insight types
   - Detailed views: drill down to vessel level
```

---

## 📊 Frontend Integration Points

### Analytics Panel (Column 1)
Displays company-level summary from `SummaryByCompany`:
- Total inventory value
- Number of commodities tracked
- Alert summary (critical, warning count)
- Top commodities by value

### Insights Panels (Column 2)

#### Stock Level Warnings
From `StockLevelInsight`:
- List of commodities below desired levels
- Current vs desired stock
- Alert level (critical/warning/caution)

#### Mark-to-Market Gains/Losses
From `MarkToMarketInsight`:
- Unrealized gains at market price
- Risks vs replacement cost
- Margin implications

#### Working Capital Impact
From `WorkingCapitalInsight`:
- Excess inventory days
- Capital tied up
- Daily opportunity cost

#### Gross Profit Projection
From `GrossProfitInsight`:
- Estimated profit if all sells at market
- Realized profit at current realization rate
- Timeline to realization

---

## 🔧 Configuration Panel (Left Drawer)

Allows editing of `CommoditySetting` values:
- Desired stock levels
- Target inventory days
- Cost/replacement prices
- Realization assumptions
- Gross margin targets

---

## 📈 Sample Queries for Frontend

### Total Inventory by Commodity
```sql
SELECT 
    c.commodity_name,
    SUM(ir.physical_stock) as total_qty,
    SUM(ir.physical_stock * p.cost_price) as total_value
FROM inventory_records ir
JOIN commodities c ON ir.commodity_id = c.id
JOIN price_history p ON ir.commodity_id = p.commodity_id
WHERE ir.report_id = {latest_report}
GROUP BY c.id, c.commodity_name
ORDER BY total_value DESC;
```

### Alerts by Company
```sql
SELECT 
    sli.alert_level,
    COUNT(*) as count,
    GROUP_CONCAT(c.commodity_name) as commodities
FROM stock_level_insights sli
JOIN inventory_records ir ON sli.inventory_record_id = ir.id
JOIN commodities c ON ir.commodity_id = c.id
WHERE ir.report_id = {latest_report}
GROUP BY sli.alert_level;
```

### Working Capital Opportunity Cost
```sql
SELECT 
    c.company_name,
    SUM(wci.daily_opportunity_cost) as total_daily_cost,
    SUM(wci.daily_opportunity_cost * 365) as annual_cost
FROM working_capital_insights wci
JOIN inventory_records ir ON wci.inventory_record_id = ir.id
JOIN inventory_reports irpt ON ir.report_id = irpt.id
JOIN companies c ON irpt.company_id = c.id
WHERE ir.report_id = {latest_report}
GROUP BY c.id, c.company_name;
```

---

## 🎯 Next Steps

1. **Create migration scripts** to build these tables in PostgreSQL/SQLite
2. **Build import service** to parse Excel files and populate tables
3. **Implement insight calculation logic** as stored procedures or Python service
4. **Create API endpoints** to serve data to frontend
5. **Build UI components** to visualize insights

