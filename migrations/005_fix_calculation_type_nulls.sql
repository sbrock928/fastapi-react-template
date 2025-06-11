-- Migration to fix NULL calculation_type values in report_calculation table
-- This addresses the issue where calculation_type was not being populated

-- First, let's see what we're working with
SELECT 
    rc.id,
    rc.calculation_id,
    rc.calculation_type,
    r.name as report_name
FROM report_calculation rc
JOIN report r ON rc.report_id = r.id
WHERE rc.calculation_type IS NULL
ORDER BY rc.id;

-- Update static fields (calculation_id starts with 'static_')
UPDATE report_calculation 
SET calculation_type = 'static_field'
WHERE calculation_type IS NULL 
AND calculation_id LIKE 'static_%';

-- For numeric calculation_ids, we need to check which table they exist in
-- First, update ones that exist in user_calculation table
UPDATE report_calculation 
SET calculation_type = 'user_calculation'
WHERE calculation_type IS NULL 
AND calculation_id NOT LIKE 'static_%'
AND CAST(calculation_id AS INTEGER) IN (
    SELECT id FROM user_calculation
);

-- Then update ones that exist in system_calculation table
UPDATE report_calculation 
SET calculation_type = 'system_calculation'
WHERE calculation_type IS NULL 
AND calculation_id NOT LIKE 'static_%'
AND CAST(calculation_id AS INTEGER) IN (
    SELECT id FROM system_calculation
);

-- For any remaining NULL values, default to user_calculation for backwards compatibility
UPDATE report_calculation 
SET calculation_type = 'user_calculation'
WHERE calculation_type IS NULL;

-- Verify the fix
SELECT 
    calculation_type,
    COUNT(*) as count
FROM report_calculation
GROUP BY calculation_type
ORDER BY calculation_type;

-- Show any remaining NULL values (should be none)
SELECT COUNT(*) as remaining_nulls
FROM report_calculation 
WHERE calculation_type IS NULL;