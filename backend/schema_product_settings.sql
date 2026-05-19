-- Product Settings Table for Cloud SQL PostgreSQL
-- Stores configurable parameters per product/item
-- These settings control inventory thresholds and planning parameters

CREATE TABLE IF NOT EXISTS product_settings (
    id                      SERIAL          PRIMARY KEY,
    
    -- Product identifier
    item                    VARCHAR(255)    NOT NULL UNIQUE,
    
    -- Stock thresholds
    safety_stock            NUMERIC(15, 3),          -- Stock below this → CRITICAL status
    reorder_point           NUMERIC(15, 3),          -- Stock below this → WARNING status
    
    -- Time constraints
    max_storage_days        INTEGER,                 -- Max storage days before aging alert
    max_inventory_days      INTEGER,                 -- Inventory cycle window for projected sales
    
    -- Sales planning
    monthly_target_volume   NUMERIC(15, 3),          -- Expected monthly sales (MT)
    
    -- Metadata
    is_active               BOOLEAN         NOT NULL DEFAULT TRUE,
    notes                   TEXT,
    
    -- Audit fields
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    created_by              VARCHAR(255),
    updated_by              VARCHAR(255)
);

-- Auto-update updated_at on row modification
CREATE OR REPLACE FUNCTION update_product_settings_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER product_settings_updated_at
    BEFORE UPDATE ON product_settings
    FOR EACH ROW EXECUTE FUNCTION update_product_settings_timestamp();

-- Indexes for quick lookups
CREATE INDEX IF NOT EXISTS idx_product_settings_item ON product_settings (item);
CREATE INDEX IF NOT EXISTS idx_product_settings_active ON product_settings (is_active);

-- -----------------------------------------------------------------------
-- View: Active Product Settings with computed daily targets
-- -----------------------------------------------------------------------
CREATE OR REPLACE VIEW v_active_product_settings AS
SELECT 
    id,
    item,
    safety_stock,
    reorder_point,
    max_storage_days,
    max_inventory_days,
    monthly_target_volume,
    CASE 
        WHEN monthly_target_volume IS NOT NULL 
        THEN ROUND(monthly_target_volume / 30.0, 3)
        ELSE NULL
    END as daily_target_volume,
    is_active,
    notes,
    updated_at
FROM product_settings
WHERE is_active = TRUE
ORDER BY item;

-- Insert default settings for common products (based on the image)
INSERT INTO product_settings (item, safety_stock, reorder_point, max_storage_days, max_inventory_days, monthly_target_volume) VALUES
    ('Toluene', 2000, 3500, 90, 30, 2500),
    ('Toluene', 2000, 3500, 90, 30, 2500),
    ('Toluene', 500, 1000, 60, 30, 800),
    ('Mix Xylene', 1500, 2500, 90, 30, 1500),
    ('Mix Xylene', 2500, 4000, 90, 30, 2500),
    ('Acid', 600, 1200, 120, 30, 1000),
    ('Methanol', 1000, 2000, 90, 30, 1200),
    ('Cyclo', 200, 400, 60, 30, 300),
    ('Styrene', 400, 800, 30, 30, 800),
    ('BG', 300, 600, 90, 30, 400)
ON CONFLICT (item) DO NOTHING;
