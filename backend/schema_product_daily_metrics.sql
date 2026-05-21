-- Product Daily Metrics Schema
-- Tracks daily product-level performance and planning metrics
-- Created: 2026-05-21

CREATE TABLE IF NOT EXISTS product_daily_metrics (
    id                              SERIAL              PRIMARY KEY,

    -- Identity
    product_name                    VARCHAR(255)        NOT NULL,
    metric_date                     DATE                NOT NULL,

    -- Pricing Metrics (₹/MT or relevant currency)
    market_price                    NUMERIC(15, 4),
    replacement_cost                NUMERIC(15, 4),

    -- Stock Level Targets
    safety_stock_level              NUMERIC(15, 3),
    reorder_stock_level             NUMERIC(15, 3),

    -- Planning Targets
    target_monthly_sales            NUMERIC(15, 3),     -- MT or units per month
    target_storage_cap_days         NUMERIC(10, 2),     -- max days inventory can be stored
    target_inventory_days           NUMERIC(10, 2),     -- optimal inventory holding days
    target_cash_realization_days    NUMERIC(10, 2),     -- days to convert inventory to cash

    -- Audit fields
    created_at                      TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

-- Auto-update updated_at on row modification
CREATE OR REPLACE FUNCTION update_product_daily_metrics_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER product_daily_metrics_updated_at
    BEFORE UPDATE ON product_daily_metrics
    FOR EACH ROW EXECUTE FUNCTION update_product_daily_metrics_timestamp();

-- Indexes for efficient daily product queries
CREATE INDEX IF NOT EXISTS idx_product_daily_metrics_product     ON product_daily_metrics (product_name);
CREATE INDEX IF NOT EXISTS idx_product_daily_metrics_date        ON product_daily_metrics (metric_date);
CREATE INDEX IF NOT EXISTS idx_product_daily_metrics_product_date ON product_daily_metrics (product_name, metric_date DESC);
