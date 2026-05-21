-- Inventory Detail Schema Migration
-- Created: 2026-05-21
-- Based on incoming vessel and inventory tracking data

CREATE TABLE IF NOT EXISTS inventory_detail (
    id                          SERIAL              PRIMARY KEY,

    -- Import & Vessel Information
    date_of_import              DATE                NOT NULL,
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
