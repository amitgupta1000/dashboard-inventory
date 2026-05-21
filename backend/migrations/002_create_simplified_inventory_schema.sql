-- Migration: Create Simplified Inventory Management Schema
-- Date: 2026-05-21
-- Description: Stores daily inventory with cost price; other fields auto-populated from previous day

-- ============================================================================
-- MASTER DATA TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS commodities (
    id SERIAL PRIMARY KEY,
    commodity_name VARCHAR(255) UNIQUE NOT NULL,
    commodity_code VARCHAR(50),
    category VARCHAR(100),
    unit_of_measure VARCHAR(50) DEFAULT 'MT',
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_active (is_active),
    INDEX idx_commodity_name (commodity_name)
);

CREATE TABLE IF NOT EXISTS terminals (
    id SERIAL PRIMARY KEY,
    terminal_name VARCHAR(255) NOT NULL,
    terminal_code VARCHAR(50),
    port VARCHAR(100),
    region VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_terminal_port (terminal_name, port),
    INDEX idx_terminal_name (terminal_name)
);

-- ============================================================================
-- CONFIGURATION - AUTO-POPULATED FROM PREVIOUS DAY
-- ============================================================================

CREATE TABLE IF NOT EXISTS commodity_daily_configs (
    id SERIAL PRIMARY KEY,
    commodity_id INTEGER NOT NULL REFERENCES commodities(id) ON DELETE CASCADE,
    config_date DATE NOT NULL,
    
    -- Financial Parameters (auto-populated from previous day, then editable)
    cost_price_per_unit DECIMAL(12, 4),
    market_price_per_unit DECIMAL(12, 4),
    replacement_cost_per_unit DECIMAL(12, 4),
    
    -- Inventory Targets
    desired_stock_level DECIMAL(12, 4),
    min_stock_level DECIMAL(12, 4),
    max_stock_level DECIMAL(12, 4),
    target_inventory_days DECIMAL(8, 2) DEFAULT 30,
    
    -- Sales Assumptions
    estimated_days_to_sale DECIMAL(8, 2) DEFAULT 15,
    cash_realization_rate DECIMAL(5, 4) DEFAULT 0.95,
    expected_gross_margin DECIMAL(5, 4),
    
    -- Working Capital
    annual_cost_of_capital_rate DECIMAL(5, 4) DEFAULT 0.08,
    
    -- Metadata
    is_finalized BOOLEAN DEFAULT FALSE,
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uq_commodity_date_config (commodity_id, config_date),
    INDEX idx_config_date (config_date),
    INDEX idx_commodity_id (commodity_id)
);

-- ============================================================================
-- DAILY INVENTORY DATA
-- ============================================================================

CREATE TABLE IF NOT EXISTS daily_inventory_reports (
    id SERIAL PRIMARY KEY,
    report_date DATE UNIQUE NOT NULL,
    
    file_name VARCHAR(255),
    submitted_by VARCHAR(255),
    
    total_records INTEGER DEFAULT 0,
    total_value_at_cost DECIMAL(15, 2),
    
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_report_date (report_date)
);

CREATE TABLE IF NOT EXISTS daily_inventory_records (
    id SERIAL PRIMARY KEY,
    
    -- Relationships
    report_id INTEGER NOT NULL REFERENCES daily_inventory_reports(id) ON DELETE CASCADE,
    commodity_id INTEGER NOT NULL REFERENCES commodities(id) ON DELETE CASCADE,
    terminal_id INTEGER NOT NULL REFERENCES terminals(id) ON DELETE CASCADE,
    
    record_date DATE NOT NULL,
    
    -- Quantities
    physical_stock DECIMAL(12, 4) NOT NULL,
    unsold_qty DECIMAL(12, 4),
    sold_qty_pending DECIMAL(12, 4),
    
    -- Vessel Information
    num_vessels INTEGER DEFAULT 1,
    earliest_vessel_date DATE,
    latest_vessel_date DATE,
    inventory_age_days INTEGER,
    
    -- Pricing
    cost_price_per_unit DECIMAL(12, 4),
    market_price_per_unit DECIMAL(12, 4),
    
    -- Calculated Fields
    value_at_cost DECIMAL(15, 4),
    value_at_market DECIMAL(15, 4),
    days_of_stock DECIMAL(8, 2),
    
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uq_report_commodity_terminal (report_id, commodity_id, terminal_id),
    INDEX idx_report_id (report_id),
    INDEX idx_commodity_id (commodity_id),
    INDEX idx_terminal_id (terminal_id),
    INDEX idx_record_date (record_date)
);

-- ============================================================================
-- INSIGHTS PLACEHOLDER
-- ============================================================================

CREATE TABLE IF NOT EXISTS insight_snapshots (
    id SERIAL PRIMARY KEY,
    record_id INTEGER REFERENCES daily_inventory_records(id) ON DELETE CASCADE,
    
    snapshot_date DATE,
    insight_type VARCHAR(50),  -- "STOCK_LEVEL", "MARK_TO_MARKET", "WORKING_CAPITAL", "GROSS_PROFIT"
    
    insight_data LONGTEXT,
    alert_level VARCHAR(50),
    alert_message TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_snapshot_date (snapshot_date),
    INDEX idx_insight_type (insight_type)
);

-- ============================================================================
-- AUDIT TRAIL
-- ============================================================================

CREATE TABLE IF NOT EXISTS data_import_logs (
    id SERIAL PRIMARY KEY,
    import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_name VARCHAR(255),
    file_size INTEGER,
    
    num_records_imported INTEGER DEFAULT 0,
    num_records_skipped INTEGER DEFAULT 0,
    import_status VARCHAR(50),
    error_messages TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_import_date (import_date)
);

-- ============================================================================
-- SEED DATA: COMMODITIES (extracted from 12-5-26.xlsx)
-- ============================================================================

INSERT INTO commodities (commodity_name, unit_of_measure, is_active)
VALUES
    ('2-ETHYLHEXANOL', 'MT', TRUE),
    ('ACETIC ACID', 'MT', TRUE),
    ('BUTYL ACETATE', 'MT', TRUE),
    ('BUTYL DI  GLYCOL', 'MT', TRUE),
    ('BUTYL GLYCOL', 'MT', TRUE),
    ('C-9', 'MT', TRUE),
    ('CYCLOHEXANE', 'MT', TRUE),
    ('CYCLOHEXANONE', 'MT', TRUE),
    ('DEG', 'MT', TRUE),
    ('EDC', 'MT', TRUE),
    ('HEXANE', 'MT', TRUE),
    ('IBA', 'MT', TRUE),
    ('IBAC', 'MT', TRUE),
    ('IPA', 'MT', TRUE),
    ('MEG', 'MT', TRUE),
    ('METHANOL', 'MT', TRUE),
    ('MIX XYLENE', 'MT', TRUE),
    ('MIX XYLENE ISOMER GR', 'MT', TRUE),
    ('MIXED HEPTANE', 'MT', TRUE),
    ('MMA', 'MT', TRUE),
    ('N-PROPANOL', 'MT', TRUE),
    ('NORMAL BUTANOL', 'MT', TRUE),
    ('ORTHO XYLENE', 'MT', TRUE),
    ('PHENOL-M', 'MT', TRUE),
    ('POLYLOL 0434', 'MT', TRUE),
    ('POLYLOL 0656', 'MT', TRUE),
    ('POLYOL 1127', 'MT', TRUE),
    ('PROPIONIC ACID', 'MT', TRUE),
    ('PROPYLENE GLYCOL', 'MT', TRUE),
    ('STYRENE MONOMER', 'MT', TRUE),
    ('TOLUENE', 'MT', TRUE)
ON DUPLICATE KEY UPDATE is_active = TRUE;

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Latest inventory by commodity and terminal
CREATE OR REPLACE VIEW v_latest_inventory AS
SELECT
    c.commodity_name,
    t.terminal_name,
    t.port,
    dir.record_date,
    dir.physical_stock,
    dir.unsold_qty,
    dir.sold_qty_pending,
    dir.cost_price_per_unit,
    dir.market_price_per_unit,
    dir.value_at_cost,
    dir.value_at_market,
    dir.inventory_age_days
FROM daily_inventory_records dir
JOIN commodities c ON dir.commodity_id = c.id
JOIN terminals t ON dir.terminal_id = t.id
WHERE dir.record_date = (SELECT MAX(record_date) FROM daily_inventory_records);

-- Daily configuration by commodity
CREATE OR REPLACE VIEW v_commodity_configs_latest AS
SELECT
    c.commodity_name,
    cc.config_date,
    cc.cost_price_per_unit,
    cc.market_price_per_unit,
    cc.replacement_cost_per_unit,
    cc.desired_stock_level,
    cc.min_stock_level,
    cc.max_stock_level,
    cc.target_inventory_days,
    cc.estimated_days_to_sale,
    cc.cash_realization_rate,
    cc.expected_gross_margin,
    cc.is_finalized
FROM commodity_daily_configs cc
JOIN commodities c ON cc.commodity_id = c.id
WHERE cc.config_date = (SELECT MAX(config_date) FROM commodity_daily_configs);

-- Total inventory value by commodity
CREATE OR REPLACE VIEW v_inventory_summary AS
SELECT
    c.commodity_name,
    COUNT(DISTINCT dir.terminal_id) as num_locations,
    SUM(dir.physical_stock) as total_qty,
    SUM(dir.value_at_cost) as total_value_at_cost,
    SUM(dir.value_at_market) as total_value_at_market,
    MAX(dir.inventory_age_days) as max_age_days,
    dir.record_date
FROM daily_inventory_records dir
JOIN commodities c ON dir.commodity_id = c.id
WHERE dir.record_date = (SELECT MAX(record_date) FROM daily_inventory_records)
GROUP BY c.id, c.commodity_name, dir.record_date;
