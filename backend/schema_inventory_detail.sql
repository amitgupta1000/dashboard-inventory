-- Inventory Detail Schema for Cloud SQL PostgreSQL
-- Based on incoming vessel and inventory tracking data
-- Columns: DATE, VESSEL DATE, VESSEL NAME, PRODUCT NAME, PORT, UNSOLD QTY, 
--          SOLD QTY / PENDING LIFTING, PHYSICAL STOCK, OTR QTY, COMPANY TERMINAL NAME, 
--          NO OF DAYS OF STOCK

CREATE TABLE IF NOT EXISTS inventory_detail (
    id                          SERIAL              PRIMARY KEY,

    -- Import & Vessel Information
    date                        DATE                NOT NULL,
    vessel_date                 DATE,
    vessel_name                 VARCHAR(255),

    -- Product & Location
    product_name                VARCHAR(255)        NOT NULL,
    port_name                   VARCHAR(255),
    company_terminal_name       VARCHAR(255),

    -- Stock Quantities (in metric tons or relevant unit)
    unsold_qty                  NUMERIC(15, 3),
    sold_qty_pending_lifting    NUMERIC(15, 3),
    physical_stock              NUMERIC(15, 3),
    otr_qty                     NUMERIC(15, 3),     -- Over The Road Quantity

    -- Pricing & Cost Information
    purchase_price_USD          NUMERIC(15, 4),
    cif_duty                    NUMERIC(15, 4),     -- CIF + Duty cost
    cost_price_INR              NUMERIC(15, 4),
    average_selling_price_INR   NUMERIC(15, 4),
    exchange_rate               NUMERIC(10, 4),     -- USD to INR exchange rate

    -- Incoming Stock
    incoming_stock              NUMERIC(15, 3),     -- Incoming stock (MT)
    incoming_stock_date         DATE,               -- Expected arrival date

    -- Metrics
    no_of_days_of_stock         INTEGER,

    -- Audit fields
    created_at                  TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

-- Auto-update updated_at on row modification
CREATE OR REPLACE FUNCTION update_inventory_detail_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER inventory_detail_updated_at
    BEFORE UPDATE ON inventory_detail
    FOR EACH ROW EXECUTE FUNCTION update_inventory_detail_timestamp();

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_inventory_detail_product      ON inventory_detail (product_name);
CREATE INDEX IF NOT EXISTS idx_inventory_detail_vessel       ON inventory_detail (vessel_name);
CREATE INDEX IF NOT EXISTS idx_inventory_detail_terminal     ON inventory_detail (company_terminal_name);
CREATE INDEX IF NOT EXISTS idx_inventory_detail_date         ON inventory_detail (date_of_import);
CREATE INDEX IF NOT EXISTS idx_inventory_detail_port         ON inventory_detail (port_name);
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
