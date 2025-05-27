-- Data Model Refactoring Migration
-- Separates static data from cycle-specific/historical data
-- 
-- Changes:
-- 1. Remove cycle_code from Deal table
-- 2. Remove cycle_code and time-varying fields from Tranche table  
-- 3. Create new Tranche_Historical table for cycle-specific data
-- 4. Migrate existing data to new structure

-- Step 1: Create the new Tranche_Historical table
CREATE TABLE IF NOT EXISTS tranche_historical (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tranche_id INTEGER NOT NULL,
    cycle_code VARCHAR(50) NOT NULL,
    principal_amount DECIMAL(20, 2) NOT NULL,
    interest_rate DECIMAL(8, 6) NOT NULL,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (tranche_id) REFERENCES tranche(id),
    UNIQUE(tranche_id, cycle_code)
);

-- Step 2: Migrate existing tranche data to historical table
-- This preserves existing cycle-specific data
INSERT INTO tranche_historical (tranche_id, cycle_code, principal_amount, interest_rate, created_date, updated_date, is_active)
SELECT 
    id as tranche_id,
    COALESCE(cycle_code, '2024Q4') as cycle_code,  -- Default cycle for existing data
    principal_amount,
    interest_rate,
    created_date,
    updated_date,
    is_active
FROM tranche 
WHERE cycle_code IS NOT NULL;

-- Step 3: Create temporary backup tables
CREATE TABLE deal_backup AS SELECT * FROM deal;
CREATE TABLE tranche_backup AS SELECT * FROM tranche;

-- Step 4: Recreate Deal table without cycle_code
DROP TABLE deal;
CREATE TABLE deal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    originator VARCHAR(255) NOT NULL,
    deal_type VARCHAR(50) NOT NULL,
    closing_date DATE,
    total_principal DECIMAL(20, 2) NOT NULL,
    credit_rating VARCHAR(10),
    yield_rate DECIMAL(8, 6),
    duration DECIMAL(8, 2),
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Step 5: Migrate deal data (excluding cycle_code)
INSERT INTO deal (id, name, originator, deal_type, closing_date, total_principal, credit_rating, yield_rate, duration, created_date, updated_date, is_active)
SELECT 
    id, name, originator, deal_type, closing_date, total_principal, credit_rating, yield_rate, duration, created_date, updated_date, is_active
FROM deal_backup;

-- Step 6: Recreate Tranche table without cycle_code and time-varying fields
DROP TABLE tranche;
CREATE TABLE tranche (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    class_name VARCHAR(50) NOT NULL,
    subordination_level INTEGER DEFAULT 1,
    credit_rating VARCHAR(10),
    payment_priority INTEGER DEFAULT 1,
    maturity_date DATE,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (deal_id) REFERENCES deal(id)
);

-- Step 7: Migrate tranche static data (excluding cycle_code, principal_amount, interest_rate)
INSERT INTO tranche (id, deal_id, name, class_name, subordination_level, credit_rating, payment_priority, maturity_date, created_date, updated_date, is_active)
SELECT DISTINCT
    id, deal_id, name, class_name, subordination_level, credit_rating, payment_priority, maturity_date, created_date, updated_date, is_active
FROM tranche_backup;

-- Step 8: Create indexes for performance
CREATE INDEX idx_tranche_historical_tranche_id ON tranche_historical(tranche_id);
CREATE INDEX idx_tranche_historical_cycle_code ON tranche_historical(cycle_code);
CREATE INDEX idx_tranche_historical_tranche_cycle ON tranche_historical(tranche_id, cycle_code);
CREATE INDEX idx_tranche_deal_id ON tranche(deal_id);
CREATE INDEX idx_deal_originator ON deal(originator);
CREATE INDEX idx_deal_deal_type ON deal(deal_type);

-- Step 9: Clean up backup tables (optional - comment out to keep backups)
-- DROP TABLE deal_backup;
-- DROP TABLE tranche_backup;

-- Verification queries to check migration success
-- SELECT 'Deal count:' as check_type, COUNT(*) as count FROM deal;
-- SELECT 'Tranche count:' as check_type, COUNT(*) as count FROM tranche;
-- SELECT 'Historical records count:' as check_type, COUNT(*) as count FROM tranche_historical;
-- SELECT 'Unique tranche-cycle combinations:' as check_type, COUNT(DISTINCT tranche_id || '-' || cycle_code) as count FROM tranche_historical;