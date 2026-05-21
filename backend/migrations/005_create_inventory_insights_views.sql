-- Inventory Insights Views Migration
-- Creates summary views at Company/Product/Port, Product/Port, and Port levels
-- Includes stock status flags, mark-to-market valuations, and holding cost calculations
-- Created: 2026-05-21

-- ============================================================================
-- LEVEL 1: COMPANY/PRODUCT/PORT SUMMARY VIEW
-- ============================================================================
CREATE OR REPLACE VIEW v_inventory_summary_company_product_port AS
SELECT
    id.company_terminal_name,
    id.product_name,
    id.port_name,
    
    -- Quantities
    SUM(id.unsold_qty) AS total_unsold_qty,
    SUM(id.physical_stock) AS total_physical_stock,
    SUM(id.sold_qty_pending_lifting) AS total_sold_pending,
    COUNT(DISTINCT id.vessel_name) AS num_vessels,
    
    -- Latest record date for this aggregation
    MAX(id.date) AS latest_record_date,
    
    -- Pricing - Weighted Average Purchase Price
    CASE 
        WHEN SUM(id.unsold_qty) > 0 
        THEN SUM(id.unsold_qty * id.purchase_price_USD) / SUM(id.unsold_qty)
        ELSE NULL 
    END AS weighted_avg_purchase_price_USD,
    
    CASE 
        WHEN SUM(id.unsold_qty) > 0 
        THEN SUM(id.unsold_qty * id.cost_price_INR) / SUM(id.unsold_qty)
        ELSE NULL 
    END AS weighted_avg_cost_price_INR,
    
    -- Market pricing from latest daily metrics
    pdm.market_price AS current_market_price_INR,
    
    -- Mark-to-market comparison
    CASE 
        WHEN pdm.market_price IS NOT NULL AND 
             CASE WHEN SUM(id.unsold_qty) > 0 
                  THEN SUM(id.unsold_qty * id.cost_price_INR) / SUM(id.unsold_qty)
                  ELSE NULL END IS NOT NULL
        THEN pdm.market_price - 
             (CASE WHEN SUM(id.unsold_qty) > 0 
                   THEN SUM(id.unsold_qty * id.cost_price_INR) / SUM(id.unsold_qty)
                   ELSE NULL END)
        ELSE NULL
    END AS mark_to_market_variance_INR,
    
    -- Holding cost calculation: 0.5% per month of (unsold qty × purchase price)
    -- Based on days held from max date to today
    CASE 
        WHEN SUM(id.unsold_qty) > 0 AND MAX(id.date) IS NOT NULL
        THEN (SUM(id.unsold_qty) * 
              CASE WHEN SUM(id.unsold_qty) > 0 
                   THEN SUM(id.unsold_qty * id.cost_price_INR) / SUM(id.unsold_qty)
                   ELSE NULL END) * 
             (EXTRACT(DAY FROM (CURRENT_DATE - MAX(id.date))) / 30.0) * 0.005
        ELSE NULL
    END AS holding_cost_to_date_INR,
    
    -- Stock level status
    CASE
        WHEN pdm.safety_stock_level IS NOT NULL AND SUM(id.physical_stock) < pdm.safety_stock_level 
        THEN 'CRITICAL'
        WHEN pdm.reorder_stock_level IS NOT NULL AND SUM(id.physical_stock) < pdm.reorder_stock_level 
        THEN 'WARNING'
        ELSE 'OK'
    END AS stock_status_flag,
    
    pdm.safety_stock_level,
    pdm.reorder_stock_level,
    
    CURRENT_TIMESTAMP AS view_generated_at
FROM inventory_detail id
LEFT JOIN product_daily_metrics pdm 
    ON id.product_name = pdm.product_name 
    AND pdm.metric_date = (
        SELECT MAX(metric_date) 
        FROM product_daily_metrics 
        WHERE product_name = id.product_name
    )
GROUP BY 
    id.company_terminal_name, 
    id.product_name, 
    id.port_name,
    pdm.market_price,
    pdm.safety_stock_level,
    pdm.reorder_stock_level
ORDER BY 
    id.company_terminal_name, 
    id.product_name, 
    id.port_name;


-- ============================================================================
-- LEVEL 2: PRODUCT/PORT SUMMARY VIEW
-- ============================================================================
CREATE OR REPLACE VIEW v_inventory_summary_product_port AS
SELECT
    id.product_name,
    id.port_name,
    
    -- Quantities
    SUM(id.unsold_qty) AS total_unsold_qty,
    SUM(id.physical_stock) AS total_physical_stock,
    SUM(id.sold_qty_pending_lifting) AS total_sold_pending,
    COUNT(DISTINCT id.vessel_name) AS num_vessels,
    COUNT(DISTINCT id.company_terminal_name) AS num_terminals,
    
    -- Latest record date
    MAX(id.date) AS latest_record_date,
    
    -- Pricing - Weighted Average Cost Price
    CASE 
        WHEN SUM(id.unsold_qty) > 0 
        THEN SUM(id.unsold_qty * id.cost_price_INR) / SUM(id.unsold_qty)
        ELSE NULL 
    END AS weighted_avg_cost_price_INR,
    
    -- Market pricing
    pdm.market_price AS current_market_price_INR,
    
    -- Mark-to-market variance
    CASE 
        WHEN pdm.market_price IS NOT NULL AND 
             CASE WHEN SUM(id.unsold_qty) > 0 
                  THEN SUM(id.unsold_qty * id.cost_price_INR) / SUM(id.unsold_qty)
                  ELSE NULL END IS NOT NULL
        THEN pdm.market_price - 
             (CASE WHEN SUM(id.unsold_qty) > 0 
                   THEN SUM(id.unsold_qty * id.cost_price_INR) / SUM(id.unsold_qty)
                   ELSE NULL END)
        ELSE NULL
    END AS mark_to_market_variance_INR,
    
    -- Holding cost
    CASE 
        WHEN SUM(id.unsold_qty) > 0 AND MAX(id.date) IS NOT NULL
        THEN (SUM(id.unsold_qty) * 
              CASE WHEN SUM(id.unsold_qty) > 0 
                   THEN SUM(id.unsold_qty * id.cost_price_INR) / SUM(id.unsold_qty)
                   ELSE NULL END) * 
             (EXTRACT(DAY FROM (CURRENT_DATE - MAX(id.date))) / 30.0) * 0.005
        ELSE NULL
    END AS holding_cost_to_date_INR,
    
    -- Stock status
    CASE
        WHEN pdm.safety_stock_level IS NOT NULL AND SUM(id.physical_stock) < pdm.safety_stock_level 
        THEN 'CRITICAL'
        WHEN pdm.reorder_stock_level IS NOT NULL AND SUM(id.physical_stock) < pdm.reorder_stock_level 
        THEN 'WARNING'
        ELSE 'OK'
    END AS stock_status_flag,
    
    pdm.safety_stock_level,
    pdm.reorder_stock_level,
    
    CURRENT_TIMESTAMP AS view_generated_at
FROM inventory_detail id
LEFT JOIN product_daily_metrics pdm 
    ON id.product_name = pdm.product_name 
    AND pdm.metric_date = (
        SELECT MAX(metric_date) 
        FROM product_daily_metrics 
        WHERE product_name = id.product_name
    )
GROUP BY 
    id.product_name, 
    id.port_name,
    pdm.market_price,
    pdm.safety_stock_level,
    pdm.reorder_stock_level
ORDER BY 
    id.product_name, 
    id.port_name;


-- ============================================================================
-- LEVEL 3: PORT SUMMARY VIEW
-- ============================================================================
CREATE OR REPLACE VIEW v_inventory_summary_port AS
SELECT
    id.port_name,
    
    -- Quantities
    SUM(id.unsold_qty) AS total_unsold_qty,
    SUM(id.physical_stock) AS total_physical_stock,
    SUM(id.sold_qty_pending_lifting) AS total_sold_pending,
    COUNT(DISTINCT id.product_name) AS num_products,
    COUNT(DISTINCT id.vessel_name) AS num_vessels,
    COUNT(DISTINCT id.company_terminal_name) AS num_terminals,
    
    -- Latest record date
    MAX(id.date) AS latest_record_date,
    
    -- Overall weighted average cost (across all products)
    CASE 
        WHEN SUM(id.unsold_qty) > 0 
        THEN SUM(id.unsold_qty * id.cost_price_INR) / SUM(id.unsold_qty)
        ELSE NULL 
    END AS weighted_avg_cost_price_INR,
    
    -- Total holding cost across port
    CASE 
        WHEN SUM(id.unsold_qty) > 0 AND MAX(id.date) IS NOT NULL
        THEN (SUM(id.unsold_qty) * 
              CASE WHEN SUM(id.unsold_qty) > 0 
                   THEN SUM(id.unsold_qty * id.cost_price_INR) / SUM(id.unsold_qty)
                   ELSE NULL END) * 
             (EXTRACT(DAY FROM (CURRENT_DATE - MAX(id.date))) / 30.0) * 0.005
        ELSE NULL
    END AS total_holding_cost_to_date_INR,
    
    -- Count of products at each stock level
    SUM(CASE WHEN pdm.safety_stock_level IS NOT NULL AND id.physical_stock < pdm.safety_stock_level THEN 1 ELSE 0 END) AS products_at_critical_level,
    SUM(CASE WHEN pdm.reorder_stock_level IS NOT NULL AND id.physical_stock < pdm.reorder_stock_level AND (pdm.safety_stock_level IS NULL OR id.physical_stock >= pdm.safety_stock_level) THEN 1 ELSE 0 END) AS products_at_warning_level,
    
    CURRENT_TIMESTAMP AS view_generated_at
FROM inventory_detail id
LEFT JOIN product_daily_metrics pdm 
    ON id.product_name = pdm.product_name 
    AND pdm.metric_date = (
        SELECT MAX(metric_date) 
        FROM product_daily_metrics 
        WHERE product_name = id.product_name
    )
GROUP BY 
    id.port_name
ORDER BY 
    id.port_name;


-- ============================================================================
-- INDEXING VIEWS - Grant SELECT permissions and add supporting indexes
-- ============================================================================

-- Create indexes on inventory_detail for view performance
CREATE INDEX IF NOT EXISTS idx_inventory_detail_company_product_port 
    ON inventory_detail (company_terminal_name, product_name, port_name);

CREATE INDEX IF NOT EXISTS idx_inventory_detail_unsold_qty 
    ON inventory_detail (unsold_qty);
