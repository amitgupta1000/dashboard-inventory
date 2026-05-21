# Excel to Database Schema Mapping Guide

## 📋 Excel File Structure Analysis

**File:** 12-5-26.xlsx  
**Worksheet:** 12-05-2026 (date-based naming)  
**Total Records:** 154 data rows (multiple commodities, vessels, terminals)

---

## 🗺️ Column Mapping

| Excel Column | Header | Sample Data | Maps To Database | Notes |
|------|--------|-------------|------------------|-------|
| A | DATE | 2026-05-12 | `inventory_records.report_date` | All rows share same date |
| B | VESSEL DATE | 2025-11-22 | `vessels.vessel_date` | Arrival/loading date of each vessel |
| C | VESSEL NAME | F-6243 BOW ENDEAVOR | `vessels.vessel_name` | Unique ship identifier |
| D | PRODUCT NAME | ACETIC ACID | `commodities.commodity_name` | The commodity being stored |
| E | PORT | MUMBAI, JNPT, KANDLA | `terminals.port` | Storage location (warehouse port) |
| F | UNSOLD QTY | 0, 1891.307 | `vessels.unsold_qty` | Available for sale from this vessel |
| G | UNSOLD QTY | (empty) | (duplicate header) | Appears to be redundant column |
| H | SOLD QTY/PENDING LIFTING | Formula: =I-F | `inventory_records.sold_qty_pending` | Already sold, awaiting customer pickup |
| I | PHYSICAL STOCK | 0.14, 46.577 | `vessels.physical_stock` | Total quantity on hand |
| J | OTR QTY | 1573.43, 1425 | `inventory_records.other_qty` | Other/miscellaneous quantity |
| K | TERMINAL | AEGIS, GBL (SELORD), RKT+AHIR | `terminals.terminal_name` | Warehouse/storage facility name |
| L | (blank) | (none) | (unused) | Empty column |
| M | NO OF DAYS OF STOCK | Formula: =TODAY()-B | `inventory_records.inventory_age_days` | Age of inventory in days |
| N | IMPORT PRICE ($) MT | (empty in data) | `inventory_records.import_price_per_unit` | Cost price per unit - **MISSING IN FILE** |

---

## 🔗 Key Relationships from Excel Data

### Multi-Level Grouping

The data naturally groups hierarchically:

```
Company (implicit)
  └─ Terminal (column K: AEGIS, GBL, RKT+AHIR, ADANI)
      └─ Commodity (column D: ACETIC ACID, 2-ETHYLHEXANOL, etc.)
          └─ Vessel (column C: F-6243 BOW ENDEAVOR, F-6316 TG CRAB, etc.)
              └─ Physical Stock (column I)
```

### Aggregation Strategy

1. **Vessel Level:** Each row in the file represents one vessel
2. **Terminal + Commodity Level:** Multiple vessels are aggregated by terminal + commodity into `InventoryRecord`
3. **Company Level:** All terminals + commodities aggregate to `SummaryByCompany`

**Example from data:**
- **ACETIC ACID at AEGIS (from 4 different vessels):**
  - F-6243 BOW ENDEAVOR (2025-11-22): 0.14 MT
  - F-6316 TG CRAB (2026-02-05): 2.87 MT
  - F-6302 YONG CHANG... (2026-02-21): 46.577 MT
  - F-6321 PVT LYRA (2026-03-08): 1172.079 MT
  - **Aggregated:** 1221.656 MT at AEGIS terminal

---

## 📊 Data Import Flow

### Step 1: Identify/Create Master Data

**From Column D - Commodity:**
```python
commodity = get_or_create_commodity(
    name="ACETIC ACID",
    code="AA",  # Auto-generate if not provided
    category="Chemical",
    unit_of_measure="MT"
)
```

**From Columns K, E - Terminal:**
```python
terminal = get_or_create_terminal(
    company_id=1,  # Need to determine from context
    name="AEGIS",
    port="MUMBAI",
    code="AEGIS_MUM"  # Composite of terminal + port
)
```

### Step 2: Create Daily Report Header

```python
report = InventoryReport(
    company_id=1,
    report_date=datetime(2026, 5, 12),  # From column A
    file_name="12-5-26.xlsx",
    submitted_by="analyst@company.com"  # Manual input
)
```

### Step 3: Group Vessels by Terminal + Commodity

```python
# Aggregate all rows with same (Terminal, Commodity) combination
groups = defaultdict(list)
for row in excel_rows:
    key = (row.terminal, row.commodity)
    groups[key].append(row)
```

### Step 4: Create InventoryRecord (Aggregated)

```python
for (terminal, commodity), vessel_rows in groups.items():
    record = InventoryRecord(
        report_id=report.id,
        terminal_id=terminal.id,
        commodity_id=commodity.id,
        
        # Aggregate across all vessels
        physical_stock=sum(v.physical_stock for v in vessel_rows),
        unsold_qty=sum(v.unsold_qty for v in vessel_rows),
        sold_qty_pending=sum(v.sold_qty_pending for v in vessel_rows),
        
        # Vessel metadata
        num_vessels=len(vessel_rows),
        earliest_vessel_date=min(v.vessel_date for v in vessel_rows),
        latest_vessel_date=max(v.vessel_date for v in vessel_rows),
        
        # Use first non-null price found
        import_price_per_unit=next(
            (v.import_price for v in vessel_rows if v.import_price),
            None
        ),
        
        # Calculate age based on earliest vessel
        inventory_age_days=(report.report_date - earliest_vessel_date).days
    )
    record.save()
    
    # Create individual vessel records for drill-down
    for vessel_row in vessel_rows:
        vessel = Vessel(
            inventory_record_id=record.id,
            vessel_name=vessel_row.vessel_name,
            vessel_date=vessel_row.vessel_date,
            unsold_qty=vessel_row.unsold_qty,
            sold_qty=vessel_row.sold_qty_pending,
            physical_stock=vessel_row.physical_stock,
            other_qty=vessel_row.other_qty
        )
        vessel.save()
```

---

## ⚠️ Data Quality Issues in Sample File

### 1. **Missing Cost Price Data** (Column N is empty)
   - **Impact:** Cannot calculate COGS, mark-to-market, or gross profit
   - **Solution:** Import prices from:
     - Historical purchase records
     - Manual entry via Configuration Panel
     - External price feed

### 2. **Formula-Based Calculations** (Columns F, H, M)
   - **Current:** Excel formulas (e.g., `=I3-F3`, `=TODAY()-B3`)
   - **Import Issue:** Formulas don't evaluate in most import libraries
   - **Solution:** Either:
     - Pre-calculate in Excel and paste values only
     - Recalculate in database import script
     - Add validation logic to flag unexpected values

### 3. **Implicit Company Mapping**
   - **Issue:** No company column; terminals map to companies implicitly
   - **Solution:** Create configuration mapping:
     ```python
     TERMINAL_TO_COMPANY = {
         "AEGIS": "Company A",
         "GBL (SELORD)": "Company A",
         "RKT+AHIR": "Company B",
         "ADANI": "Company C"
     }
     ```

### 4. **Port Duplicates Across Terminals**
   - **Data:** Multiple terminals at same port (AEGIS and GBL both at MUMBAI)
   - **Solution:** Use composite key: `terminal_code + port` or add warehouse distinction

### 5. **Column Duplication** (Columns F & G - both "UNSOLD QTY")
   - **Likely Reason:** Data entry error or formatting artifact
   - **Handling:** Use column F, ignore column G

---

## 💾 SQL Insert Example

Given an aggregated record for ACETIC ACID at AEGIS on 2026-05-12:

```sql
-- Create inventory record
INSERT INTO inventory_records (
    report_id, terminal_id, commodity_id,
    physical_stock, unsold_qty, sold_qty_pending,
    num_vessels, earliest_vessel_date, latest_vessel_date,
    import_price_per_unit, inventory_age_days
) VALUES (
    1,  -- report_id (from InventoryReport)
    2,  -- terminal_id (AEGIS)
    1,  -- commodity_id (ACETIC ACID)
    1221.656,  -- Sum of all vessel stocks
    1895.307,  -- Sum of unsold quantities
    0,  -- Sum of sold_qty_pending (none in this batch)
    4,  -- Number of vessels
    '2025-11-22',  -- Earliest vessel date
    '2026-03-08',  -- Latest vessel date
    NULL,  -- import_price_per_unit (missing in data)
    172  -- Days since oldest vessel (2026-05-12 - 2025-11-22)
);

-- Create individual vessel records
INSERT INTO vessels (inventory_record_id, vessel_name, vessel_date, unsold_qty, physical_stock)
VALUES
    (1, 'F-6243 BOW ENDEAVOR', '2025-11-22', 0, 0.14),
    (1, 'F-6316 TG CRAB', '2026-02-05', 0, 2.87),
    (1, 'F-6302 YONG CHANG SHUN HANG', '2026-02-21', 0, 46.577),
    (1, 'F-6321 PVT LYRA', '2026-03-08', 1891.307, 1172.079);
```

---

## 🔄 Missing Data to Add

For complete insights functionality, add these columns to future imports:

| Data | Current Status | Source | Frequency |
|------|---|---|---|
| **Import Price** | ❌ Missing | Purchase invoices | Daily |
| **Current Market Price** | ❌ Missing | Market data feed | Daily |
| **Replacement Cost** | ❌ Missing | Vendor quotes | Weekly |
| **Desired Stock Level** | ❌ Missing | Configuration | As needed |
| **Target Days** | ❌ Missing | Configuration | As needed |
| **Expected Sale Timeline** | ❌ Missing | Sales forecast | Weekly |
| **Cash Realization Rate** | ❌ Missing | Historical data | Monthly |

---

## ✅ Data Validation Rules

```python
# Rules to validate before import
validation_rules = {
    "report_date": lambda x: x is not None and x.date() <= today,
    "vessel_date": lambda x: x is not None and x <= report_date,
    "physical_stock": lambda x: x >= 0,
    "unsold_qty": lambda x: x is None or x >= 0,
    "inventory_age_days": lambda x: x >= 0 and x <= 3650,  # Max 10 years
    "commodity_name": lambda x: len(x.strip()) > 0,
    "terminal_name": lambda x: len(x.strip()) > 0,
    "vessel_name": lambda x: len(x.strip()) > 0,
}
```

---

## 📝 Configuration Panel Fields

Once imported, the Configuration Panel (left drawer) should allow editing:

```python
commodity_settings = {
    "commodity": "ACETIC ACID",
    "company": "Company A",
    
    # Stock Targets
    "desired_stock_level": 1000,      # MT
    "min_stock_level": 500,           # MT
    "max_stock_level": 2000,          # MT
    
    # Financial Parameters
    "cost_price_per_unit": 480,       # $/MT (can override import_price)
    "replacement_cost_per_unit": 520, # $/MT
    "expected_gross_margin": 0.05,    # 5%
    
    # Inventory Management
    "target_inventory_days": 30,      # Days
    "estimated_days_to_sale": 15,     # Days
    "cash_realization_rate": 0.95,    # 95% of expected price
    
    # Thresholds
    "annual_cost_of_capital": 0.08,   # 8%
}
```

