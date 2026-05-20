# Intelligence & Analytics Features

## Overview
The Inventory Dashboard now includes comprehensive intelligence features that analyze stock levels, compare them to thresholds, and provide actionable insights through natural language summaries.

## Key Features

### 1. Product Intelligence Summary (`v_product_intelligence_summary`)
Aggregates inventory by product and provides:
- **Stock Status Analysis**: Compares current stock to safety/reorder thresholds
  - `CRITICAL`: Stock below safety level - immediate action required
  - `WARNING`: Stock below reorder point - procurement needed
  - `EXCESS`: Stock above 3x monthly target - reduce procurement
  - `NORMAL`: Stock within optimal range

- **Days of Stock Calculation**: Shows how many days the current stock will last based on monthly consumption
- **Gap Analysis**: Calculates shortage or excess quantities
- **Profitability Metrics**: Profit margin percentage
- **Target Fulfillment**: Percentage of monthly target covered by current stock

### 2. Shipment Intelligence (`v_shipment_intelligence`)
Analyzes individual shipments with:
- **Aging Analysis**: 
  - `AGED`: Stock exceeds max storage days - liquidation recommended
  - `AGING_SOON`: Stock approaching max storage limit (>80%)
  - `FRESH`: Stock within acceptable age

- **Movement Velocity**: Days required to deplete current stock
- **Price Variance**: Comparison between market price and purchase price
- **Recommended Actions**:
  - `URGENT_REORDER`: Stock critically low
  - `REORDER_RECOMMENDED`: Stock approaching reorder point
  - `LIQUIDATE_AGED_STOCK`: Inventory aged beyond limit
  - `REDUCE_PROCUREMENT`: Excess inventory detected
  - `MONITOR`: No action needed

- **Risk Flags**: Array of risk indicators (LOW_STOCK, AGED_INVENTORY, EXCESS_STOCK, NEGATIVE_MARGIN)

### 3. Critical Alerts (`v_critical_alerts`)
Prioritized alerts system:
- **Priority 1** 🔴 CRITICAL: Stock below safety level
- **Priority 2** 🟠 URGENT: Aged inventory
- **Priority 3** 🟡 WARNING: Approaching reorder point  
- **Priority 4** 🔵 INFO: Excess stock

Each alert includes a human-readable message explaining the issue.

### 4. Natural Language Narrative (`v_inventory_narrative`)
Generates executive summary with:
- **Overall Health**: CRITICAL / NEEDS_ATTENTION / OVERSTOCKED / HEALTHY
- **Executive Summary**: Natural language paragraph summarizing inventory status
- **Key Metrics**:
  - Count of products in each status (critical, warning, excess, normal)
  - Average days of stock coverage
  - Total shortage and excess quantities
  - Average profit margin
  - Aged and aging-soon shipment counts

- **Recommended Actions**: Array of prioritized action items

### 5. Product-Specific Narrative (Function)
`get_product_narrative(product_name)` provides detailed analysis for individual products:
- Natural language description of product status
- Specific quantities and metrics
- Tailored action recommendations

## API Endpoints

### Intelligence Endpoints
```
GET /api/intelligence/summary
- Returns product-wise intelligence summary
- Sorted by status priority (critical first)

GET /api/intelligence/shipments
- Returns shipment-level intelligence with aging analysis
- Sorted by recommended action priority

GET /api/intelligence/alerts
- Returns prioritized critical alerts
- Limited to top issues requiring attention

GET /api/intelligence/narrative
- Returns natural language executive summary
- Includes overall health status and recommendations

GET /api/intelligence/product/{product_name}
- Returns detailed narrative for specific product
- Includes status and action recommendations
```

## Frontend Components

### Insights Dashboard Tab
Located at: `frontend/src/components/InsightsDashboard.tsx`

Features:
1. **Executive Summary Card**
   - Overall health indicator with color coding
   - Natural language summary paragraph
   - Status breakdown (Critical/Warning/Excess/Normal counts)
   - Recommended actions list

2. **Critical Alerts Panel**
   - Color-coded alerts by priority
   - Shows top 10 most critical issues
   - Detailed alert messages

3. **Product Intelligence Table**
   - Comprehensive view of all products
   - Status badges with color coding
   - Key metrics (current stock, days coverage, margins)
   - Interactive "Details" button for product-specific narratives
   - Visual indicators for low stock and margins

4. **Product Detail Modal**
   - Natural language analysis for selected product
   - Status indicator
   - Specific action recommendations

### Visual Indicators
- 🔴 Red: Critical issues requiring immediate attention
- 🟠 Orange: Urgent issues needing action soon
- 🟡 Yellow: Warnings and potential issues
- 🔵 Blue: Informational (excess stock)
- 🟢 Green: Normal/healthy status

## Intelligence Logic

### Stock Status Determination
```sql
CASE
    WHEN current_stock < safety_stock THEN 'CRITICAL'
    WHEN current_stock < reorder_point THEN 'WARNING'
    WHEN current_stock > (monthly_target * 3) THEN 'EXCESS'
    ELSE 'NORMAL'
END
```

### Days of Stock Calculation
```sql
days_of_stock = current_stock / (monthly_target_volume / 30)
```

### Aging Status
```sql
CASE
    WHEN days_in_stock > max_storage_days THEN 'AGED'
    WHEN days_in_stock > (max_storage_days * 0.8) THEN 'AGING_SOON'
    ELSE 'FRESH'
END
```

### Profit Margin
```sql
profit_margin = ((selling_price - purchase_price) / purchase_price) * 100
```

## Usage Examples

### 1. Check Overall Inventory Health
Navigate to "Intelligence & Insights" tab to see:
- Executive summary with overall health status
- Count of products in each status category
- Recommended actions

### 2. Identify Critical Issues
View the Critical Alerts panel for:
- Prioritized list of issues
- Specific products requiring attention
- Alert messages explaining the problem

### 3. Analyze Product Performance
In the Product Intelligence Table:
- Review days of stock coverage for each product
- Check profit margins
- Identify shortage or excess quantities
- Click "Details" for specific product analysis

### 4. Make Procurement Decisions
Use the intelligence data to:
- Identify products needing immediate reorder (CRITICAL status)
- Plan procurement for products approaching reorder point (WARNING)
- Reduce orders for overstocked items (EXCESS)
- Prioritize liquidation of aged inventory

## Database Setup

Run these SQL scripts in order:
1. `schema_product_settings.sql` - Product configuration table
2. `schema_inventory_dashboard.sql` - Main inventory schema
3. `schema_intelligence_views.sql` - Analytics views and functions

## Benefits

1. **Proactive Management**: Identify issues before they become critical
2. **Data-Driven Decisions**: Use actual consumption rates and aging data
3. **Natural Language Insights**: Easy-to-understand summaries for stakeholders
4. **Prioritized Actions**: Focus on highest-impact issues first
5. **Cost Optimization**: Reduce carrying costs by identifying excess stock
6. **Risk Mitigation**: Flag aged inventory before it becomes unsellable
7. **Profitability Tracking**: Monitor margins at product level

## Next Steps

Consider adding:
- Email/SMS alerts for critical status changes
- Historical trend analysis
- Predictive analytics for demand forecasting
- Automated reorder suggestions
- Integration with procurement systems
