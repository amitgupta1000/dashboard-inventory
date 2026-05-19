-- Inventory table for Cloud SQL PostgreSQL
-- Run this once against your Cloud SQL instance to create the schema.

CREATE TABLE IF NOT EXISTS inventory (
    id                    SERIAL PRIMARY KEY,
    company_name          VARCHAR(255)   NOT NULL,
    port_name             VARCHAR(255),
    product_name          VARCHAR(255)   NOT NULL,
    physical_stock        NUMERIC(15, 2),
    total_sold_qty        NUMERIC(15, 2),
    total_unsold_qty      NUMERIC(15, 2),
    incoming_vessel_qty   NUMERIC(15, 2),
    avg_import_price_usd  NUMERIC(15, 4),
    avg_price_inr         NUMERIC(15, 4),
    current_market_price  NUMERIC(15, 4),
    replacement_cost      NUMERIC(15, 4),
    stock_value           NUMERIC(20, 2),
    created_at            TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ    NOT NULL DEFAULT NOW()
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

-- Useful indexes for dashboard queries
CREATE INDEX IF NOT EXISTS idx_inventory_company   ON inventory (company_name);
CREATE INDEX IF NOT EXISTS idx_inventory_product   ON inventory (product_name);
CREATE INDEX IF NOT EXISTS idx_inventory_port      ON inventory (port_name);
