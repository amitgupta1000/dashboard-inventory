-- Migration: Create Inventory Management Schema
-- Date: 2026-05-21
-- Description: Creates all tables for multi-company, multi-commodity inventory tracking with financial insights

-- ============================================================================
-- MASTER DATA TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(255) UNIQUE NOT NULL,
    company_code VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_company_code (company_code),
    INDEX idx_is_active (is_active)
);

CREATE TABLE IF NOT EXISTS terminals (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    terminal_name VARCHAR(255) NOT NULL,
    terminal_code VARCHAR(50) NOT NULL,
    port VARCHAR(100),
    location VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_company_terminal (company_id, terminal_code),
    INDEX idx_terminal_code (terminal_code),
    INDEX idx_company_id (company_id)
);

CREATE TABLE IF NOT EXISTS commodities (
    id SERIAL PRIMARY KEY,
    commodity_name VARCHAR(255) UNIQUE NOT NULL,
    commodity_code VARCHAR(50) UNIQUE NOT NULL,
    category VARCHAR(100),
    unit_of_measure VARCHAR(50) DEFAULT 'MT',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_commodity_code (commodity_code),
    INDEX idx_is_active (is_active)
);

CREATE TABLE IF NOT EXISTS commodity_settings (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    commodity_id INTEGER NOT NULL REFERENCES commodities(id) ON DELETE CASCADE,
    
    desired_stock_level DECIMAL(12, 4),
    min_stock_level DECIMAL(12, 4),
    max_stock_level DECIMAL(12, 4),
    
    target_inventory_days DECIMAL(8, 2) DEFAULT 30,
    
    cost_price_per_unit DECIMAL(12, 4),
    replacement_cost_per_unit DECIMAL(12, 4),
    estimated_days_to_sale DECIMAL(8, 2) DEFAULT 15,
    cash_realization_rate DECIMAL(5, 4) DEFAULT 1.0,
    
    expected_gross_margin DECIMAL(5, 4),
    
    is_active BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_company_commodity (company_id, commodity_id),
    INDEX idx_company_id (company_id),
    INDEX idx_commodity_id (commodity_id)
);

-- ============================================================================
-- DAILY INVENTORY DATA TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS inventory_reports (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    report_date DATE NOT NULL,
    
    submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    submitted_by VARCHAR(255),
    file_name VARCHAR(255),
    
    total_records INTEGER DEFAULT 0,
    total_value DECIMAL(15, 2) DEFAULT 0,
    
    is_verified BOOLEAN DEFAULT FALSE,
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_company_report_date (company_id, report_date),
    INDEX idx_report_date (report_date),
    INDEX idx_company_id (company_id)
);

CREATE TABLE IF NOT EXISTS inventory_records (
    id SERIAL PRIMARY KEY,
    
    report_id INTEGER NOT NULL REFERENCES inventory_reports(id) ON DELETE CASCADE,
    terminal_id INTEGER NOT NULL REFERENCES terminals(id) ON DELETE CASCADE,
    commodity_id INTEGER NOT NULL REFERENCES commodities(id) ON DELETE CASCADE,
    
    physical_stock DECIMAL(12, 4) NOT NULL,
    unsold_qty DECIMAL(12, 4),
    sold_qty_pending DECIMAL(12, 4),
    
    num_vessels INTEGER DEFAULT 1,
    earliest_vessel_date DATE,
    latest_vessel_date DATE,
    
    import_price_per_unit DECIMAL(12, 4),
    
    inventory_age_days INTEGER,
    days_of_stock DECIMAL(8, 2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_report_id (report_id),
    INDEX idx_terminal_id (terminal_id),
    INDEX idx_commodity_id (commodity_id),
    INDEX idx_physical_stock (physical_stock)
);

CREATE TABLE IF NOT EXISTS vessels (
    id SERIAL PRIMARY KEY,
    inventory_record_id INTEGER NOT NULL REFERENCES inventory_records(id) ON DELETE CASCADE,
    
    vessel_name VARCHAR(255) NOT NULL,
    vessel_date DATE NOT NULL,
    
    unsold_qty DECIMAL(12, 4),
    sold_qty DECIMAL(12, 4),
    physical_stock DECIMAL(12, 4),
    
    other_qty DECIMAL(12, 4),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_inventory_record_id (inventory_record_id),
    INDEX idx_vessel_name (vessel_name)
);

-- ============================================================================
-- MARKET PRICING & FINANCIAL DATA
-- ============================================================================

CREATE TABLE IF NOT EXISTS price_history (
    id SERIAL PRIMARY KEY,
    commodity_id INTEGER NOT NULL REFERENCES commodities(id) ON DELETE CASCADE,
    price_date DATE NOT NULL,
    
    cost_price DECIMAL(12, 4) NOT NULL,
    market_price DECIMAL(12, 4) NOT NULL,
    replacement_cost DECIMAL(12, 4) NOT NULL,
    
    source VARCHAR(100),
    is_verified BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_commodity_date (commodity_id, price_date),
    INDEX idx_price_date (price_date),
    INDEX idx_commodity_id (commodity_id)
);

-- ============================================================================
-- INSIGHTS & ANALYSIS TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS stock_level_insights (
    id SERIAL PRIMARY KEY,
    report_id INTEGER NOT NULL REFERENCES inventory_reports(id) ON DELETE CASCADE,
    inventory_record_id INTEGER NOT NULL REFERENCES inventory_records(id) ON DELETE CASCADE,
    
    current_stock DECIMAL(12, 4),
    desired_stock DECIMAL(12, 4),
    stock_variance DECIMAL(12, 4),
    variance_pct DECIMAL(7, 2),
    
    alert_level VARCHAR(50),
    alert_message TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_report_id (report_id),
    INDEX idx_alert_level (alert_level),
    INDEX idx_created_at (created_at)
);

CREATE TABLE IF NOT EXISTS mark_to_market_insights (
    id SERIAL PRIMARY KEY,
    report_id INTEGER NOT NULL REFERENCES inventory_reports(id) ON DELETE CASCADE,
    inventory_record_id INTEGER NOT NULL REFERENCES inventory_records(id) ON DELETE CASCADE,
    
    quantity DECIMAL(12, 4),
    
    value_at_cost DECIMAL(15, 4),
    value_at_market DECIMAL(15, 4),
    value_at_replacement DECIMAL(15, 4),
    
    gain_at_market DECIMAL(15, 4),
    gain_pct_market DECIMAL(7, 2),
    
    loss_vs_replacement DECIMAL(15, 4),
    replacement_impact DECIMAL(7, 2),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_report_id (report_id),
    INDEX idx_created_at (created_at)
);

CREATE TABLE IF NOT EXISTS working_capital_insights (
    id SERIAL PRIMARY KEY,
    report_id INTEGER NOT NULL REFERENCES inventory_reports(id) ON DELETE CASCADE,
    inventory_record_id INTEGER NOT NULL REFERENCES inventory_records(id) ON DELETE CASCADE,
    
    current_inventory_days DECIMAL(8, 2),
    target_inventory_days DECIMAL(8, 2),
    excess_days DECIMAL(8, 2),
    
    inventory_value DECIMAL(15, 4),
    excess_capital_tied_up DECIMAL(15, 4),
    
    annual_cost_of_capital_rate DECIMAL(5, 4) DEFAULT 0.08,
    annual_opportunity_cost DECIMAL(15, 4),
    daily_opportunity_cost DECIMAL(10, 4),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_report_id (report_id),
    INDEX idx_created_at (created_at)
);

CREATE TABLE IF NOT EXISTS gross_profit_insights (
    id SERIAL PRIMARY KEY,
    report_id INTEGER NOT NULL REFERENCES inventory_reports(id) ON DELETE CASCADE,
    inventory_record_id INTEGER NOT NULL REFERENCES inventory_records(id) ON DELETE CASCADE,
    
    quantity DECIMAL(12, 4),
    cost_per_unit DECIMAL(12, 4),
    market_price_per_unit DECIMAL(12, 4),
    
    estimated_days_to_sale DECIMAL(8, 2),
    cash_realization_rate DECIMAL(5, 4) DEFAULT 1.0,
    
    total_cogs DECIMAL(15, 4),
    expected_revenue DECIMAL(15, 4),
    estimated_gross_profit DECIMAL(15, 4),
    gross_profit_margin_pct DECIMAL(7, 2),
    
    estimated_sale_date DATE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_report_id (report_id),
    INDEX idx_created_at (created_at)
);

-- ============================================================================
-- SUMMARY & AGGREGATION TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS summary_by_company (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    report_date DATE NOT NULL,
    
    total_inventory_value DECIMAL(15, 4),
    total_quantity_by_unit DECIMAL(12, 4),
    num_commodities INTEGER,
    num_terminals INTEGER,
    
    critical_alerts INTEGER DEFAULT 0,
    warning_alerts INTEGER DEFAULT 0,
    
    total_unrealized_gain DECIMAL(15, 4),
    total_opportunity_cost DECIMAL(15, 4),
    total_estimated_gross_profit DECIMAL(15, 4),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_company_date (company_id, report_date),
    INDEX idx_report_date (report_date)
);

CREATE TABLE IF NOT EXISTS summary_by_commodity (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    commodity_id INTEGER NOT NULL REFERENCES commodities(id) ON DELETE CASCADE,
    report_date DATE NOT NULL,
    
    total_quantity DECIMAL(12, 4),
    total_inventory_value DECIMAL(15, 4),
    num_terminals INTEGER,
    
    stock_alert_level VARCHAR(50),
    avg_inventory_days DECIMAL(8, 2),
    
    total_unrealized_gain DECIMAL(15, 4),
    total_opportunity_cost DECIMAL(15, 4),
    total_estimated_gross_profit DECIMAL(15, 4),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_company_commodity_date (company_id, commodity_id, report_date),
    INDEX idx_report_date (report_date),
    INDEX idx_company_id (company_id)
);

-- ============================================================================
-- AUDIT & TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS data_import_logs (
    id SERIAL PRIMARY KEY,
    import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_name VARCHAR(255),
    file_size INTEGER,
    
    num_records_imported INTEGER,
    num_records_skipped INTEGER,
    import_status VARCHAR(50),
    
    error_messages TEXT,
    imported_by VARCHAR(255),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_import_date (import_date)
);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Total inventory by commodity
CREATE OR REPLACE VIEW v_inventory_by_commodity AS
SELECT
    c.id,
    c.commodity_name,
    c.commodity_code,
    ir.report_id,
    SUM(ir.physical_stock) as total_quantity,
    SUM(ir.physical_stock * COALESCE(ph.cost_price, ir.import_price_per_unit)) as total_value_at_cost,
    SUM(ir.physical_stock * COALESCE(ph.market_price, ir.import_price_per_unit)) as total_value_at_market,
    COUNT(DISTINCT ir.terminal_id) as num_locations
FROM inventory_records ir
JOIN commodities c ON ir.commodity_id = c.id
LEFT JOIN price_history ph ON ir.commodity_id = ph.commodity_id
    AND ph.price_date = (SELECT MAX(price_date) FROM price_history WHERE commodity_id = ir.commodity_id)
GROUP BY c.id, c.commodity_name, c.commodity_code, ir.report_id;

-- Stock alerts summary
CREATE OR REPLACE VIEW v_stock_alerts_summary AS
SELECT
    sli.alert_level,
    COUNT(*) as count,
    SUM(CASE WHEN sli.alert_level = 'CRITICAL' THEN 1 ELSE 0 END) as critical_count,
    SUM(CASE WHEN sli.alert_level = 'WARNING' THEN 1 ELSE 0 END) as warning_count
FROM stock_level_insights sli
WHERE sli.created_at = (SELECT MAX(created_at) FROM stock_level_insights)
GROUP BY sli.alert_level;

-- Working capital summary by company
CREATE OR REPLACE VIEW v_working_capital_by_company AS
SELECT
    c.id,
    c.company_name,
    ir.report_date,
    SUM(wci.excess_days * wci.daily_opportunity_cost) as total_opportunity_cost,
    SUM(wci.daily_opportunity_cost * 365) as annual_opportunity_cost,
    COUNT(DISTINCT ir.terminal_id) as num_terminals_affected
FROM working_capital_insights wci
JOIN inventory_records ir ON wci.inventory_record_id = ir.id
JOIN inventory_reports irpt ON ir.report_id = irpt.id
JOIN companies c ON irpt.company_id = c.id
WHERE ir.report_id = (SELECT MAX(id) FROM inventory_reports)
GROUP BY c.id, c.company_name, ir.report_date;
