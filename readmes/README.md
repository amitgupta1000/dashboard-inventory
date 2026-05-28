# Inventory Management Dashboard - Complete Implementation Guide

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [Tech Stack](#tech-stack)
3. [Database Architecture](#database-architecture)
4. [Data Models & Schemas](#data-models--schemas)
5. [API Endpoints](#api-endpoints)
6. [Data Loading Pipeline](#data-loading-pipeline)
7. [Frontend Architecture](#frontend-architecture)
8. [Setup & Installation](#setup--installation)
9. [Running the Application](#running-the-application)

---

## 🏗️ System Overview

**Dashboard Inventory** is a full-stack inventory management system that combines real-time stock tracking, target management, market pricing intelligence, and historical analytics in a single platform.

**Core Capabilities**:
- 📊 **Real-time inventory tracking** across commodities and terminals
- 🎯 **Configurable targets** with automatic versioning via config_date
- 💰 **Market pricing data** from daily Excel reports
- 📈 **Historical analytics** with daily snapshots and insights
- 📤 **Multi-source data loading** from Excel, CSV files
- 🔄 **Async processing** with modern Python async/await patterns
- 💾 **Dual database support** - PostgreSQL (production) and SQLite (development)

```
┌──────────────────────────────────────────────────────────────────┐
│                    INVENTORY DASHBOARD ARCHITECTURE              │
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│   Input Sources          Backend API              Database         UI
│   ──────────────         ─────────────            ────────────    ────
│                                                                    │
│   Excel Files ───┐       FastAPI               PostgreSQL/SQLite  React 18.2
│   CSV Files ────►├──────► (async routes)  ───► Tables:           TypeScript
│   Web Uploads ──┘       - /api/targets         - commodities      Vite 7.3.3
│                         - /api/market-data     - targets          Tailwind CSS
│   GCS Bucket            - /api/inventory       - inventory        Lucide Icons
│   (File uploads)        - /api/uploads         - market data
│                                                 - snapshots
│                                                 - logs
│
│  Data Loaders               Middleware
│  ────────────              ──────────
│  - load_commodities        - CORS
│  - load_inventory_targets  - Async sessions
│  - load_market_data        - Error handling
│  - load_stock_report       - Validation
│
└──────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

### **Backend**
| Component | Version | Purpose |
|-----------|---------|---------|
| FastAPI | Latest | REST API framework with async support |
| SQLAlchemy | 2.0+ | ORM with async support (asyncpg for PostgreSQL, aiosqlite for SQLite) |
| PostgreSQL | 14+ | Production database (Cloud SQL) |
| SQLite | 3.x | Development/testing database (local) |
| Pandas | 2.x | Data processing and CSV/Excel parsing |
| Pydantic | 2.x | Data validation and schema definitions |
| Python | 3.11+ | Async/await support, modern syntax |

### **Frontend**
| Component | Version | Purpose |
|-----------|---------|---------|
| React | 18.2.0 | UI framework |
| TypeScript | 5.x | Type-safe JavaScript |
| Vite | 7.3.3 | Lightning-fast build tool |
| Tailwind CSS | 3.3.6 | Utility-first CSS framework |
| Lucide React | Latest | Beautiful icon library |
| Axios | Latest | HTTP client for API calls |
| Vitest | Latest | Unit testing framework |

### **Database**
| Database | Environment | Connection String |
|----------|-------------|-------------------|
| PostgreSQL | Production | `postgresql+asyncpg://user:pass@host:5432/inventory` |
| SQLite | Development | `sqlite+aiosqlite:///./jobs.db` |

---

## 🗄️ Database Architecture

### Core Tables

#### **1. commodities** (Master Data)
Stores all commodity/product definitions
```sql
CREATE TABLE commodities (
    id SERIAL PRIMARY KEY,
    commodity_name VARCHAR(255) UNIQUE NOT NULL,
    commodity_code VARCHAR(50),
    category VARCHAR(100),
    unit_of_measure VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Key Fields**:
- `commodity_name`: Unique identifier (e.g., "TOLUENE", "ACETIC ACID")
- `is_active`: Filter for active commodities
- Used as FK by targets, inventory records, and market data

#### **2. commodity_daily_configs** (Inventory Targets - Versioned)
Stores inventory targets with automatic versioning
```sql
CREATE TABLE commodity_daily_configs (
    id SERIAL PRIMARY KEY,
    commodity_id INTEGER FOREIGN KEY,
    config_date DATE NOT NULL,  -- Versioning key (multiple entries per commodity = versions)
    
    -- Target levels
    desired_stock_level FLOAT,
    min_stock_level FLOAT,
    max_stock_level FLOAT,
    monthly_sales_target FLOAT,
    
    -- Timing targets
    target_inventory_days FLOAT DEFAULT 30,
    target_storage_cap_days FLOAT,
    estimated_days_to_sale FLOAT DEFAULT 15,
    
    -- Financial targets
    expected_gross_margin FLOAT,
    annual_cost_of_capital_rate FLOAT DEFAULT 0.08,
    cash_realization_rate FLOAT DEFAULT 0.95,
    
    -- Metadata
    is_finalized BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE (commodity_id, config_date)
);
```

**Versioning Strategy**:
- Multiple rows per commodity with different `config_date` values = version history
- Highest `config_date` = current target configuration
- API filters by `max(config_date)` to get latest targets
- History accessible via `/api/targets/history/{commodity_id}`

#### **3. daily_inventory_records** (Detailed Inventory)
Stores daily inventory levels per commodity and terminal
```sql
CREATE TABLE daily_inventory_records (
    id SERIAL PRIMARY KEY,
    commodity_id INTEGER FOREIGN KEY,
    terminal_id INTEGER FOREIGN KEY,
    report_id INTEGER FOREIGN KEY,
    record_date DATE,
    
    -- Stock levels
    physical_stock FLOAT,
    incoming_stock FLOAT,
    total_stock FLOAT,
    
    -- Calculated fields
    stock_status VARCHAR(50),  -- CRITICAL, WARNING, NORMAL, EXCESS
    days_of_stock FLOAT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### **4. market_data_hvb** (Daily Market Pricing)
Stores daily market pricing from Excel reports
```sql
CREATE TABLE market_data_hvb (
    id SERIAL PRIMARY KEY,
    product_name VARCHAR(255),
    port VARCHAR(100),
    company_name VARCHAR(255),
    
    -- Physical stock
    physical_stock FLOAT,
    port_stock FLOAT,
    
    -- Pricing
    market_price FLOAT,
    selling_price FLOAT,
    replacement_cost_dollar FLOAT,
    replacement_cost_inr FLOAT,
    
    -- Metadata
    report_date DATE,
    usdinr_rate FLOAT,
    
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Data Origin**: `load_market_data.py` loads from `DAILY PRICE REPORT 22-05-2026.xlsx`

#### **5. daily_inventory_reports** (Report Headers)
Groups inventory records by report/date
```sql
CREATE TABLE daily_inventory_reports (
    id SERIAL PRIMARY KEY,
    report_date DATE,
    source_file VARCHAR(500),
    total_records INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### **6. terminals** (Terminal/Port Master)
Stores terminal/port information
```sql
CREATE TABLE terminals (
    id SERIAL PRIMARY KEY,
    terminal_name VARCHAR(255) UNIQUE,
    port_code VARCHAR(50),
    region VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### **7. data_import_logs** (Audit Trail)
Tracks all data imports and processing
```sql
CREATE TABLE data_import_logs (
    id SERIAL PRIMARY KEY,
    import_type VARCHAR(50),  -- 'CSV', 'EXCEL', 'API'
    source_file VARCHAR(500),
    rows_processed INTEGER,
    rows_failed INTEGER,
    status VARCHAR(50),  -- 'SUCCESS', 'PARTIAL', 'FAILED'
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### **8. inventory_detail** (Detailed Daily Tracking)
Comprehensive daily inventory tracking
```sql
CREATE TABLE inventory_detail (
    id SERIAL PRIMARY KEY,
    commodity_id INTEGER,
    terminal_id INTEGER,
    incoming_stock_date DATE,
    physical_stock NUMERIC(15,3),
    physical_stock_value NUMERIC(18,2),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 📊 Data Models & Schemas

### Pydantic Models (API Request/Response)

#### **TargetUpdate** (PUT /api/targets/{commodity_id})
```python
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
```

#### **TargetResponse** (GET /api/targets)
```python
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
```

#### **MarketDataResponse** (GET /api/market-data)
```python
class MarketDataResponse(BaseModel):
    id: int
    product_name: str
    port: str
    company_name: str
    physical_stock: float
    port_stock: float
    market_price: float
    selling_price: float
    replacement_cost_inr: float
    report_date: date
    usdinr_rate: float
```

---

## 🔌 API Endpoints

### **Targets Management** (`/api/targets`)

```bash
# Get all current targets (latest by config_date)
GET /api/targets
Response: [TargetResponse, ...]

# Get target for specific commodity
GET /api/targets/{commodity_id}
Response: TargetResponse

# Update target (creates new version if date changes)
PUT /api/targets/{commodity_id}
Body: TargetUpdate
Response: TargetResponse

# Get target version history
GET /api/targets/history/{commodity_id}
Response: [TargetResponse, ...]  # ordered by config_date DESC
```

### **Market Data** (`/api/market-data`)

```bash
# Get latest market data
GET /api/market-data
Params: ?product={name}, ?port={name}, ?report_date={date}
Response: [MarketDataResponse, ...]

# Get market data summary
GET /api/market-data/summary
Response: {
  "total_records": 60,
  "unique_products": 30,
  "unique_ports": 8,
  "latest_report_date": "2026-05-22"
}

# Get data for specific product across all ports
GET /api/market-data/product/{product_name}
Response: [MarketDataResponse, ...]
```

### **Inventory** (`/api/inventory`)

```bash
# Get inventory data
GET /api/inventory
Params: ?commodity={name}, ?terminal={name}

# Get inventory summary
GET /api/inventory/summary
```

### **File Uploads** (`/api/uploads`)

```bash
# Upload file
POST /api/uploads
Body: FormData { file: File }

# Get upload history
GET /api/uploads/history
```

---

## 📤 Data Loading Pipeline

### **Data Loaders**

#### **1. load_commodities.py**
Loads commodity/product master data from `inventory_targets.csv`

```bash
python -c "from backend.load_commodities import load_commodities_from_csv; \
           load_commodities_from_csv('data_files/inventory_targets.csv')"
```

**Process**:
1. Read CSV with latin-1 encoding
2. Extract unique product names
3. Normalize names (uppercase, trim spaces)
4. Insert into `commodities` table
5. Result: 34 commodities loaded

#### **2. load_inventory_targets.py**
Loads target configurations from `inventory_targets.csv`

```bash
python -c "import asyncio; \
           from backend.load_inventory_targets import load_inventory_targets_from_csv; \
           asyncio.run(load_inventory_targets_from_csv('data_files/inventory_targets.csv'))"
```

**CSV Column Mapping**:
| CSV Column | Target Field | Notes |
|---|---|---|
| product_name | commodity_id (lookup) | Exact case-insensitive match |
| desired_stock_leve | desired_stock_level | Fixed typo from CSV |
| min_stock_level | min_stock_level | Direct mapping |
| max_stock_level | max_stock_level | Direct mapping |
| target_inventory_holding_days | target_inventory_days | Renamed |
| monthly_sales_target | monthly_sales_target | New field (added May 27) |
| target_storage_cap_days | target_storage_cap_days | New field (added May 27) |
| target_cash_realisation_days | estimated_days_to_sale | Renamed |
| expected_gross_margin | expected_gross_margin | Converted % to decimal |
| annual_cost_of_capital | annual_cost_of_capital_rate | Converted % to decimal |

**Features**:
- Exact commodity matching (no substring collisions)
- Percentage to decimal conversion ("12%" → 0.12)
- Versioning via config_date (today by default)
- Automatic updates if same date exists
- Result: 34/34 targets loaded successfully

#### **3. load_market_data.py**
Loads daily market pricing from Excel report

```bash
python -c "import asyncio; \
           from backend.load_market_data import load_market_data_from_excel; \
           asyncio.run(load_market_data_from_excel('data_files/DAILY PRICE REPORT 22-05-2026.xlsx', '2026-05-22'))"
```

**Excel Processing**:
- Reads `DAILY PRICE REPORT 22-05-2026.xlsx`
- Extracts USD/INR rate from last row
- Maps 60 columns to schema
- Parses "PRODUCT - PORT" format into separate columns
- Result: 60 rows loaded (30 unique products, 8 ports)

#### **4. load_stock_report.py** (Work in Progress)
Loads detailed stock reports from `stock_report.xlsx`

**Features**:
- Commodity-level stock tracking
- Terminal-specific quantities
- Daily inventory snapshots
- Audit trail of changes

#### **5. migrate_add_target_fields.py**
Database migration script to add new columns

```bash
python backend/migrate_add_target_fields.py
```

**Adds**:
- `monthly_sales_target` FLOAT
- `target_storage_cap_days` FLOAT

---

## 🎨 Frontend Architecture

### **React Components**

#### **UploadPanel.tsx** (Modal - 330 lines)
Main data management hub with 5 action buttons:

**Button Organization**:
1. 📤 **File Uploads** (3 buttons)
   - Upload Inventory
   - Upload Market Data
   - Upload Sales Data

2. ⚙️ **Configuration** (1 button)
   - Review & Update Targets

3. 📊 **Analytics & Actions** (2 buttons)
   - View Insights
   - Manage Suppliers

**Features**:
- Centered modal overlay with backdrop
- Integrated TargetEditor as child component
- File upload handling
- Status alerts (saving, success, error)

#### **TargetEditor.tsx** (Modal - 380 lines)
Commodity targets management with version history

**Features**:
- Table view of all 34 commodities
- Editable fields (stock levels, days, targets)
- Track modified rows in Map
- "History" button shows all config_date versions
- Batch save (only modified rows sent to API)
- Real-time status feedback

**State Management**:
```typescript
const [targets, setTargets] = useState([]);
const [editedTargets, setEditedTargets] = useState(new Map());
const [showHistory, setShowHistory] = useState(false);
const [history, setHistory] = useState([]);
const [saveStatus, setSaveStatus] = useState<'idle'|'saving'|'success'|'error'>('idle');
```

#### **DataTable.tsx**
Displays inventory/market data in tabular format

**Features**:
- Column customization
- Sorting and filtering
- Pagination
- Export functionality

#### **App.tsx** (Main Component - 250+ lines)
Core application layout and orchestration

**Key State**:
- inventory, summary, alerts, narrative
- selectedProduct for drilldowns
- uploadPanelOpen for modal control
- asOfDate, backdate for temporal queries
- searchQuery for filtering

**Main Sections**:
1. Header with date pickers and search
2. KPI metrics summary
3. Inventory data table
4. Product details panel
5. Analytics insights

### **Styling**

- **Framework**: Tailwind CSS 3.3.6
- **Layout**: Flexbox/Grid utilities
- **Colors**: Custom color scheme (see `styles/colors.ts`)
- **Animations**: CSS animations (`styles/animations.css`)
- **Icons**: Lucide React (Activity, Upload, Settings, etc.)
- **Responsive**: Mobile-first responsive design

### **API Integration**

```typescript
const API_BASE_URL = 'http://localhost:8000';

// Axios instance for requests
const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' }
});

// Example: Fetch targets
const response = await axiosInstance.get('/api/targets');
const targets = response.data;

// Example: Update target
await axiosInstance.put(`/api/targets/${commodityId}`, {
  desired_stock_level: 1000,
  monthly_sales_target: 500
});
```

---

## ⚙️ Setup & Installation

### **Prerequisites**
- Python 3.11+
- Node.js 18+ (for frontend)
- PostgreSQL 14+ (production) OR SQLite (development)
- Git

### **Backend Setup**

1. **Clone repository**
   ```bash
   git clone https://github.com/amitgupta1000/dashboard-inventory.git
   cd dashboard-inventory
   ```

2. **Create Python environment**
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # On Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r backend/requirements.txt
   ```

4. **Configure environment**
   ```bash
   # Create .env in backend/ directory
   cat > backend/.env << EOF
  # Cloud SQL (PostgreSQL) - recommended
  USE_SQLITE=false
   CLOUD_SQL_PASSWORD=your_password
   CLOUD_SQL_HOST=your_host
  CLOUD_SQL_PORT=5432
  CLOUD_SQL_USER=postgres
   CLOUD_SQL_DATABASE=inventory

  # Optional local fallback:
  # USE_SQLITE=true
   EOF
   ```

5. **Initialize database**
   ```bash
   python backend/init_db.py
   ```
    Notes:
    - This is the only supported database bootstrap command.
    - `backend/create_db.py` has been retired after consolidation.

### **Frontend Setup**

1. **Navigate to frontend**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure API endpoint**
   ```bash
  # Optional (defaults to same-origin / Vite proxy)
  # frontend/.env
  VITE_API_BASE_URL=http://localhost:8000
   ```

---

## 🚀 Running the Application

### **Backend**
```bash
cd c:\dashboard-inventory
python main.py
# Server runs on: http://localhost:8000
# API docs on: http://localhost:8000/docs
```

### **Frontend**
```bash
cd frontend
npm run dev
# App runs on: http://localhost:5173
# Vite dev server with hot reload
```

### **Full Stack**
```bash
# Terminal 1: Backend
python main.py

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Load data (optional)
python -c "from backend.load_commodities import load_commodities_from_csv; \
           load_commodities_from_csv()"

python -c "import asyncio; \
           from backend.load_inventory_targets import load_inventory_targets_from_csv; \
           asyncio.run(load_inventory_targets_from_csv())"
```

### **Data Loading Workflow**

#### **Prerequisite: Load Commodities First**
```bash
python backend/load_commodities.py
```
- Creates 34 commodity master records from `inventory_targets.csv`
- **Must run first** - other loaders depend on these existing

---

#### **Complete Upload Sequence**

**Step 1: Load Inventory Targets** (Recommended)
```bash
python backend/load_inventory_targets.py
```
- Loads 34 commodity targets from `inventory_targets.csv`
- Creates versioned configurations with `config_date` key
- Includes: desired stock, min/max levels, sales targets, storage capacity, margins, etc.

**Step 2: Upload Daily Price Report** ⚡
```bash
python backend/load_market_data.py
```
- **Source File**: `data_files/DAILY PRICE REPORT 22-05-2026.xlsx`
- **Destination**: `market_data_hvb` table
- **Purpose**: Market pricing data across 30 products × 8 ports = 60 records
- **Content**: Product names formatted as `PRODUCT - PORT` (e.g., `TOLUENE - KANDLA`)
- **Extras**: Extracts USD/INR exchange rate from report

**Step 3: Upload Stock Report** 📦
```bash
python backend/load_stock_report.py
```
- **Source Files**: `data_files/stock_report.csv` (preferred) or `data_files/stock_report.xlsx`
- **Destination**: `inventory_detail` table
- **Purpose**: Vessel-level stock data with calculated days of stock
- **Key Calculation**: `no_of_days_of_stock = report_date - vessel_date` (derived, not from file)
- **Status**: ⚠️ **WIP** - File exists but may need completion/testing

---

#### **Files Available in `data_files/`**
- ✅ `daily_price_report.xlsx` - Daily market prices
- ✅ `inventory_targets.csv` - Commodity master & targets
- ✅ `stock_report.csv` - Vessel stock data (CSV format)
- ✅ `stock_report.xlsx` - Vessel stock data (Excel format)

---

#### **Dependencies Chart**

| Loader | Depends On | Creates Table | Records |
|--------|-----------|----------------|---------|
| `load_commodities` | None | `commodities` | 34 |
| `load_inventory_targets` | `commodities` | `commodity_daily_configs` | 34 |
| `load_market_data` | None (independent) | `market_data_hvb` | 60 |
| `load_stock_report` | `commodities` | `inventory_detail` | WIP |

**Note**: Daily price report is independent and can run anytime. Stock report needs commodities to exist for product name matching.

---

## � Ingestion Feedback System

All data loaders provide comprehensive user feedback with detailed status information.

### **Feedback Metrics**

Each ingestion returns detailed metrics:

```json
{
  "status": "success|partial_success|failed",
  "message": "Human-readable message",
  "total_rows": 60,
  "rows_inserted": 45,
  "rows_updated": 15,
  "rows_failed": 0,
  "report_date": "2026-05-22",
  "source_file": "DAILY PRICE REPORT 22-05-2026.xlsx",
  "destination_table": "market_data_hvb",
  
  "commodity_match": {
    "total_rows": 60,
    "matched_commodities": 58,
    "unmatched_commodities": 2,
    "match_percentage": 96.7,
    "unmatched_samples": ["Unknown Product", "Invalid Name"]
  },
  
  "schema_validation": {
    "expected_columns": 16,
    "matched_columns": 16,
    "missing_columns": [],
    "unrecognized_columns": [],
    "match_percentage": 100.0
  },
  
  "error_messages": [
    "Row 25: Invalid date format",
    "Row 47: Missing required field"
  ]
}
```

### **Key Feedback Components**

#### **Status Codes**
- `success`: All rows processed without errors
- `partial_success`: Some rows succeeded, some failed (non-critical)
- `failed`: Critical error - all or most rows failed

#### **Row Metrics**
- `total_rows`: Total rows in file
- `rows_inserted`: New records created
- `rows_updated`: Existing records modified
- `rows_failed`: Failed to process

#### **Commodity Matching** (Stock Report)
- **matched_commodities**: Products found in commodity master
- **unmatched_commodities**: Products NOT in database (potential issues)
- **match_percentage**: % of rows with valid commodity match
- **unmatched_samples**: First 5 unmatched product names for debugging

**Why It Matters**: Helps identify missing master data or misspelled product names in source files.

#### **Schema Validation**
- **expected_columns**: Columns required for parsing
- **matched_columns**: Columns successfully found in file
- **missing_columns**: Required columns not found (parsing may fail)
- **unrecognized_columns**: Extra columns in file (usually ignored)
- **match_percentage**: % of expected columns found

**Why It Matters**: Detects column name variations (e.g., "Cost_Price" vs "CostPrice" vs "cost_price_mt_inr") that could cause parsing failures in future uploads. Allows detecting schema drift.

#### **Error Messages**
- First 10 errors recorded (row number + specific error)
- Helps debug problematic rows without processing entire file
- Examples: invalid date format, type conversion failures, constraint violations

### **Using Feedback in Frontend**

The upload response includes complete feedback:

```typescript
// Example in UploadPanel.tsx
const response = await axios.post('/api/uploads/inventory', formData);
const feedback = response.data.ingestion;

// Display status
console.log(`Status: ${feedback.status}`);
console.log(`Message: ${feedback.message}`);

// Show metrics
console.log(`Inserted: ${feedback.rows_inserted}`);
console.log(`Updated: ${feedback.rows_updated}`);
console.log(`Failed: ${feedback.rows_failed}`);

// Warn about unmatched commodities
if (feedback.commodity_match.unmatched_commodities > 0) {
  console.warn(
    `⚠️ ${feedback.commodity_match.unmatched_commodities} products not found in master data:`,
    feedback.commodity_match.unmatched_samples
  );
}

// Alert on schema issues
if (feedback.schema_validation.missing_columns.length > 0) {
  console.warn(
    `⚠️ Missing expected columns:`,
    feedback.schema_validation.missing_columns
  );
}

// Display errors
if (feedback.error_messages.length > 0) {
  console.error('First 10 errors:', feedback.error_messages);
}
```

---

## �📝 Key Implementation Details

### **Async/Await Pattern**
- All database operations use `async` functions with SQLAlchemy's async engine
- FastAPI routes are async for better concurrency
- Example:
  ```python
  async def load_inventory_targets_from_csv(file_path: str):
      async with async_session() as session:
          await session.execute(...)
          await session.commit()
  ```

### **Data Versioning (config_date)**
- Instead of explicit version numbers, uses `config_date`
- Multiple rows with same `commodity_id` but different dates = versions
- Example:
  ```
  commodity_id | config_date | desired_stock_level
  1           | 2026-05-20  | 1000
  1           | 2026-05-22  | 1200 (newer version)
  1           | 2026-05-25  | 1500 (current)
  ```

### **Commodity Matching Strategy**
1. Exact case-insensitive match (avoids "TOLUENE" vs "TOLUENE TDI" collisions)
2. Fuzzy matching fallback (70%+ similarity)
3. Normalization: uppercase + trim + collapse spaces

### **Vessel Data Deduplication (Comprehensive Uniqueness Key)**

For daily vessel stock uploads, the system uses an **expanded composite key** to determine uniqueness:

#### **Uniqueness Key Fields**
```
(date, vessel_name, vessel_date, product_name, port_name, 
 company_terminal_name, company_name,
 unsold_qty, sold_qty_pending_lifting, physical_stock, otr_qty,
 cost_price_INR, average_selling_price_INR, no_of_days_of_stock)
```

#### **Behavior**

| Scenario | Action | Result |
|----------|--------|--------|
| Same vessel, SAME quantities on same day | Skip duplicate | No new row |
| Same vessel, DIFFERENT quantities on same day | Insert new row | Time-series tracking |
| Same vessel, any data on DIFFERENT day | Insert new row | Historical record |
| New vessel | Insert | New record |

#### **Example: Daily Upload Pattern**

```
May 22 Upload (morning):
├─ Vessel Alpha, 100 MT → INSERT
├─ Vessel Beta, 200 MT → INSERT
└─ Total: 2 rows inserted, 0 updated

May 22 Upload (reupload same file):
├─ Vessel Alpha, 100 MT → SKIP (exact duplicate)
├─ Vessel Beta, 200 MT → SKIP (exact duplicate)
└─ Total: 0 rows inserted, 2 duplicates skipped
└─ Feedback: rows_inserted=0, rows_updated=2, rows_failed=0

May 22 Upload (corrected quantities):
├─ Vessel Alpha, 120 MT → INSERT (different qty)
├─ Vessel Beta, 200 MT → SKIP (same)
└─ Total: 1 row inserted, 1 skipped
└─ DB now has 3 rows for May 22 (2 original, 1 updated)

May 23 Upload:
├─ Vessel Alpha, 90 MT → INSERT (different day)
├─ Vessel Beta, 180 MT → INSERT (different day)
└─ Total: 2 new rows for May 23
└─ DB now has 7 total rows (5 for May 22-23 historical data)
```

#### **Why This Matters**

✅ **Prevents accidental duplicates**: Re-uploading same file creates no duplicates
✅ **Tracks inventory changes**: Different quantities create new records (audit trail)
✅ **Supports corrections**: Corrected quantities inserted as new records
✅ **Historical accuracy**: Full time-series of all snapshots preserved

#### **Creating Fresh Table with Expanded Key**

Use this script to create the `inventory_detail` table with the comprehensive uniqueness constraint from scratch:

```bash
# Creates new table with expanded unique constraint
# Automatically backs up existing table if present
python backend/create_inventory_detail_table.py
```

This script:
- Creates table with all proper constraints built in
- Backs up existing table if present (no data loss)
- Works with both PostgreSQL and SQLite
- Provides verification that constraint is properly set

**For existing databases:**

```bash
# PostgreSQL: Has data, use migration script to avoid recreation
python backend/migrate_expand_inventory_key.py

# SQLite: Simpler to reset and recreate
rm jobs.db
python backend/init_db.py
```

### **Percentage Handling**
- CSV values like "12%" converted to decimal 0.12
- Stored as FLOAT in database
- API returns decimal values

---

## 📚 File Structure

```
dashboard-inventory/
├── backend/
│   ├── __init__.py
│   ├── database.py              # ORM models, engine config
│   ├── gcs.py                   # Google Cloud Storage integration
│   ├── load_commodities.py      # Load commodity master data
│   ├── load_inventory_targets.py # Load target configurations
│   ├── load_market_data.py      # Load market pricing
│   ├── load_stock_report.py     # Load stock reports (WIP)
│   ├── create_inventory_detail_table.py  # Create inventory_detail with expanded key
│   ├── migrate_add_target_fields.py      # Database migrations
│   ├── migrate_expand_inventory_key.py   # Expand uniqueness constraint (PostgreSQL)
│   ├── ingestion_feedback.py    # User feedback & schema validation
│   ├── routes/
│   │   ├── targets.py           # Targets API (CRUD + history)
│   │   ├── market_data.py       # Market data API
│   │   ├── inventory.py         # Inventory queries
│   │   └── uploads.py           # File upload handling
│   ├── requirements.txt
│   └── .env                     # Environment config
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main component
│   │   ├── components/
│   │   │   ├── UploadPanel.tsx  # Upload modal (330 lines)
│   │   │   ├── TargetEditor.tsx # Targets editor (380 lines)
│   │   │   ├── DataTable.tsx    # Data display
│   │   │   └── ...
│   │   ├── styles/
│   │   │   ├── animations.css
│   │   │   ├── colors.ts
│   │   │   └── ...
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── ...
├── data_files/
│   ├── inventory_targets.csv
│   ├── DAILY PRICE REPORT 22-05-2026.xlsx
│   ├── stock_report.xlsx
│   └── ...
├── readmes/
│   ├── README.md (old)
│   ├── README_UPDATED.md (this file)
│   ├── TARGETS_CSV_MAPPING.md
│   └── ...
├── main.py                      # FastAPI application entry point
└── jobs.db                      # SQLite database (development)
```

---

## 🔍 Current Status (May 27, 2026)

### ✅ Completed
- ✅ Backend API with 4 routers (targets, market_data, inventory, uploads)
- ✅ Frontend React UI with TypeScript and Vite
- ✅ Database schema with 8 tables
- ✅ Data loaders for commodities, targets, market data
- ✅ Async/await patterns throughout
- ✅ Pydantic validation models
- ✅ Modal-based UI (UploadPanel, TargetEditor)
- ✅ CSV/Excel parsing with pandas
- ✅ Auto-versioning via config_date
- ✅ 34 commodities loaded
- ✅ 34 commodity targets loaded
- ✅ 60 market data records loaded

### 🟡 In Progress
- 🟡 Stock report loader (load_stock_report.py)
- 🟡 Advanced analytics and insights
- 🟡 Performance optimization for large datasets

### 🔮 Future Enhancements
- 📋 Automated alerts for stock levels
- 📊 Advanced forecasting and predictions
- 🔔 Real-time notifications
- 📧 Email alerts for critical stock events
- 📱 Mobile app
- 🔐 User authentication and role-based access

---

## 💬 Support & Documentation

**API Documentation**: Visit `http://localhost:8000/docs` for interactive Swagger UI

**Schema Reference**: See [TARGETS_CSV_MAPPING.md](TARGETS_CSV_MAPPING.md) for detailed column mappings

**Development**: Ensure Python 3.11+ and Node 18+ are installed

---

**Last Updated**: May 27, 2026
**Maintained By**: Dashboard Inventory Team
