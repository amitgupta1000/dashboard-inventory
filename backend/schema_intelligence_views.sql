-- Intelligent Analytics Views for Inventory Dashboard
-- These views provide actionable insights based on stock levels and thresholds

-- =========================================================================
-- VIEW 1: Product-wise Summary with Threshold Analysis
-- Aggregates inventory by product and compares to safety/reorder thresholds
-- =========================================================================
CREATE OR REPLACE VIEW v_product_intelligence_summary AS
WITH inventory_aggregates AS (
    SELECT
        i.item,
        i.company,
        i.port,
        COUNT(*) as shipment_count,
        SUM(i.physical_stock) as total_physical_stock,
        SUM(i.ready_unsold) as total_ready_unsold,
        SUM(i.incoming_qty) as total_incoming_qty,
        AVG(i.market_price) as avg_market_price,
        AVG(i.selling_price) as avg_selling_price,
        AVG(i.purchase_price) as avg_purchase_price,
        AVG(i.cif_duty) as avg_cif_duty,
        -- Calculate weighted average costs
        CASE 
            WHEN SUM(i.physical_stock) > 0 
            THEN SUM(i.physical_stock * COALESCE(i.purchase_price, 0)) / SUM(i.physical_stock)
            ELSE NULL 
        END as weighted_avg_purchase_price,
        MIN(i.record_date) as oldest_stock_date,
        MAX(i.record_date) as latest_stock_date
    FROM inventory i
    GROUP BY i.item, i.company, i.port
),
product_totals AS (
    SELECT
        item,
        SUM(total_physical_stock) as total_stock_all_locations,
        SUM(total_ready_unsold) as total_unsold_all_locations,
        SUM(total_incoming_qty) as total_incoming_all_locations,
        AVG(avg_market_price) as overall_avg_market_price,
        AVG(avg_selling_price) as overall_avg_selling_price,
        AVG(avg_purchase_price) as overall_avg_purchase_price,
        COUNT(DISTINCT company) as company_count,
        COUNT(DISTINCT port) as port_count
    FROM inventory_aggregates
    GROUP BY item
)
SELECT
    pt.item,
    pt.total_stock_all_locations,
    pt.total_unsold_all_locations,
    pt.total_incoming_all_locations,
    pt.overall_avg_market_price,
    pt.overall_avg_selling_price,
    pt.overall_avg_purchase_price,
    
    -- Threshold comparisons
    ps.safety_stock,
    ps.reorder_point,
    ps.max_storage_days,
    ps.max_inventory_days,
    ps.monthly_target_volume,
    
    -- Days of stock calculation
    CASE 
        WHEN ps.monthly_target_volume > 0 AND pt.total_stock_all_locations IS NOT NULL
        THEN ROUND((pt.total_stock_all_locations / (ps.monthly_target_volume / 30.0))::numeric, 1)
        ELSE NULL 
    END as days_of_stock_remaining,
    
    -- Stock status indicators
    CASE
        WHEN pt.total_stock_all_locations < ps.safety_stock THEN 'CRITICAL'
        WHEN pt.total_stock_all_locations < ps.reorder_point THEN 'WARNING'
        WHEN pt.total_stock_all_locations > (ps.monthly_target_volume * 3) THEN 'EXCESS'
        ELSE 'NORMAL'
    END as stock_status,
    
    -- Gap analysis
    CASE 
        WHEN pt.total_stock_all_locations < ps.safety_stock 
        THEN ps.safety_stock - pt.total_stock_all_locations
        ELSE 0 
    END as shortage_qty,
    
    CASE 
        WHEN pt.total_stock_all_locations > (ps.monthly_target_volume * 3)
        THEN pt.total_stock_all_locations - (ps.monthly_target_volume * 3)
        ELSE 0 
    END as excess_qty,
    
    -- Profitability indicators
    CASE 
        WHEN pt.overall_avg_purchase_price > 0 AND pt.overall_avg_selling_price > 0
        THEN ROUND(((pt.overall_avg_selling_price - pt.overall_avg_purchase_price) / pt.overall_avg_purchase_price * 100)::numeric, 2)
        ELSE NULL 
    END as profit_margin_percent,
    
    -- Demand fulfillment
    CASE 
        WHEN ps.monthly_target_volume > 0 AND pt.total_stock_all_locations IS NOT NULL
        THEN ROUND((pt.total_stock_all_locations / ps.monthly_target_volume * 100)::numeric, 1)
        ELSE NULL 
    END as target_fulfillment_percent,
    
    pt.company_count,
    pt.port_count,
    NOW() as computed_at
    
FROM product_totals pt
LEFT JOIN product_settings ps ON pt.item = ps.item AND ps.is_active = TRUE
ORDER BY 
    CASE 
        WHEN pt.total_stock_all_locations < ps.safety_stock THEN 1
        WHEN pt.total_stock_all_locations < ps.reorder_point THEN 2
        ELSE 3
    END,
    pt.item;

-- =========================================================================
-- VIEW 2: Shipment-Level Intelligence with Aging Analysis
-- Applies inventory days controls to individual shipments
-- =========================================================================
CREATE OR REPLACE VIEW v_shipment_intelligence AS
SELECT
    i.id,
    i.record_date,
    i.item,
    i.port,
    i.company,
    i.physical_stock,
    i.ready_unsold,
    i.incoming_qty,
    i.arrival_date,
    i.purchase_price,
    i.selling_price,
    i.market_price,
    i.status as system_status,
    
    -- Product settings
    ps.safety_stock,
    ps.reorder_point,
    ps.max_storage_days,
    ps.max_inventory_days,
    ps.monthly_target_volume,
    
    -- Aging calculations
    CASE 
        WHEN i.record_date IS NOT NULL 
        THEN EXTRACT(DAY FROM (CURRENT_DATE - i.record_date))
        ELSE NULL 
    END as days_in_stock,
    
    -- Aging status
    CASE
        WHEN i.record_date IS NULL THEN 'UNKNOWN'
        WHEN EXTRACT(DAY FROM (CURRENT_DATE - i.record_date)) > ps.max_storage_days THEN 'AGED'
        WHEN EXTRACT(DAY FROM (CURRENT_DATE - i.record_date)) > (ps.max_storage_days * 0.8) THEN 'AGING_SOON'
        ELSE 'FRESH'
    END as aging_status,
    
    -- Movement velocity (days to deplete at current rate)
    CASE 
        WHEN ps.monthly_target_volume > 0 AND i.physical_stock > 0
        THEN ROUND((i.physical_stock / (ps.monthly_target_volume / 30.0))::numeric, 1)
        ELSE NULL 
    END as days_to_deplete,
    
    -- Price variance analysis
    CASE 
        WHEN i.market_price IS NOT NULL AND i.purchase_price IS NOT NULL AND i.purchase_price > 0
        THEN ROUND(((i.market_price - i.purchase_price) / i.purchase_price * 100)::numeric, 2)
        ELSE NULL 
    END as price_variance_percent,
    
    -- Action recommendations
    CASE
        WHEN i.physical_stock < ps.safety_stock THEN 'URGENT_REORDER'
        WHEN i.physical_stock < ps.reorder_point THEN 'REORDER_RECOMMENDED'
        WHEN EXTRACT(DAY FROM (CURRENT_DATE - i.record_date)) > ps.max_storage_days THEN 'LIQUIDATE_AGED_STOCK'
        WHEN i.ready_unsold > (ps.monthly_target_volume * 2) THEN 'REDUCE_PROCUREMENT'
        ELSE 'MONITOR'
    END as recommended_action,
    
    -- Risk flags
    ARRAY_REMOVE(ARRAY[
        CASE WHEN i.physical_stock < ps.safety_stock THEN 'LOW_STOCK' END,
        CASE WHEN EXTRACT(DAY FROM (CURRENT_DATE - i.record_date)) > ps.max_storage_days THEN 'AGED_INVENTORY' END,
        CASE WHEN i.ready_unsold > (ps.monthly_target_volume * 3) THEN 'EXCESS_STOCK' END,
        CASE WHEN i.market_price < i.purchase_price THEN 'NEGATIVE_MARGIN' END
    ], NULL) as risk_flags,
    
    NOW() as computed_at
    
FROM inventory i
LEFT JOIN product_settings ps ON i.item = ps.item AND ps.is_active = TRUE
ORDER BY 
    CASE 
        WHEN i.physical_stock < ps.safety_stock THEN 1
        WHEN EXTRACT(DAY FROM (CURRENT_DATE - i.record_date)) > ps.max_storage_days THEN 2
        WHEN i.physical_stock < ps.reorder_point THEN 3
        ELSE 4
    END,
    i.record_date;

-- =========================================================================
-- VIEW 3: Critical Alerts with Prioritization
-- Identifies all critical issues across inventory
-- =========================================================================
CREATE OR REPLACE VIEW v_critical_alerts AS
WITH alert_data AS (
    SELECT
        item,
        company,
        port,
        physical_stock,
        safety_stock,
        reorder_point,
        record_date,
        EXTRACT(DAY FROM (CURRENT_DATE - record_date)) as days_old,
        max_storage_days,
        ready_unsold,
        monthly_target_volume,
        CASE
            WHEN physical_stock < safety_stock THEN 1
            WHEN EXTRACT(DAY FROM (CURRENT_DATE - record_date)) > max_storage_days THEN 2
            WHEN physical_stock < reorder_point THEN 3
            WHEN ready_unsold > (monthly_target_volume * 3) THEN 4
            ELSE 5
        END as priority
    FROM v_shipment_intelligence
    WHERE recommended_action != 'MONITOR'
)
SELECT
    priority,
    CASE priority
        WHEN 1 THEN '🔴 CRITICAL - Stock Below Safety Level'
        WHEN 2 THEN '🟠 URGENT - Aged Inventory'
        WHEN 3 THEN '🟡 WARNING - Approaching Reorder Point'
        WHEN 4 THEN '🔵 INFO - Excess Stock'
        ELSE 'MONITOR'
    END as alert_type,
    item,
    company,
    port,
    physical_stock,
    safety_stock,
    reorder_point,
    days_old,
    max_storage_days,
    CASE priority
        WHEN 1 THEN CONCAT('Stock critically low: ', ROUND(physical_stock, 2), ' MT (Safety: ', safety_stock, ' MT)')
        WHEN 2 THEN CONCAT('Inventory aged: ', days_old, ' days (Max: ', max_storage_days, ' days)')
        WHEN 3 THEN CONCAT('Stock low: ', ROUND(physical_stock, 2), ' MT (Reorder: ', reorder_point, ' MT)')
        WHEN 4 THEN CONCAT('Excess inventory: ', ROUND(ready_unsold, 2), ' MT')
        ELSE 'No action needed'
    END as alert_message,
    NOW() as generated_at
FROM alert_data
ORDER BY priority, item;

-- =========================================================================
-- VIEW 4: Natural Language Summary
-- Generates human-readable insights
-- =========================================================================
CREATE OR REPLACE VIEW v_inventory_narrative AS
WITH summary_stats AS (
    SELECT
        COUNT(DISTINCT item) as total_products,
        COUNT(*) FILTER (WHERE stock_status = 'CRITICAL') as critical_count,
        COUNT(*) FILTER (WHERE stock_status = 'WARNING') as warning_count,
        COUNT(*) FILTER (WHERE stock_status = 'EXCESS') as excess_count,
        COUNT(*) FILTER (WHERE stock_status = 'NORMAL') as normal_count,
        ROUND(AVG(days_of_stock_remaining), 1) as avg_days_stock,
        SUM(shortage_qty) as total_shortage,
        SUM(excess_qty) as total_excess,
        ROUND(AVG(profit_margin_percent), 2) as avg_profit_margin
    FROM v_product_intelligence_summary
),
aged_stats AS (
    SELECT
        COUNT(*) FILTER (WHERE aging_status = 'AGED') as aged_count,
        COUNT(*) FILTER (WHERE aging_status = 'AGING_SOON') as aging_soon_count
    FROM v_shipment_intelligence
)
SELECT
    -- Overall health indicator
    CASE
        WHEN ss.critical_count > 0 THEN 'CRITICAL'
        WHEN ss.warning_count > 3 THEN 'NEEDS_ATTENTION'
        WHEN ss.excess_count > 2 THEN 'OVERSTOCKED'
        ELSE 'HEALTHY'
    END as overall_health,
    
    -- Executive summary
    CONCAT(
        'Inventory Status: ',
        CASE
            WHEN ss.critical_count > 0 THEN CONCAT('⚠️ CRITICAL - ', ss.critical_count, ' product(s) below safety stock. ')
            WHEN ss.warning_count > 0 THEN CONCAT('⚡ ', ss.warning_count, ' product(s) approaching reorder point. ')
            ELSE '✅ All products adequately stocked. '
        END,
        CASE
            WHEN aged.aged_count > 0 THEN CONCAT(aged.aged_count, ' shipment(s) aged beyond storage limits. ')
            ELSE ''
        END,
        CASE
            WHEN ss.excess_count > 0 THEN CONCAT(ss.excess_count, ' product(s) overstocked. ')
            ELSE ''
        END,
        'Average inventory coverage: ', COALESCE(ss.avg_days_stock::text, 'N/A'), ' days. ',
        CASE
            WHEN ss.avg_profit_margin IS NOT NULL THEN CONCAT('Average margin: ', ss.avg_profit_margin, '%. ')
            ELSE ''
        END
    ) as executive_summary,
    
    -- Detailed stats
    ss.total_products,
    ss.critical_count,
    ss.warning_count,
    ss.excess_count,
    ss.normal_count,
    ss.avg_days_stock,
    ss.total_shortage,
    ss.total_excess,
    ss.avg_profit_margin,
    aged.aged_count,
    aged.aging_soon_count,
    
    -- Action items
    ARRAY_REMOVE(ARRAY[
        CASE WHEN ss.critical_count > 0 THEN CONCAT('Urgent: Procure ', ROUND(ss.total_shortage, 0), ' MT to meet safety stock') END,
        CASE WHEN aged.aged_count > 0 THEN CONCAT('Liquidate ', aged.aged_count, ' aged shipment(s)') END,
        CASE WHEN ss.excess_count > 0 THEN CONCAT('Reduce procurement for ', ss.excess_count, ' overstocked item(s)') END,
        CASE WHEN ss.avg_days_stock < 15 THEN 'Review reorder points - low coverage across portfolio' END
    ], NULL) as recommended_actions,
    
    NOW() as generated_at
    
FROM summary_stats ss
CROSS JOIN aged_stats aged;

-- =========================================================================
-- FUNCTION: Generate product-specific narrative
-- =========================================================================
CREATE OR REPLACE FUNCTION get_product_narrative(product_name TEXT)
RETURNS TABLE (
    narrative TEXT,
    status TEXT,
    actions TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    WITH product_data AS (
        SELECT
            item,
            total_stock_all_locations,
            safety_stock,
            reorder_point,
            days_of_stock_remaining,
            stock_status,
            shortage_qty,
            excess_qty,
            profit_margin_percent
        FROM v_product_intelligence_summary
        WHERE item = product_name
    )
    SELECT
        CONCAT(
            'Product: ', pd.item, '. ',
            'Current stock: ', ROUND(pd.total_stock_all_locations, 2), ' MT. ',
            'Status: ', pd.stock_status, '. ',
            CASE
                WHEN pd.stock_status = 'CRITICAL' 
                THEN CONCAT('⚠️ Critically low - ', ROUND(pd.shortage_qty, 2), ' MT below safety stock. Immediate procurement required. ')
                WHEN pd.stock_status = 'WARNING'
                THEN CONCAT('⚡ Stock low - approaching reorder point. Plan procurement of ', ROUND(pd.reorder_point - pd.total_stock_all_locations, 2), ' MT. ')
                WHEN pd.stock_status = 'EXCESS'
                THEN CONCAT('📦 Excess stock - ', ROUND(pd.excess_qty, 2), ' MT above optimal levels. Consider reducing orders. ')
                ELSE '✅ Stock levels normal. '
            END,
            CASE
                WHEN pd.days_of_stock_remaining IS NOT NULL 
                THEN CONCAT('Coverage: ', pd.days_of_stock_remaining, ' days at current consumption rate. ')
                ELSE ''
            END,
            CASE
                WHEN pd.profit_margin_percent IS NOT NULL
                THEN CONCAT('Margin: ', pd.profit_margin_percent, '%. ')
                ELSE ''
            END
        )::TEXT as narrative,
        pd.stock_status::TEXT as status,
        ARRAY_REMOVE(ARRAY[
            CASE WHEN pd.stock_status = 'CRITICAL' THEN CONCAT('URGENT: Order ', ROUND(pd.shortage_qty, 0), ' MT immediately') END,
            CASE WHEN pd.stock_status = 'WARNING' THEN 'Initiate reorder process' END,
            CASE WHEN pd.stock_status = 'EXCESS' THEN 'Suspend new orders until stock normalizes' END,
            CASE WHEN pd.days_of_stock_remaining < 10 THEN 'Monitor daily - low coverage' END
        ], NULL)::TEXT[] as actions
    FROM product_data pd;
END;
$$ LANGUAGE plpgsql;
