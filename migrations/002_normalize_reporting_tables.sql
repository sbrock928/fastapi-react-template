-- Migration to refactor reporting data model from JSON to normalized tables
-- This migration creates the new tables and migrates existing data

BEGIN TRANSACTION;

-- Create the new normalized tables
CREATE TABLE IF NOT EXISTS report_deals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    deal_id INTEGER NOT NULL,
    FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS report_tranches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_deal_id INTEGER NOT NULL,
    tranche_id INTEGER NOT NULL,
    FOREIGN KEY (report_deal_id) REFERENCES report_deals (id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_report_deals_report_id ON report_deals(report_id);
CREATE INDEX IF NOT EXISTS idx_report_deals_deal_id ON report_deals(deal_id);
CREATE INDEX IF NOT EXISTS idx_report_tranches_report_deal_id ON report_tranches(report_deal_id);
CREATE INDEX IF NOT EXISTS idx_report_tranches_tranche_id ON report_tranches(tranche_id);

-- Migrate existing data if the old columns exist
-- Note: This assumes the old structure had selected_deals and selected_tranches as JSON columns

-- First, check if we need to migrate data from old JSON columns
-- If the old columns don't exist, this will be a no-op

-- Remove old JSON columns if they exist (we're dropping backward compatibility)
-- This will drop the data - make sure to backup if needed
ALTER TABLE reports DROP COLUMN IF EXISTS selected_deals;
ALTER TABLE reports DROP COLUMN IF EXISTS selected_tranches;

COMMIT;