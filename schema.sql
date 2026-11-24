-- Clean up existing tables if re-running script
DROP TABLE IF EXISTS audit_log CASCADE;
DROP TABLE IF EXISTS purchase_orders CASCADE;
DROP TABLE IF EXISTS agent_registry CASCADE;
DROP TABLE IF EXISTS inventory CASCADE;
DROP TABLE IF EXISTS transportation_providers CASCADE;

-- ------------------------------------------
-- 1. INVENTORY TABLE
-- Single source of truth for the factory's raw material stock.
-- Modified: Added MCDM Phase 1 Hard Constraints.
-- ------------------------------------------
CREATE TABLE inventory (
    item_id SERIAL PRIMARY KEY,
    material_name VARCHAR(100) NOT NULL UNIQUE,
    current_stock_tons DECIMAL(10,2) NOT NULL CHECK (current_stock_tons >= 0),
    safety_stock_tons DECIMAL(10,2) NOT NULL CHECK (safety_stock_tons >= 0),
    reorder_point_tons DECIMAL(10,2) NOT NULL CHECK (reorder_point_tons >= 0),
    average_daily_consumption DECIMAL(10,2) NOT NULL CHECK (average_daily_consumption > 0),
    -- Hard constraints for Phase 1 MCDM evaluation:
    max_lead_time_days INT NOT NULL DEFAULT 7,
    max_budget_per_ton DECIMAL(10,2) NOT NULL
);

-- ------------------------------------------
-- 2. AGENT REGISTRY TABLE
-- Identity management store utilizing plaintext authentication tokens.
-- ------------------------------------------
CREATE TABLE agent_registry (
    agent_id VARCHAR(50) PRIMARY KEY,
    auth_token VARCHAR(255) NOT NULL,
    assigned_role VARCHAR(50) NOT NULL,
    max_per_transaction_budget DECIMAL(12,2) NOT NULL CHECK (max_per_transaction_budget >= 0),
    account_status BOOLEAN DEFAULT TRUE
);

-- ------------------------------------------
-- 3. PURCHASE ORDERS TABLE
-- Write-restricted ledger for approved corporate spend.
-- ------------------------------------------
CREATE TABLE purchase_orders (
    po_id SERIAL PRIMARY KEY,
    agent_id VARCHAR(50) NOT NULL REFERENCES agent_registry(agent_id),
    vendor_name VARCHAR(100) NOT NULL,
    total_tonnage DECIMAL(10,2) NOT NULL CHECK (total_tonnage > 0),
    negotiated_unit_price DECIMAL(10,2) NOT NULL CHECK (negotiated_unit_price > 0),
    total_landed_cost DECIMAL(12,2) NOT NULL CHECK (total_landed_cost > 0),
    authorization_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------
-- 4. AUDIT LOG TABLE
-- Append-only table capturing blocked security violations.
-- Note: agent_id purposefully unconstrained to allow logging of completely fake IDs.
-- ------------------------------------------
CREATE TABLE audit_log (
    event_id SERIAL PRIMARY KEY,
    agent_id VARCHAR(50),
    step_failed VARCHAR(100) NOT NULL,
    error_message TEXT NOT NULL,
    raw_payload JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------
-- 5. TRANSPORTATION PROVIDERS TABLE (New)
-- Used by the Logistics Agent to calculate variable freight rates.
-- ------------------------------------------
CREATE TABLE transportation_providers (
    provider_id SERIAL PRIMARY KEY,
    provider_name VARCHAR(100) NOT NULL UNIQUE,
    transport_mode VARCHAR(50) NOT NULL,
    base_rate_per_ton_km DECIMAL(10,4) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- ------------------------------------------
-- 6. PERFORMANCE & SCALABILITY INDEXES
-- Enforces speed during asynchronous Multi-Agent lookups.
-- ------------------------------------------
CREATE INDEX idx_inventory_material ON inventory(material_name);
CREATE INDEX idx_agent_active ON agent_registry(agent_id, account_status);
CREATE INDEX idx_po_agent ON purchase_orders(agent_id);
CREATE INDEX idx_audit_agent ON audit_log(agent_id);

-- ==========================================
-- SEED INITIAL MOCK DATA
-- ==========================================

-- Seed Initial Factory Stock (INR aligned)
INSERT INTO inventory (material_name, current_stock_tons, safety_stock_tons, reorder_point_tons, average_daily_consumption, max_lead_time_days, max_budget_per_ton)
VALUES
    ('Bulk Wheat Flour', 15.00, 20.00, 35.00, 5.00, 7, 40000.00),
    ('Refined Sugar', 40.00, 10.00, 15.00, 2.50, 10, 45000.00),
    ('Palm Oil', 8.00, 10.00, 18.00, 3.00, 5, 80000.00),
    ('Cocoa Beans', 5.00, 8.00, 12.00, 1.50, 14, 280000.00),
    ('Bulk Corn (Maize)', 25.00, 15.00, 30.00, 4.00, 7, 18000.00),
    ('Corrugated Cartons', 50.00, 20.00, 40.00, 10.00, 4, 10000.00);

-- Seed Agent Identities (INR aligned)
INSERT INTO agent_registry (agent_id, auth_token, assigned_role, max_per_transaction_budget, account_status)
VALUES
    ('AGENT_INVENTORY_01', 'inv_token_123', 'Inventory Agent', 0.00, TRUE),
    ('AGENT_FINANCE_01', 'secret_fin_token_123', 'Finance Agent', 4000000.00, TRUE),
    ('AGENT_ROGUE_01', 'secret_rogue_token', 'Finance Agent', 100000.00, FALSE);

-- Seed Logistics Providers (INR aligned to match market_telemetry.py)
INSERT INTO transportation_providers (provider_name, transport_mode, base_rate_per_ton_km)
VALUES
    ('FastFreight Logistics', 'Road', 4.5000),
    ('National Rail Cargo', 'Rail', 2.0000),
    ('Express Transit Freight', 'Road', 5.2000);


    -- SUPPLIERS TABLE & BENCHMARK SEED DATA
-- Module: Persistence Layer (Member 2)
-- ==========================================

-- 1. Create the Suppliers Table
CREATE TABLE IF NOT EXISTS suppliers (
    vendor_id VARCHAR(50) PRIMARY KEY,
    material_supplied VARCHAR(100) NOT NULL REFERENCES inventory(material_name) ON DELETE CASCADE,
    price_inr DECIMAL(12,2) NOT NULL CHECK (price_inr > 0),
    lead_time_days INT NOT NULL CHECK (lead_time_days > 0),
    reliability DECIMAL(3,2) NOT NULL CHECK (reliability >= 0.00 AND reliability <= 1.00), -- Decimal format (e.g. 0.90 = 90%)
    is_active BOOLEAN DEFAULT TRUE
);

-- 2. Performance Index for Fast MCDM Candidate Querying
CREATE INDEX IF NOT EXISTS idx_suppliers_lookup ON suppliers(material_supplied, is_active);

-- 3. Seed Candidate Vendors Across All 6 FMCG Catalog Items
INSERT INTO suppliers (vendor_id, material_supplied, price_inr, lead_time_days, reliability)
VALUES 
    -- 1. Bulk Wheat Flour (INR per Ton)
    ('Shakti Agro Mills Ltd.', 'Bulk Wheat Flour', 35000.00, 6, 0.90),
    ('Deccan Roller Flour Mills', 'Bulk Wheat Flour', 33000.00, 9, 0.82),
    ('Narmada Grain & Agritech', 'Bulk Wheat Flour', 38000.00, 5, 0.95),

    -- 2. Refined Sugar (INR per Ton)
    ('Konkan Sugars Ltd.', 'Refined Sugar', 42000.00, 7, 0.92),
    ('Baramati Cane Refineries', 'Refined Sugar', 39000.00, 11, 0.80),
    ('Godavari Sugar Corp.', 'Refined Sugar', 44000.00, 4, 0.97),

    -- 3. Palm Oil (INR per Ton)
    ('Sahyadri Oils Ltd.', 'Palm Oil', 75000.00, 5, 0.88),
    ('Adani Wilmar Industrial', 'Palm Oil', 71000.00, 8, 0.84),
    ('Godrej Agrovet Palm Div.', 'Palm Oil', 78000.00, 3, 0.96),

    -- 4. Cocoa Beans (INR per Ton)
    ('Malabar Cocoa Estates', 'Cocoa Beans', 260000.00, 12, 0.91),
    ('Nilgiri Craft Cocoa Ltd.', 'Cocoa Beans', 245000.00, 16, 0.85),
    ('Olam Food Ingredients', 'Cocoa Beans', 275000.00, 8, 0.98),

    -- 5. Bulk Corn (Maize) (INR per Ton)
    ('Kaveri Maize & Starch Co.', 'Bulk Corn (Maize)', 16000.00, 6, 0.89),
    ('Vidarbha Agro Corp.', 'Bulk Corn (Maize)', 15000.00, 10, 0.81),
    ('Indus Grain Logistics', 'Bulk Corn (Maize)', 17500.00, 4, 0.93),

    -- 6. Corrugated Cartons (INR per 1000 Units)
    ('Horizon Packtech Ltd.', 'Corrugated Cartons', 9000.00, 4, 0.94),
    ('Western India Corrugators', 'Corrugated Cartons', 8200.00, 7, 0.87),
    ('Apex Kraft Packaging', 'Corrugated Cartons', 9500.00, 2, 0.98)

ON CONFLICT (vendor_id) DO UPDATE 
SET price_inr = EXCLUDED.price_inr,
    lead_time_days = EXCLUDED.lead_time_days,
    reliability = EXCLUDED.reliability,
    is_active = EXCLUDED.is_active;