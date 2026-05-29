-- Stock Analytics Bootstrap Schema (PostgreSQL)
--
-- This schema matches the currently implemented runtime flow:
-- - stock rows are loaded into inventory_detail
-- - target variance is read from commodities + commodity_daily_configs
-- - alerts and narrative are computed in Python (main.py), not SQL views

-- -----------------------------------------------------------------------
-- Core master table: commodities
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS commodities (
    id                  SERIAL PRIMARY KEY,
    commodity_name      VARCHAR(255) NOT NULL UNIQUE,
    commodity_code      VARCHAR(50),
    category            VARCHAR(100),
    unit_of_measure     VARCHAR(50) DEFAULT 'MT',
    is_active           BOOLEAN DEFAULT TRUE,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_commodities_name ON commodities (commodity_name);

-- -----------------------------------------------------------------------
-- Planning table: commodity_daily_configs
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS commodity_daily_configs (
    id                              SERIAL PRIMARY KEY,
    commodity_id                    INTEGER NOT NULL REFERENCES commodities(id) ON DELETE CASCADE,
    config_date                     DATE NOT NULL,

    cost_price_per_unit             NUMERIC(12, 4),
    market_price_per_unit           NUMERIC(12, 4),
    replacement_cost_per_unit       NUMERIC(12, 4),

    desired_stock_level             DOUBLE PRECISION,
    min_stock_level                 DOUBLE PRECISION,
    max_stock_level                 DOUBLE PRECISION,
    target_inventory_days           DOUBLE PRECISION DEFAULT 30,
    monthly_sales_target            DOUBLE PRECISION,
    target_storage_cap_days         DOUBLE PRECISION,

    estimated_days_to_sale          DOUBLE PRECISION DEFAULT 15,
    cash_realization_rate           DOUBLE PRECISION DEFAULT 0.95,
    expected_gross_margin           DOUBLE PRECISION,
    annual_cost_of_capital_rate     DOUBLE PRECISION DEFAULT 0.08,

    is_finalized                    BOOLEAN DEFAULT FALSE,
    notes                           TEXT,

    created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_commodity_date_config UNIQUE (commodity_id, config_date)
);

CREATE INDEX IF NOT EXISTS idx_cfg_date ON commodity_daily_configs (config_date);
CREATE INDEX IF NOT EXISTS idx_cfg_commodity ON commodity_daily_configs (commodity_id);

-- -----------------------------------------------------------------------
-- Stock fact table: inventory_detail
-- Grain: report_date + vessel + product + terminal + company + port
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inventory_detail (
    id                              SERIAL PRIMARY KEY,

    date                            DATE NOT NULL,
    fd                              VARCHAR(50),
    vessel_date                     DATE,
    vessel_name                     VARCHAR(255),

    product_name                    VARCHAR(255) NOT NULL,
    port_name                       VARCHAR(255),
    company_terminal_name           VARCHAR(255),
    company_name                    VARCHAR(255),

    unsold_qty                      NUMERIC(15, 3),
    sold_qty_pending_lifting        NUMERIC(15, 3),
    physical_stock                  NUMERIC(15, 3),
    otr_qty                         NUMERIC(15, 3),

    purchase_price_USD              NUMERIC(15, 4),
    cif_duty                        NUMERIC(15, 4),
    cost_price_INR                  NUMERIC(15, 4),
    average_selling_price_INR       NUMERIC(15, 4),
    market_price_INR                NUMERIC(10, 4),

    incoming_stock                  NUMERIC(15, 3),
    incoming_stock_date             DATE,

    no_of_days_of_stock             INTEGER,

    created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_inventory_detail_complete_record
        UNIQUE (
            date, fd, vessel_name, vessel_date, product_name, port_name,
            company_terminal_name, company_name,
            unsold_qty, sold_qty_pending_lifting, physical_stock, otr_qty,
            cost_price_INR, average_selling_price_INR, market_price_INR, no_of_days_of_stock
        )
);

CREATE INDEX IF NOT EXISTS idx_inventory_detail_date ON inventory_detail (date);
CREATE INDEX IF NOT EXISTS idx_inventory_detail_fd ON inventory_detail (fd);
CREATE INDEX IF NOT EXISTS idx_inventory_detail_product ON inventory_detail (product_name);
CREATE INDEX IF NOT EXISTS idx_inventory_detail_port ON inventory_detail (port_name);
CREATE INDEX IF NOT EXISTS idx_inventory_detail_company ON inventory_detail (company_name);
CREATE INDEX IF NOT EXISTS idx_inventory_detail_terminal ON inventory_detail (company_terminal_name);
CREATE INDEX IF NOT EXISTS idx_inventory_detail_vessel ON inventory_detail (vessel_name);

-- -----------------------------------------------------------------------
-- Legacy helper table still used by /api/refresh in main.py
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS processed_files (
    id              SERIAL PRIMARY KEY,
    gcs_path        VARCHAR(500) NOT NULL UNIQUE,
    filename        VARCHAR(255) NOT NULL,
    rows_imported   INTEGER,
    processed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_processed_files_path ON processed_files (gcs_path);
