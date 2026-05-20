# Inventory Management Dashboard - Complete Workflow Guide

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [Data Input](#data-input)
3. [Data Processing Pipeline](#data-processing-pipeline)
4. [Database Architecture](#database-architecture)
5. [Intelligence & Analytics Layer](#intelligence--analytics-layer)
6. [Frontend Visualization](#frontend-visualization)
7. [Complete Workflow Examples](#complete-workflow-examples)
8. [API Reference](#api-reference)
9. [Deployment & Setup](#deployment--setup)

---

## 🏗️ System Overview

This is a **3-tier inventory intelligence system** that transforms raw Excel data into actionable business insights.

```
┌─────────────────────────────────────────────────────────────────┐
│                    INVENTORY MANAGEMENT DASHBOARD               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Input Layer      Processing Layer      Storage Layer      Insight Layer      UI Layer
│  ───────────────  ───────────────────   ──────────────    ────────────────   ─────────
│                                                                   │
│  stock_report    FastAPI Backend       PostgreSQL        SQL Views &       React/Vite
│  .xlsx (GCS) ──► Parser & Validator ──► Cloud SQL ────► Functions ────► Tailwind
│                                                         (Intelligence)      CSS
│  Product         Data Cleaning         Inventory        Product Analysis
│  Settings ────►  Data Mapping          Tables           Alerts & Narrative
│                  Deduplication                         Shipment Analytics
│                  Validation
│
└─────────────────────────────────────────────────────────────────┘
```

---

## 📥 Data Input

### 1. Primary Data Source: Excel File
**Location**: `stock_report.xlsx` (uploaded to Google Cloud Storage)
**Worksheet**: `STOCK SHEET`

**Expected Columns**:
```
- VESSEL ARRIVAL DATE
- Company Name (STPL, KRL, etc.)
- PORT NAME (KANDLA, etc.)
- VESSEL NAME
- PRODUCT NAME (Toluene, IPA, DEG, Mixed Xylene, etc.)
- NO OF DAYS OF STOCK
- BL QTY (Bill of Lading)
- OTR QTY (Over The Road)
- PHYSICAL STOCK ON PORT
- TOTAL UNSOLD QTY
- TOTAL SOLD QTY
- Avg. Per MT PRICE (inclusive) INR
- IMPORT PRICE ($ / MT)
- EXCHANGE RATE
- PHYSICAL QTY. STOCK VALUE
- INCOMING VESSEL QTY
- CURRENT MARKET PRICE
- REPLACEMENT COST
```

### 2. Secondary Data Source: Product Settings
**Origin**: Dashboard UI (`Product Settings` tab)
**Purpose**: Define thresholds and targets for inventory management

**Fields per Product**:
- Safety Stock (MT) - Stock level triggering CRITICAL alert
- Reorder Point (MT) - Stock level triggering WARNING alert
- Max Storage Days - Maximum days inventory can stay in storage
- Max Inventory Days - Inventory cycle window for projected sales
- Monthly Target Volume (MT) - Expected monthly consumption
- Notes - Additional product-specific notes

---

## 🔄 Data Processing Pipeline

### Step 1: File Upload & Validation
```
Excel File (GCS)
    ↓
[Python: pandas.read_excel()]
    ↓
Parse "STOCK SHEET" worksheet
    ↓
Validate column structure
    ↓
Check for required fields
    ↓
Remove blank rows & duplicates
```

**Code Location**: `main.py` - `_parse_excel()` function

### Step 2: Data Mapping & Type Conversion
```
Raw DataFrame
    ↓
Map Excel columns → Database columns:
├─ VESSEL ARRIVAL DATE → vessel_arrival_date (DATE)
├─ Company Name → company_name (VARCHAR)
├─ PORT NAME → port_name (VARCHAR)
├─ PRODUCT NAME → product_name (VARCHAR)
├─ PHYSICAL STOCK ON PORT → physical_stock (NUMERIC)
├─ TOTAL UNSOLD QTY → total_unsold_qty (NUMERIC)
├─ TOTAL SOLD QTY → total_sold_qty (NUMERIC)
├─ Avg. Per MT PRICE → avg_per_mt_price_inr (NUMERIC)
├─ IMPORT PRICE → import_price_usd_mt (NUMERIC)
├─ EXCHANGE RATE → exchange_rate (NUMERIC)
├─ PHYSICAL QTY. STOCK VALUE → physical_qty_value (NUMERIC)
├─ INCOMING VESSEL QTY → incoming_vessel_qty (NUMERIC)
├─ CURRENT MARKET PRICE → current_market_price (NUMERIC)
└─ REPLACEMENT COST → replacement_cost (NUMERIC)
    ↓
Convert data types:
├─ Dates → datetime.date
├─ Numbers → DECIMAL/FLOAT
└─ Text → VARCHAR
    ↓
Handle missing values (NULL handling)
    ↓
Validate numeric ranges
```

**Code Location**: `main.py` - `_parse_excel()` function, numeric conversion loop

### Step 3: Duplicate Detection & Deduplication
```
Parsed Records
    ↓
Check processed_files table:
├─ File hash (SHA256) - Prevents re-processing same file
├─ GCS path - Unique identifier
└─ Timestamp - When file was processed
    ↓
If file not previously processed:
    → Mark as new file
    → Continue to insertion
    ↓
If file already processed:
    → Skip (prevents duplicates)
    → Log skip event
```

**Code Location**: `main.py` - `refresh_inventory()` endpoint

### Step 4: Database Insertion
```
Validated Records
    ↓
INSERT INTO inventory_dashboard (
    vessel_arrival_date, company_name, port_name, product_name,
    physical_stock_on_port, total_unsold_qty, total_sold_qty,
    avg_per_mt_price_inr, import_price_usd_mt, exchange_rate,
    physical_qty_value, incoming_vessel_qty,
    current_market_price, replacement_cost
)
    ↓
Record insertion in processed_files table:
├─ gcs_path
├─ filename
├─ file_hash
├─ rows_imported
└─ processed_at timestamp
    ↓
Transaction commit
```

**Code Location**: `main.py` - `_insert_inventory()` function

---

## 🗄️ Database Architecture

### 1. Main Inventory Table: `inventory_dashboard`
Stores all shipment records with:
- Record metadata (dates, locations, products)
- Quantities (physical stock, sold, unsold, incoming)
- Pricing (import price, market price, replacement cost)
- Calculated fields (status, computed import in INR)

```sql
CREATE TABLE inventory_dashboard (
    id SERIAL PRIMARY KEY,
    vessel_arrival_date DATE,
    company_name VARCHAR(255),
    port_name VARCHAR(255),
    product_name VARCHAR(255) NOT NULL,
    physical_stock_on_port NUMERIC(15, 3),
    total_unsold_qty NUMERIC(15, 3),
    total_sold_qty NUMERIC(15, 3),
    avg_per_mt_price_inr NUMERIC(15, 4),
    import_price_usd_mt NUMERIC(15, 4),
    exchange_rate NUMERIC(10, 4),
    physical_qty_value NUMERIC(18, 2),
    incoming_vessel_qty NUMERIC(15, 3),
    current_market_price NUMERIC(15, 4),
    replacement_cost NUMERIC(15, 4),
    -- Computed fields
    stock_status VARCHAR(20),
    calculated_import_inr NUMERIC(15, 4),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2. Product Settings Table: `product_settings`
Stores user-configured thresholds and targets:

```sql
CREATE TABLE product_settings (
    id SERIAL PRIMARY KEY,
    item VARCHAR(255) UNIQUE,
    safety_stock NUMERIC(15, 3),
    reorder_point NUMERIC(15, 3),
    max_storage_days INTEGER,
    max_inventory_days INTEGER,
    monthly_target_volume NUMERIC(15, 3),
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3. File Processing Tracking Table: `processed_files`
Prevents duplicate imports:

```sql
CREATE TABLE processed_files (
    id SERIAL PRIMARY KEY,
    gcs_path VARCHAR(500) UNIQUE,
    filename VARCHAR(255),
    file_hash VARCHAR(64),
    rows_imported INTEGER,
    rows_updated INTEGER DEFAULT 0,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 🧠 Intelligence & Analytics Layer

This layer transforms raw inventory data into actionable insights using SQL views and computed fields.

### View 1: Product Intelligence Summary
**Purpose**: Aggregates inventory by product and compares to thresholds

**Key Calculations**:
```
Stock Status Classification:
├─ CRITICAL: current_stock < safety_stock
├─ WARNING: current_stock < reorder_point
├─ EXCESS: current_stock > (monthly_target × 3)
└─ NORMAL: within acceptable range

Days of Stock Remaining:
    = current_stock / (monthly_target_volume / 30)
    = How many days until stock runs out

Gap Analysis:
    shortage_qty = (safety_stock - current_stock) if critical
    excess_qty = (current_stock - optimal_level) if overstocked

Profit Margin %:
    = ((selling_price - purchase_price) / purchase_price) × 100

Target Fulfillment %:
    = (current_stock / monthly_target_volume) × 100
```

**Output Fields**:
```json
{
  "item": "Toluene",
  "total_stock_all_locations": 5000,
  "safety_stock": 2000,
  "reorder_point": 3500,
  "days_of_stock_remaining": 45.5,
  "stock_status": "NORMAL",
  "shortage_qty": 0,
  "excess_qty": 0,
  "profit_margin_percent": 18.5,
  "target_fulfillment_percent": 150
}
```

### View 2: Shipment Intelligence
**Purpose**: Analyzes individual shipments with aging analysis

**Key Calculations**:
```
Days in Stock:
    = CURRENT_DATE - record_date

Aging Status:
├─ AGED: days_in_stock > max_storage_days
├─ AGING_SOON: days_in_stock > (max_storage_days × 0.8)
└─ FRESH: days_in_stock ≤ (max_storage_days × 0.8)

Days to Deplete:
    = physical_stock / (monthly_target_volume / 30)

Price Variance %:
    = ((market_price - purchase_price) / purchase_price) × 100

Recommended Action:
├─ URGENT_REORDER: stock < safety_stock
├─ LIQUIDATE_AGED_STOCK: days_in_stock > max_storage_days
├─ REORDER_RECOMMENDED: stock < reorder_point
├─ REDUCE_PROCUREMENT: unsold > monthly_target × 3
└─ MONITOR: normal situation

Risk Flags Array:
├─ LOW_STOCK
├─ AGED_INVENTORY
├─ EXCESS_STOCK
└─ NEGATIVE_MARGIN
```

### View 3: Critical Alerts
**Purpose**: Prioritized alert system

**Priority Levels**:
```
Priority 1 (🔴 CRITICAL):
    Stock < safety_stock
    Action: Immediate procurement

Priority 2 (🟠 URGENT):
    Inventory aged beyond max_storage_days
    Action: Liquidate immediately

Priority 3 (🟡 WARNING):
    Stock < reorder_point
    Action: Plan procurement

Priority 4 (🔵 INFO):
    Excess inventory > monthly_target × 3
    Action: Review demand forecast
```

### View 4: Inventory Narrative (Natural Language)
**Purpose**: Generates executive summary

**Algorithm**:
```
Overall Health:
    IF critical_count > 0 → "CRITICAL"
    ELSE IF warning_count > 3 → "NEEDS_ATTENTION"
    ELSE IF excess_count > 2 → "OVERSTOCKED"
    ELSE → "HEALTHY"

Executive Summary Generation:
    1. Start with health status
    2. Add counts of each status category
    3. Note any aged inventory
    4. Include average coverage days
    5. Add profit margin info
    6. Generate action items list

Example Output:
"Inventory Status: ⚠️ CRITICAL - 2 product(s) below safety 
stock. 1 shipment(s) aged beyond storage limits. Average 
inventory coverage: 18.5 days. Average margin: 15.3%."
```

**API Response**:
```json
{
  "overall_health": "CRITICAL",
  "executive_summary": "...",
  "total_products": 10,
  "critical_count": 2,
  "warning_count": 3,
  "excess_count": 1,
  "normal_count": 4,
  "avg_days_stock": 18.5,
  "total_shortage": 5500,
  "total_excess": 2000,
  "avg_profit_margin": 15.3,
  "aged_count": 1,
  "aging_soon_count": 2,
  "recommended_actions": [
    "Urgent: Procure 5500 MT to meet safety stock",
    "Liquidate 1 aged shipment(s)",
    "Reduce procurement for 1 overstocked item(s)"
  ]
}
```

---

## 🎨 Frontend Visualization

### 1. Intelligence & Insights Tab (Default View)

#### A. Executive Summary Card
```
┌─────────────────────────────────────────────────────┐
│ 📊 Executive Summary        [HEALTHY/CRITICAL]     │
├─────────────────────────────────────────────────────┤
│                                                       │
│ Natural language paragraph explaining inventory     │
│ status with specific numbers and recommendations.   │
│                                                       │
│ ┌─────┬────────┬────────┬────────┐                │
│ │Crit │Warning │ Excess │ Normal │                │
│ │  2  │   3    │   1    │   4    │                │
│ └─────┴────────┴────────┴────────┘                │
│                                                       │
│ ⚠️ Recommended Actions:                             │
│ • Action 1                                          │
│ • Action 2                                          │
│ • Action 3                                          │
└─────────────────────────────────────────────────────┘
```

#### B. Critical Alerts Panel
```
┌─────────────────────────────────────────────────────┐
│ 🚨 Critical Alerts                                  │
├─────────────────────────────────────────────────────┤
│                                                       │
│ ┌────────────────────────────────────────────────┐ │
│ │🔴 CRITICAL - Stock Below Safety Level          │ │
│ │Toluene @ STPL - KANDLA                         │ │
│ │Stock critically low: 1500 MT (Safety: 2000 MT)│ │
│ └────────────────────────────────────────────────┘ │
│                                                       │
│ ┌────────────────────────────────────────────────┐ │
│ │🟠 URGENT - Aged Inventory                      │ │
│ │IPA @ STPL - KANDLA                             │ │
│ │Inventory aged: 95 days (Max: 90 days)          │ │
│ └────────────────────────────────────────────────┘ │
│                                                       │
│ [Show more alerts...]                               │
└─────────────────────────────────────────────────────┘
```

#### C. Product Intelligence Table
```
┌─────────────────────────────────────────────────────────────────┐
│ 📈 Product Intelligence Summary                                 │
├──────────┬────────┬──────────┬──────────┬──────┬──────┬────────┤
│Product  │Status  │Current   │Days      │Margin│Actions        │
│          │        │Stock     │Coverage  │%     │               │
├──────────┼────────┼──────────┼──────────┼──────┼──────┼────────┤
│Toluene  │CRITICAL│1,500 MT  │12 days   │18.5% │Details        │
│IPA      │WARNING │2,100 MT  │22 days   │16.2% │Details        │
│DEG      │NORMAL  │5,000 MT  │45 days   │22.1% │Details        │
│...      │...     │...       │...       │...   │...             │
└──────────┴────────┴──────────┴──────────┴──────┴──────┴────────┘
```

#### D. Product Detail Modal (Click "Details")
```
┌─────────────────────────────────────────────────────┐
│ Product Analysis: Toluene                        [X] │
├─────────────────────────────────────────────────────┤
│                                                       │
│ Status: [CRITICAL]                                  │
│                                                       │
│ Product: Toluene. Current stock: 1,500 MT. Status: │
│ CRITICAL. ⚠️ Critically low - 500 MT below safety  │
│ stock. Immediate procurement required. Coverage:    │
│ 12 days at current consumption rate.                │
│                                                       │
│ 🎯 Recommended Actions:                             │
│ • URGENT: Order 500 MT immediately                 │
│ • Monitor daily - low coverage                      │
│                                                       │
│                                              [Close] │
└─────────────────────────────────────────────────────┘
```

### 2. Inventory Dashboard Tab

Shows all raw inventory records with sortable, paginated table.

### 3. Product Settings Tab

Editable table to configure thresholds and targets for each product.

---

## 📊 Complete Workflow Examples

### Example 1: New Stock Report Upload

**Scenario**: Excel file uploaded to GCS bucket with new shipment data

**Step-by-Step Flow**:

1. **File Uploaded to GCS**
   ```
   stock_report.xlsx → GCS bucket (dashboard-inventory)
   ```

2. **Manual Refresh Trigger**
   ```
   User clicks "Refresh Data" or system runs scheduled job
   POST /api/refresh
   ```

3. **File Detection & Processing**
   ```
   FastAPI backend:
   - List all files in GCS bucket
   - Check processed_files table for duplicates
   - Download new files
   ```

4. **Excel Parsing**
   ```python
   df = pd.read_excel(file_bytes, sheet_name="STOCK SHEET")
   # Map columns to database schema
   # Convert data types (string → date, text → numeric)
   # Remove blanks and validate
   ```

5. **Database Insertion**
   ```sql
   INSERT INTO inventory_dashboard (...) VALUES (...)
   COMMIT TRANSACTION
   ```

6. **Duplicate Prevention**
   ```sql
   INSERT INTO processed_files (gcs_path, file_hash, rows_imported, processed_at)
   ```

7. **Analytics Recalculation**
   ```
   SQL views automatically refresh:
   - v_product_intelligence_summary
   - v_shipment_intelligence  
   - v_critical_alerts
   - v_inventory_narrative
   ```

8. **Frontend Display Update**
   ```
   User navigates to "Intelligence & Insights" tab
   React fetches from API:
   - GET /api/intelligence/summary
   - GET /api/intelligence/alerts
   - GET /api/intelligence/narrative
   
   Frontend renders:
   - Executive summary card
   - Critical alerts panel
   - Product intelligence table
   ```

### Example 2: Identifying and Acting on Critical Stock

**Scenario**: Product stock drops below safety level

**Automatic Detection Flow**:

1. **Data Inserted**
   ```sql
   INSERT INTO inventory_dashboard 
   VALUES (product='Toluene', physical_stock_on_port=1500, ...)
   ```

2. **View Calculation**
   ```sql
   -- v_product_intelligence_summary triggers
   SELECT
       'Toluene' as item,
       1500 as total_stock,
       2000 as safety_stock,
       CASE 
           WHEN 1500 < 2000 THEN 'CRITICAL'  -- ← Status assigned
       END as stock_status,
       (2000 - 1500) as shortage_qty  -- 500 MT shortage
   ```

3. **Alert Generation**
   ```sql
   -- v_critical_alerts triggers
   SELECT
       1 as priority,
       '🔴 CRITICAL - Stock Below Safety Level' as alert_type,
       'Toluene @ STPL - KANDLA' as location,
       'Stock critically low: 1500 MT (Safety: 2000 MT)' as alert_message
   ```

4. **Narrative Generation**
   ```sql
   -- v_inventory_narrative updates
   overall_health = 'CRITICAL'
   executive_summary includes:
   "⚠️ CRITICAL - 1 product(s) below safety stock..."
   recommended_actions includes:
   "Urgent: Procure 500 MT to meet safety stock"
   ```

5. **Frontend Alert**
   ```
   Insights Dashboard displays:
   - Red banner in Executive Summary: CRITICAL
   - Alert card: "🔴 CRITICAL - Toluene below safety stock"
   - Product table: Toluene row highlighted, Status = CRITICAL
   ```

6. **User Action**
   ```
   1. User sees alert
   2. Clicks "Details" on Toluene row
   3. Modal shows: "URGENT: Order 500 MT immediately"
   4. User initiates procurement process
   ```

### Example 3: Aged Inventory Detection

**Scenario**: Inventory stored beyond max days

**Detection & Action Flow**:

1. **Aging Calculation**
   ```sql
   -- v_shipment_intelligence calculates:
   days_in_stock = TODAY - record_date = 95 days
   max_storage_days = 90 days (from product_settings)
   
   CASE
       WHEN 95 > 90 THEN 'AGED'
       WHEN 95 > (90 * 0.8=72) THEN 'AGING_SOON'
   END = 'AGED'
   ```

2. **Action Recommendation**
   ```sql
   recommended_action = 'LIQUIDATE_AGED_STOCK'
   ```

3. **Risk Flag**
   ```sql
   risk_flags = ARRAY['AGED_INVENTORY']
   ```

4. **Alert Priority**
   ```sql
   -- v_critical_alerts assigns Priority 2
   alert_type = '🟠 URGENT - Aged Inventory'
   alert_message = 'Inventory aged: 95 days (Max: 90 days)'
   ```

5. **Alert Display**
   ```
   Orange alert card in Critical Alerts panel
   Shows: Product, Location, Age vs Max, Recommendation
   ```

6. **Narrative Impact**
   ```json
   {
     "aged_count": 1,
     "recommended_actions": [
       "Liquidate 1 aged shipment(s)"
     ]
   }
   ```

---

## 🔌 API Reference

### Inventory Endpoints

**GET /api/inventory**
- Returns all inventory records
- Response: `{success: bool, data: [], total: int}`

**GET /api/inventory/summary**
- Returns aggregate statistics
- Response: `{success: bool, summary: {}}`

### Intelligence Endpoints

**GET /api/intelligence/summary**
- Product-wise intelligence with threshold comparisons
- Response: `{success: bool, data: [{item, total_stock, status, ...}]}`

**GET /api/intelligence/shipments**
- Shipment-level analysis with aging data
- Response: `{success: bool, data: [{id, days_in_stock, aging_status, ...}]}`

**GET /api/intelligence/alerts**
- Prioritized critical alerts
- Response: `{success: bool, data: [{priority, alert_type, item, message}]}`

**GET /api/intelligence/narrative**
- Natural language executive summary
- Response: 
```json
{
  "success": true,
  "data": {
    "overall_health": "CRITICAL",
    "executive_summary": "...",
    "critical_count": 2,
    "recommended_actions": ["...", "..."]
  }
}
```

**GET /api/intelligence/product/{product_name}**
- Product-specific narrative
- Response: `{success: bool, data: {narrative, status, actions}}`

### File Management Endpoints

**POST /api/upload**
- Upload Excel file to GCS
- Request: `FormData with file`
- Response: `{success: bool, gcs_path, filename}`

**POST /api/refresh**
- Process new files from GCS
- Response: `{success: bool, imported: [{gcs_path, rows}]}`

**GET /api/files**
- List all uploaded files and processing status
- Response: `{success: bool, files: [{filename, processed, rows_imported, processed_at}]}`

### Settings Endpoints

**GET /api/product-settings**
- Get all product settings
- Response: `{success: bool, data: [{item, safety_stock, reorder_point, ...}]}`

**POST /api/product-settings**
- Create new product setting
- Request: `{item, safety_stock, reorder_point, ...}`
- Response: `{success: bool, data: {id, item, ...}}`

**PUT /api/product-settings/{id}**
- Update product setting
- Request: `{field: value}`
- Response: `{success: bool, data: {id, item, ...}}`

**DELETE /api/product-settings/{id}**
- Soft delete product setting
- Response: `{success: bool, message}`

---

## 🚀 Deployment & Setup

### Prerequisites
- Python 3.9+
- Node.js 16+
- PostgreSQL (or Cloud SQL)
- Google Cloud Storage bucket
- Google Application Default Credentials

### Backend Setup

1. **Install Dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Setup Environment**
   ```bash
   cp backend/.env.example backend/.env
   # Configure GCS_BUCKET_NAME
   ```

3. **Create Database Schema**
   ```bash
   # Run these SQL scripts in order:
   # 1. schema_product_settings.sql
   # 2. schema_inventory_dashboard.sql
   # 3. schema_intelligence_views.sql
   ```

4. **Start Backend Server**
   ```bash
   python main.py
   # Server runs on http://localhost:8000
   # API docs available at http://localhost:8000/docs
   ```

### Frontend Setup

1. **Install Dependencies**
   ```bash
   cd frontend
   npm install --legacy-peer-deps
   ```

2. **Start Dev Server**
   ```bash
   npm run dev
   # Frontend runs on http://localhost:3000
   ```

3. **Build for Production**
   ```bash
   npm run build
   # Outputs to frontend/dist/
   ```

### Data Import Workflow

1. **Prepare Excel File**
   - Create/update `stock_report.xlsx`
   - Ensure data is in worksheet named "STOCK SHEET"
   - Include all required columns with data

2. **Upload to GCS**
   - Option A: Use Dashboard UI - "Upload File" button
   - Option B: Manual upload to `gs://dashboard-inventory/uploads/`

3. **Trigger Processing**
   - Frontend: Click "Refresh Data" button
   - Or API: `POST /api/refresh`
   - Backend automatically:
     - Detects new files
     - Parses Excel
     - Validates data
     - Inserts into database
     - Calculates analytics

4. **View Results**
   - Navigate to "Intelligence & Insights" tab
   - See automatic alerts and recommendations
   - Use product intelligence table for detailed view
   - Click product names for specific analysis

---

## 🎯 Key Features Summary

| Feature | Source | Processing | Display |
|---------|--------|-----------|---------|
| **Stock Status** | Excel | View: v_product_intelligence_summary | Status badge with color |
| **Days of Stock** | Settings + Inventory | Calculation: stock/(target/30) | Numeric with color coding |
| **Critical Alerts** | View: v_critical_alerts | Priority ranking | Alert cards with emoji |
| **Aged Inventory** | View: v_shipment_intelligence | Age calculation: today-date | Aging status indicator |
| **Natural Language** | View: v_inventory_narrative | Text generation algorithm | Executive summary card |
| **Profit Margin** | Excel pricing data | Calculation: (sell-buy)/buy*100 | Percentage with color |
| **Gap Analysis** | Inventory + Settings | Shortage/excess calculation | Numeric with +/- indicator |

---

## 📝 Notes

- All timestamps are stored in UTC (TIMESTAMPTZ)
- Numeric fields use DECIMAL for precision (financial calculations)
- File deduplication prevents re-importing same data
- Views automatically refresh with new data (no manual trigger)
- Natural language summaries update in real-time
- All data is immutable (updates create new records)
- Soft deletes preserve audit trail

---

## 🆘 Troubleshooting

**Issue**: Data not appearing in dashboard
- Check: File uploaded to correct GCS bucket
- Check: Excel file has "STOCK SHEET" worksheet
- Check: Run `/api/refresh` endpoint
- Check: Backend logs for parsing errors

**Issue**: Alerts not showing up
- Check: Product settings configured with correct thresholds
- Check: Product name matches exactly in settings and inventory
- Check: SQL views exist in database

**Issue**: Negative days of stock
- Check: Monthly target volume is positive
- Check: Stock quantity is positive
- Check: Calculation logic in SQL views

**Issue**: Frontend not connecting to backend
- Check: Backend running on localhost:8000
- Check: CORS enabled in FastAPI
- Check: API endpoint URLs match

---

## 📚 Documentation Files

- `INTELLIGENCE_FEATURES.md` - Detailed intelligence system documentation
- `schema_product_settings.sql` - Product configuration schema
- `schema_inventory_dashboard.sql` - Main inventory schema  
- `schema_intelligence_views.sql` - Analytics views and functions

---

**Last Updated**: May 19, 2026  
**Version**: 1.0  
**Status**: Production Ready
