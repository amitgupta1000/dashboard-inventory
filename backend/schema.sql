-- Inventory table for Cloud SQL PostgreSQL
-- Run this once against your Cloud SQL instance to create the schema.

CREATE TABLE IF NOT EXISTS inventory (
    id               SERIAL          PRIMARY KEY,

    -- Identity
    record_date      DATE,
    item             VARCHAR(255)    NOT NULL,
    port             VARCHAR(255),
    company          VARCHAR(255),
    unit             VARCHAR(10),

    -- Stock quantities
    physical_stock   NUMERIC(15, 3),
    ready_unsold     NUMERIC(15, 3),          -- can be negative
    safety_stock     NUMERIC(15, 3),
    reorder_point    NUMERIC(15, 3),

    -- Thresholds & planning
    storage_cap_days NUMERIC(10, 2),          -- max storage days before aging alert
    cycle_days       NUMERIC(10, 2),          -- inventory cycle window for projected sales
    monthly_volume   NUMERIC(15, 3),          -- expected monthly sales (MT)

    -- Pricing (₹/MT)
    market_price     NUMERIC(15, 4),
    selling_price    NUMERIC(15, 4),
    cif_duty         NUMERIC(15, 4),          -- landed cost
    purchase_price   NUMERIC(15, 4),

    -- Movement
    pending_lifting  NUMERIC(15, 3),          -- MT to dispatch
    port_stock       NUMERIC(15, 3),          -- MT in port godown
    incoming_qty     NUMERIC(15, 3),          -- MT expected to arrive
    arrival_date     VARCHAR(100),            -- free-text window, e.g. "MID MAY"

    -- Auto-computed status (do not set manually)
    status           VARCHAR(10) GENERATED ALWAYS AS (
                         CASE
                             WHEN physical_stock IS NULL THEN 'UNKNOWN'
                             WHEN physical_stock < safety_stock  THEN 'CRITICAL'
                             WHEN physical_stock < reorder_point THEN 'WARNING'
                             ELSE 'OK'
                         END
                     ) STORED,

    created_at       TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Auto-update updated_at on row modification
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER inventory_updated_at
    BEFORE UPDATE ON inventory
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Indexes for common dashboard queries
CREATE INDEX IF NOT EXISTS idx_inventory_item        ON inventory (item);
CREATE INDEX IF NOT EXISTS idx_inventory_company     ON inventory (company);
CREATE INDEX IF NOT EXISTS idx_inventory_port        ON inventory (port);
CREATE INDEX IF NOT EXISTS idx_inventory_status      ON inventory (status);
CREATE INDEX IF NOT EXISTS idx_inventory_record_date ON inventory (record_date);

-- -----------------------------------------------------------------------
-- Tracks which GCS files have already been imported to prevent re-processing
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS processed_files (
    id            SERIAL       PRIMARY KEY,
    gcs_path      VARCHAR(500) NOT NULL UNIQUE,   -- e.g. uploads/2026-05-19_stock.xlsx
    filename      VARCHAR(255) NOT NULL,
    rows_imported INTEGER,
    processed_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
