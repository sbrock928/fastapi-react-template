-- Migration: Add approval fields to user_calculations table
-- Date: 2025-06-10
-- Description: Add approved_by and approval_date fields to user_calculations for consistency with system_calculations

-- Add approval fields to user_calculations table
ALTER TABLE user_calculations 
ADD COLUMN approved_by VARCHAR(100);

ALTER TABLE user_calculations 
ADD COLUMN approval_date DATETIME;

-- Auto-approve existing user calculations for consistency
UPDATE user_calculations 
SET approved_by = 'migration_auto_approval',
    approval_date = CURRENT_TIMESTAMP
WHERE is_active = 1 AND approved_by IS NULL;

-- Add comment for future reference
-- TODO: Implement proper approval workflow for both user and system calculations