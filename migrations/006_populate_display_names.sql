-- Migration to populate display_name for existing report calculations
-- This fixes the issue where user/system calculations show numeric IDs instead of meaningful names

-- First, let's see what we're working with
SELECT 
    rc.id,
    rc.calculation_id,
    rc.calculation_type,
    rc.display_name,
    r.name as report_name
FROM report_calculation rc
JOIN report r ON rc.report_id = r.id
WHERE rc.display_name IS NULL
ORDER BY rc.calculation_type, rc.calculation_id;

-- Update display_name for static fields (use the field name after "static_")
UPDATE report_calculation 
SET display_name = REPLACE(calculation_id, 'static_', '')
WHERE display_name IS NULL 
AND calculation_id LIKE 'static_%'
AND calculation_type = 'static_field';

-- Update display_name for user calculations
-- We'll use the name from the user_calculation table
UPDATE report_calculation 
SET display_name = (
    SELECT uc.name 
    FROM user_calculation uc 
    WHERE uc.id = CAST(report_calculation.calculation_id AS INTEGER)
)
WHERE display_name IS NULL 
AND calculation_type = 'user_calculation'
AND calculation_id NOT LIKE 'static_%'
AND CAST(calculation_id AS INTEGER) IN (
    SELECT id FROM user_calculation
);

-- Update display_name for system calculations
-- We'll use the name from the system_calculation table
UPDATE report_calculation 
SET display_name = (
    SELECT sc.name 
    FROM system_calculation sc 
    WHERE sc.id = CAST(report_calculation.calculation_id AS INTEGER)
)
WHERE display_name IS NULL 
AND calculation_type = 'system_calculation'
AND calculation_id NOT LIKE 'static_%'
AND CAST(calculation_id AS INTEGER) IN (
    SELECT id FROM system_calculation
);

-- For any remaining NULL display_names with numeric calculation_ids, 
-- try to auto-detect and populate from user_calculation first, then system_calculation
UPDATE report_calculation 
SET display_name = (
    SELECT uc.name 
    FROM user_calculation uc 
    WHERE uc.id = CAST(report_calculation.calculation_id AS INTEGER)
),
calculation_type = 'user_calculation'
WHERE display_name IS NULL 
AND calculation_id NOT LIKE 'static_%'
AND calculation_type IS NULL
AND CAST(calculation_id AS INTEGER) IN (
    SELECT id FROM user_calculation
);

UPDATE report_calculation 
SET display_name = (
    SELECT sc.name 
    FROM system_calculation sc 
    WHERE sc.id = CAST(report_calculation.calculation_id AS INTEGER)
),
calculation_type = 'system_calculation'
WHERE display_name IS NULL 
AND calculation_id NOT LIKE 'static_%'
AND calculation_type IS NULL
AND CAST(calculation_id AS INTEGER) IN (
    SELECT id FROM system_calculation
);

-- For any remaining NULL values where we can't find a match, 
-- set display_name to calculation_id as fallback
UPDATE report_calculation 
SET display_name = calculation_id
WHERE display_name IS NULL;

-- Verify the fix
SELECT 
    calculation_type,
    COUNT(*) as total_count,
    COUNT(display_name) as with_display_name,
    COUNT(*) - COUNT(display_name) as missing_display_name
FROM report_calculation
GROUP BY calculation_type
ORDER BY calculation_type;

-- Show sample results
SELECT 
    rc.id,
    rc.calculation_id,
    rc.calculation_type,
    rc.display_name,
    r.name as report_name
FROM report_calculation rc
JOIN report r ON rc.report_id = r.id
ORDER BY rc.calculation_type, rc.display_name
LIMIT 20;