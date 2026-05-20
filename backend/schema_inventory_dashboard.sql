-- Inventory Dashboard Schema for Cloud SQL PostgreSQL
-- Based on the vessel arrival and inventory tracking spreadsheet
-- Run this against your Cloud SQL instance to create the schema.

CREATE TABLE IF NOT EXISTS inventory_dashboard (
    id                      SERIAL          PRIMARY KEY,

    -- Vessel & Identity
    vessel_arrival_date     DATE,
    company_name            VARCHAR(255),
    port_name               VARCHAR(255),
    vessel_name             VARCHAR(255),
    product_name            VARCHAR(255)    NOT NULL,

    -- Stock days & quantities
    no_of_days_of_stock     INTEGER,
    bl_qty                  NUMERIC(15, 3),          -- Bill of Lading quantity
    otr_qty                 NUMERIC(15, 3),          -- Over The Road quantity
    physical_stock_on_port  NUMERIC(15, 3),
    total_unsold_qty        NUMERIC(15, 3),
    total_sold_qty          NUMERIC(15, 3),

    -- Pricing (per MT)
    avg_per_mt_price_inr    NUMERIC(15, 4),          -- All inclusive INR price per MT
    import_price_usd_mt     NUMERIC(15, 4),          -- Import price in USD per MT
    exchange_rate           NUMERIC(10, 4),
    
    -- Values
    physical_qty_value      NUMERIC(18, 2),          -- Total value of physical quantity
    
    -- Incoming & Market
    incoming_vessel_qty     NUMERIC(15, 3),

    -- Computed fields
    calculated_import_inr   NUMERIC(15, 4) GENERATED ALWAYS AS (
                                CASE 
                                    WHEN import_price_usd_mt IS NOT NULL 
                                         AND exchange_rate IS NOT NULL
                                    THEN import_price_usd_mt * exchange_rate
                                    ELSE NULL
                                END
                            ) STORED,

    -- Status indicator based on stock levels
    stock_status            VARCHAR(20) GENERATED ALWAYS AS (
                                CASE
                                    WHEN no_of_days_of_stock IS NULL THEN 'UNKNOWN'
                                    WHEN no_of_days_of_stock < 7 THEN 'CRITICAL'
                                    WHEN no_of_days_of_stock < 15 THEN 'LOW'
                                    WHEN no_of_days_of_stock < 30 THEN 'MODERATE'
                                    ELSE 'ADEQUATE'
                                END
                            ) STORED,

    -- Audit fields
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Auto-update updated_at on row modification
CREATE OR REPLACE FUNCTION update_inventory_dashboard_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER inventory_dashboard_updated_at
    BEFORE UPDATE ON inventory_dashboard
    FOR EACH ROW EXECUTE FUNCTION update_inventory_dashboard_timestamp();

-- Indexes for dashboard queries
CREATE INDEX IF NOT EXISTS idx_inventory_dashboard_company     ON inventory_dashboard (company_name);
CREATE INDEX IF NOT EXISTS idx_inventory_dashboard_port        ON inventory_dashboard (port_name);
CREATE INDEX IF NOT EXISTS idx_inventory_dashboard_product     ON inventory_dashboard (product_name);
CREATE INDEX IF NOT EXISTS idx_inventory_dashboard_vessel      ON inventory_dashboard (vessel_name);
CREATE INDEX IF NOT EXISTS idx_inventory_dashboard_arrival     ON inventory_dashboard (vessel_arrival_date);
CREATE INDEX IF NOT EXISTS idx_inventory_dashboard_status      ON inventory_dashboard (stock_status);

-- -----------------------------------------------------------------------
-- View: Current Inventory Summary by Product
-- -----------------------------------------------------------------------
CREATE OR REPLACE VIEW v_inventory_summary AS
SELECT 
    product_name,
    company_name,
    port_name,
    SUM(physical_stock_on_port) as total_physical_stock,
    SUM(total_sold_qty) as total_sold,
    SUM(total_unsold_qty) as total_unsold,
    SUM(incoming_vessel_qty) as total_incoming,
    SUM(physical_qty_value) as total_value,
    AVG(avg_per_mt_price_inr) as avg_price_inr,
    MIN(no_of_days_of_stock) as min_days_of_stock,
    MAX(vessel_arrival_date) as latest_vessel_arrival
FROM inventory_dashboard
GROUP BY product_name, company_name, port_name
ORDER BY total_value DESC NULLS LAST;

-- -----------------------------------------------------------------------
-- View: Critical Stock Alerts
-- -----------------------------------------------------------------------
CREATE OR REPLACE VIEW v_critical_stock AS
SELECT 
    id,
    company_name,
    port_name,
    product_name,
    vessel_name,
    vessel_arrival_date,
    no_of_days_of_stock,
    physical_stock_on_port,
    total_unsold_qty,
    incoming_vessel_qty,
    stock_status,
    updated_at
FROM inventory_dashboard
WHERE stock_status IN ('CRITICAL', 'LOW')
ORDER BY no_of_days_of_stock ASC NULLS LAST, updated_at DESC;

-- -----------------------------------------------------------------------
-- Tracks which GCS files have already been imported
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS processed_files (
    id              SERIAL       PRIMARY KEY,
    gcs_path        VARCHAR(500) NOT NULL UNIQUE,
    filename        VARCHAR(255) NOT NULL,
    file_hash       VARCHAR(64),                    -- SHA256 hash for duplicate detection
    rows_imported   INTEGER,
    rows_updated    INTEGER      DEFAULT 0,
    processed_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_processed_files_path ON processed_files (gcs_path);
CREATE INDEX IF NOT EXISTS idx_processed_files_hash ON processed_files (file_hash);

-- -----------------------------------------------------------------------
-- Optional: Activity log for tracking changes
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inventory_activity_log (
    id              SERIAL       PRIMARY KEY,
    inventory_id    INTEGER      REFERENCES inventory_dashboard(id) ON DELETE SET NULL,
    action          VARCHAR(50)  NOT NULL,  -- INSERT, UPDATE, DELETE
    field_changed   VARCHAR(100),
    old_value       TEXT,
    new_value       TEXT,
    changed_by      VARCHAR(255),
    changed_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activity_log_inventory ON inventory_activity_log (inventory_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_timestamp ON inventory_activity_log (changed_at);
