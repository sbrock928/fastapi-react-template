-- Migration 007: Enforce unique calculation names across all group levels
-- This prevents duplicate calculation names like "Total Interest Distribution" 
-- that exist at both deal and tranche levels

-- First, identify any duplicate calculation names that exist across different group levels
SELECT name, GROUP_CONCAT(DISTINCT group_level) as group_levels, COUNT(*) as count
FROM calculations 
WHERE is_active = 1 
GROUP BY name 
HAVING COUNT(*) > 1;

-- Before applying the new constraint, we need to rename any duplicate calculations
-- Update the tranche-level "Total Interest Distribution" to be more specific
UPDATE calculations 
SET name = 'Total Interest Distribution (Tranche Level)'
WHERE name = 'Total Interest Distribution' 
  AND group_level = 'tranche' 
  AND is_active = 1;

-- Drop the old unique constraint that allowed duplicates across group levels
DROP INDEX uq_calc_name_group_level_active ON calculations;

-- Create the new unique constraint that enforces uniqueness across all group levels
CREATE UNIQUE INDEX uq_calc_name_active ON calculations (name, is_active);

-- Verify no duplicates remain
SELECT name, GROUP_CONCAT(DISTINCT group_level) as group_levels, COUNT(*) as count
FROM calculations 
WHERE is_active = 1 
GROUP BY name 
HAVING COUNT(*) > 1;