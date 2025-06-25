-- Migration 008: Add dependent calculation columns
-- Date: 2025-06-24
-- Description: Add calculation_dependencies and calculation_expression columns to support dependent calculations

BEGIN TRANSACTION;

-- Add calculation_dependencies column (JSON array of calculation IDs this calculation depends on)
ALTER TABLE user_calculations 
ADD COLUMN calculation_dependencies TEXT NULL;

-- Add calculation_expression column (mathematical expression for dependent calculations)
ALTER TABLE user_calculations 
ADD COLUMN calculation_expression TEXT NULL;

-- Add comments to document the new columns
PRAGMA table_info(user_calculations);

-- Update schema version
INSERT OR REPLACE INTO schema_migrations (version, applied_at, description) 
VALUES (8, datetime('now'), 'Add dependent calculation columns');

COMMIT;