// frontend/features/calculations/utils/calculationUtils.ts
// Enhanced calculation utilities for the multi-type calculation system

import type { CalculationField, CalculationForm } from '@/types/calculations';

/**
 * Generate preview formula for calculation - Enhanced for all calculation types
 */
export const getPreviewFormula = (calculation: CalculationForm): string => {
  if (!calculation.function_type) {
    return 'Select calculation type to see preview';
  }

  // Handle System Field calculations
  if (calculation.function_type === 'SYSTEM_FIELD') {
    if (!calculation.source || !calculation.source_field) {
      return 'Select source model and field to see preview';
    }
    return `${calculation.source}.${calculation.source_field}`;
  }
  
  // Handle System SQL calculations
  if (calculation.function_type === 'SYSTEM_SQL') {
    const resultColumn = calculation.weight_field || 'result_column';
    return `Custom SQL → ${resultColumn}`;
  }

  // Handle User-defined calculations
  if (!calculation.source || !calculation.source_field) {
    return 'Select source model and field to see preview';
  }

  const field = `${calculation.source}.${calculation.source_field}`;
  
  if (calculation.function_type === 'WEIGHTED_AVG') {
    const weightField = calculation.weight_field ? 
      `${calculation.source}.${calculation.weight_field}` : 
      '[weight_field_required]';
    return `SUM(${field} * ${weightField}) / NULLIF(SUM(${weightField}), 0)`;
  }
  
  return `${calculation.function_type}(${field})`;
};

/**
 * Get scope compatibility warning - Enhanced for all calculation types
 */
export const getScopeCompatibilityWarning = (calculation: CalculationForm): string | null => {
  if (!calculation.function_type || !calculation.level) {
    return null;
  }

  // System Field calculations
  if (calculation.function_type === 'SYSTEM_FIELD') {
    if (!calculation.source) return null;
    
    if (calculation.level === 'deal' && calculation.source !== 'Deal') {
      return `Warning: ${calculation.source} fields in deal-level reports may create multiple rows per deal. Consider the appropriate grouping level.`;
    }
    
    if (calculation.level === 'tranche' && calculation.source === 'Deal') {
      return `Note: Deal fields at tranche level will be repeated for each tranche within the deal.`;
    }
    
    return null;
  }

  // System SQL calculations
  if (calculation.function_type === 'SYSTEM_SQL') {
    if (calculation.level === 'deal') {
      return `Note: Ensure your SQL aggregates data properly to maintain one row per deal. Must include deal.dl_nbr in SELECT.`;
    } else {
      return `Note: Ensure your SQL includes proper JOIN conditions for tranche-level data. Must include both deal.dl_nbr and tranche.tr_id in SELECT.`;
    }
  }

  // User-defined calculations
  if (!calculation.source) return null;
  
  if (calculation.level === 'deal' && calculation.source === 'TrancheBal' && calculation.function_type === 'RAW') {
    return `Warning: RAW TrancheBal fields in deal-level reports will create multiple rows per deal. Use aggregation functions instead.`;
  }
  
  if (calculation.level === 'tranche' && calculation.source === 'Deal') {
    return `Note: Deal fields at tranche level will be repeated for each tranche within the deal.`;
  }

  return null;
};

/**
 * Get recommended level based on calculation configuration - Enhanced for all types
 */
export const getRecommendedLevel = (calculation: CalculationForm): string | null => {
  if (!calculation.function_type) {
    return null;
  }

  // System Field recommendations
  if (calculation.function_type === 'SYSTEM_FIELD') {
    if (!calculation.source) return null;
    
    if (calculation.source === 'Deal') {
      return 'deal';
    } else if (calculation.source === 'Tranche' || calculation.source === 'TrancheBal') {
      return 'tranche'; // Default to tranche for more specific data
    }
  }

  // System SQL - no automatic recommendation since it depends on the SQL design
  if (calculation.function_type === 'SYSTEM_SQL') {
    return null; // User should choose based on their SQL design
  }

  // User-defined calculation recommendations
  if (!calculation.source) return null;
  
  if (calculation.source === 'Deal') {
    return 'deal';
  } else if (calculation.source === 'TrancheBal') {
    // For TrancheBal, recommend deal level for aggregations, tranche for detailed analysis
    return calculation.function_type === 'RAW' ? 'tranche' : 'deal';
  } else if (calculation.source === 'Tranche') {
    return 'tranche';
  }

  return null;
};

/**
 * Get available fields for a source model
 */
export const getAvailableFields = (
  sourceModel: string, 
  allAvailableFields: Record<string, CalculationField[]>
): CalculationField[] => {
  // Convert proper case model names to lowercase for field lookup
  const modelKeyMap: Record<string, string> = {
    'Deal': 'deal',
    'Tranche': 'tranche',
    'TrancheBal': 'tranchebal'
  };
  
  // Get the correct key for field lookup
  const lookupKey = modelKeyMap[sourceModel] || sourceModel.toLowerCase();
  
  return allAvailableFields[lookupKey] || [];
};

/**
 * Enhanced validation for all calculation types
 */
export const validateCalculationForm = (
  calculation: CalculationForm, 
  modalType: 'user-defined' | 'system-field' | 'system-sql'
): string | null => {
  // Basic validation for all types
  if (!calculation.name?.trim()) {
    return 'Calculation name is required';
  }
  
  if (calculation.name.trim().length < 3) {
    return 'Calculation name must be at least 3 characters long';
  }
  
  if (!calculation.level) {
    return 'Group level is required';
  }

  // Type-specific validation
  switch (modalType) {
    case 'user-defined':
      return validateUserDefinedCalculation(calculation);
    case 'system-field':
      return validateSystemFieldCalculation(calculation);
    case 'system-sql':
      return validateSystemSqlCalculation(calculation);
    default:
      return 'Invalid calculation type';
  }
};

/**
 * Validate user-defined calculation
 */
const validateUserDefinedCalculation = (calculation: CalculationForm): string | null => {
  if (!calculation.function_type || calculation.function_type === 'SYSTEM_FIELD' || calculation.function_type === 'SYSTEM_SQL') {
    return 'Please select a valid aggregation function';
  }
  
  if (!calculation.source) {
    return 'Source model is required';
  }
  
  if (!calculation.source_field) {
    return 'Source field is required';
  }
  
  if (calculation.function_type === 'WEIGHTED_AVG' && !calculation.weight_field) {
    return 'Weight field is required for weighted average calculations';
  }
  
  return null;
};

/**
 * Validate system field calculation
 */
const validateSystemFieldCalculation = (calculation: CalculationForm): string | null => {
  if (!calculation.source) {
    return 'Source model is required';
  }
  
  if (!calculation.source_field) {
    return 'Field selection is required';
  }
  
  return null;
};

/**
 * Enhanced SQL parsing and validation utilities for complex queries
 */

interface SQLParseResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  hasCTEs: boolean;
  hasSubqueries: boolean;
  finalSelectColumns: string[];
  usedTables: string[];
}

/**
 * Parse and validate complex SQL including CTEs
 */
export const parseAndValidateComplexSQL = (sql: string, groupLevel: string, resultColumn: string): SQLParseResult => {
  const result: SQLParseResult = {
    isValid: true,
    errors: [],
    warnings: [],
    hasCTEs: false,
    hasSubqueries: false,
    finalSelectColumns: [],
    usedTables: []
  };

  if (!sql?.trim()) {
    result.isValid = false;
    result.errors.push('SQL query cannot be empty');
    return result;
  }

  const sqlTrimmed = sql.trim();

  // Security validation - dangerous operations
  const dangerousPatterns = [
    /\bDROP\b/i, /\bDELETE\s+FROM\b/i, /\bTRUNCATE\b/i,
    /\bINSERT\s+INTO\b/i, /\bUPDATE\s+.*\bSET\b/i, /\bALTER\b/i,
    /\bCREATE\b/i, /\bEXEC\b/i, /\bEXECUTE\b/i,
    /\bxp_\w+/i, /\bsp_\w+/i, /\bGRANT\b/i, /\bREVOKE\b/i
  ];

  for (const pattern of dangerousPatterns) {
    if (pattern.test(sqlTrimmed)) {
      result.isValid = false;
      result.errors.push('SQL contains dangerous operations that are not allowed');
      return result;
    }
  }

  // Check for CTEs
  result.hasCTEs = /^\s*WITH\b/i.test(sqlTrimmed);
  
  // Check for subqueries
  result.hasSubqueries = /\(\s*SELECT\b/i.test(sqlTrimmed);

  try {
    // Extract final SELECT statement
    const finalSelect = extractFinalSelect(sqlTrimmed);
    if (!finalSelect) {
      result.isValid = false;
      result.errors.push('Could not identify the final SELECT statement');
      return result;
    }

    // Validate final SELECT structure
    const selectValidation = validateFinalSelect(finalSelect, groupLevel, resultColumn);
    result.errors.push(...selectValidation.errors);
    result.warnings.push(...selectValidation.warnings);
    result.finalSelectColumns = selectValidation.columns;
    result.usedTables = selectValidation.tables;

    if (selectValidation.errors.length > 0) {
      result.isValid = false;
    }

    // Additional validation for complex queries
    if (result.hasCTEs) {
      const cteValidation = validateCTEStructure(sqlTrimmed);
      result.warnings.push(...cteValidation.warnings);
      if (cteValidation.errors.length > 0) {
        result.errors.push(...cteValidation.errors);
        result.isValid = false;
      }
    }

  } catch (error) {
    result.isValid = false;
    result.errors.push(`SQL parsing error: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }

  return result;
};

/**
 * Extract the final SELECT statement from complex SQL
 */
function extractFinalSelect(sql: string): string | null {
  const sqlTrimmed = sql.trim();
  
  // If it starts with WITH, find the final SELECT after all CTEs
  if (/^\s*WITH\b/i.test(sqlTrimmed)) {
    // More sophisticated CTE parsing
    return extractFinalSelectFromCTE(sqlTrimmed);
  }
  
  // For simple queries, return the whole query if it starts with SELECT
  if (/^\s*SELECT\b/i.test(sqlTrimmed)) {
    return sqlTrimmed;
  }
  
  return null;
}

/**
 * Extract final SELECT from CTE query using proper parsing
 */
function extractFinalSelectFromCTE(sql: string): string | null {
  // Find all top-level parentheses groups that are part of CTE definitions
  let parenCount = 0;
  let inQuotes = false;
  let quoteChar = '';
  let cteEndPosition = -1;
  
  // Track if we're inside a CTE definition or the final query
  let afterWith = false;
  let finalSelectStart = -1;
  
  for (let i = 0; i < sql.length; i++) {
    const char = sql[i];
    const prevChar = i > 0 ? sql[i - 1] : '';
    const nextFewChars = sql.substring(i, i + 6).toUpperCase();
    
    // Handle quotes
    if ((char === '"' || char === "'") && prevChar !== '\\') {
      if (!inQuotes) {
        inQuotes = true;
        quoteChar = char;
      } else if (char === quoteChar) {
        inQuotes = false;
        quoteChar = '';
      }
    }
    
    if (!inQuotes) {
      // Track parentheses
      if (char === '(') {
        parenCount++;
      } else if (char === ')') {
        parenCount--;
        
        // If we're back to 0 parentheses after WITH, we might be at the end of CTEs
        if (parenCount === 0 && afterWith && cteEndPosition === -1) {
          cteEndPosition = i;
        }
      }
      
      // Check for WITH keyword at the start
      if (!afterWith && nextFewChars === 'WITH ') {
        afterWith = true;
      }
      
      // Look for SELECT after we've closed all CTE parentheses
      if (afterWith && parenCount === 0 && cteEndPosition !== -1 && finalSelectStart === -1) {
        if (nextFewChars.startsWith('SELECT')) {
          finalSelectStart = i;
          break;
        }
      }
    }
  }
  
  // If we found the final SELECT, extract it
  if (finalSelectStart !== -1) {
    return sql.substring(finalSelectStart).trim();
  }
  
  // Fallback: look for the last SELECT statement
  const selectMatches = [...sql.matchAll(/\bSELECT\b/gi)];
  if (selectMatches.length > 0) {
    const lastSelectIndex = selectMatches[selectMatches.length - 1].index;
    if (lastSelectIndex !== undefined) {
      return sql.substring(lastSelectIndex).trim();
    }
  }
  
  return null;
}

/**
 * Validate the final SELECT statement structure
 */
function validateFinalSelect(selectSql: string, groupLevel: string, resultColumn: string): {
  errors: string[];
  warnings: string[];
  columns: string[];
  tables: string[];
} {
  const errors: string[] = [];
  const warnings: string[] = [];
  const columns: string[] = [];
  const tables: string[] = [];

  // Extract SELECT clause
  const selectMatch = selectSql.match(/SELECT\s+(.*?)\s+FROM/is);
  if (!selectMatch) {
    errors.push('Could not parse SELECT clause');
    return { errors, warnings, columns, tables };
  }

  const selectClause = selectMatch[1];
  
  // Extract basic column info (simplified parsing)
  const columnPattern = /(?:(\w+\.)?(\w+)(?:\s+AS\s+(\w+))?)|(?:AS\s+(\w+))/gi;
  let match;
  while ((match = columnPattern.exec(selectClause)) !== null) {
    const columnName = match[4] || match[3] || match[2];
    if (columnName) columns.push(columnName);
  }

  // Extract table names from FROM and JOIN clauses
  const tablePattern = /(?:FROM|JOIN)\s+(\w+)/gi;
  let tableMatch;
  while ((tableMatch = tablePattern.exec(selectSql)) !== null) {
    tables.push(tableMatch[1].toLowerCase());
  }

  // Validate required columns based on group level
  const hasRequiredDeal = /\b(?:deal\.dl_nbr|dl_nbr)\b/i.test(selectClause);
  const hasRequiredTranche = /\b(?:tranche\.tr_id|tr_id)\b/i.test(selectClause);
  const hasResultColumn = new RegExp(`\\b${resultColumn}\\b`, 'i').test(selectClause);

  if (groupLevel === 'deal') {
    if (!hasRequiredDeal) {
      errors.push('Deal-level calculations must include deal.dl_nbr or dl_nbr in the final SELECT');
    }
  } else if (groupLevel === 'tranche') {
    if (!hasRequiredDeal) {
      errors.push('Tranche-level calculations must include deal.dl_nbr or dl_nbr in the final SELECT');
    }
    if (!hasRequiredTranche) {
      errors.push('Tranche-level calculations must include tranche.tr_id or tr_id in the final SELECT');
    }
  }

  if (!hasResultColumn && resultColumn) {
    errors.push(`Final SELECT must include the result column: ${resultColumn}`);
  }

  // Validate result column name format
  if (resultColumn && !/^[a-zA-Z][a-zA-Z0-9_]*$/.test(resultColumn)) {
    errors.push('Result column name must be a valid SQL identifier (letters, numbers, underscores, starting with letter)');
  }

  return { errors, warnings, columns, tables };
}

/**
 * Validate CTE structure
 */
function validateCTEStructure(sql: string): { errors: string[]; warnings: string[] } {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Check for basic CTE syntax
  if (!/WITH\s+\w+\s+AS\s*\(/i.test(sql)) {
    errors.push('Invalid CTE syntax. Use: WITH cte_name AS (SELECT ...)');
    return { errors, warnings };
  }

  // Check for balanced parentheses
  let parenCount = 0;
  let inQuotes = false;
  let quoteChar = '';
  
  for (let i = 0; i < sql.length; i++) {
    const char = sql[i];
    const prevChar = i > 0 ? sql[i - 1] : '';
    
    if ((char === '"' || char === "'") && prevChar !== '\\') {
      if (!inQuotes) {
        inQuotes = true;
        quoteChar = char;
      } else if (char === quoteChar) {
        inQuotes = false;
        quoteChar = '';
      }
    }
    
    if (!inQuotes) {
      if (char === '(') parenCount++;
      if (char === ')') parenCount--;
    }
  }

  if (parenCount !== 0) {
    errors.push('Unbalanced parentheses in CTE structure');
  }

  // Performance warnings
  const cteCount = (sql.match(/WITH\s+\w+\s+AS/gi) || []).length;
  if (cteCount > 5) {
    warnings.push(`High number of CTEs (${cteCount}) may impact performance`);
  }

  if (/RECURSIVE/i.test(sql)) {
    warnings.push('Recursive CTEs may have performance implications');
  }

  return { errors, warnings };
}

// Update the existing validateSystemSqlCalculation function
const validateSystemSqlCalculation = (calculation: CalculationForm): string | null => {
  if (!calculation.source_field?.trim()) {
    return 'SQL query is required';
  }
  
  if (!calculation.weight_field?.trim()) {
    return 'Result column name is required';
  }
  
  // Use the enhanced validation with placeholder support
  const parseResult = parseAndValidateComplexSQLWithPlaceholders(
    calculation.source_field.trim(),
    calculation.level,
    calculation.weight_field.trim()
  );

  if (!parseResult.isValid) {
    return parseResult.errors[0] || 'SQL validation failed';
  }

  // Return warnings as info (not blocking)
  if (parseResult.warnings.length > 0) {
    console.warn('SQL Warnings:', parseResult.warnings);
  }

  return null;
};

/**
 * Enhanced SQL parsing and validation with placeholder support
 */
export const parseAndValidateComplexSQLWithPlaceholders = (sql: string, groupLevel: string, resultColumn: string): SQLParseResult => {
  const result: SQLParseResult = {
    isValid: true,
    errors: [],
    warnings: [],
    hasCTEs: false,
    hasSubqueries: false,
    finalSelectColumns: [],
    usedTables: []
  };

  if (!sql?.trim()) {
    result.isValid = false;
    result.errors.push('SQL query cannot be empty');
    return result;
  }

  const sqlTrimmed = sql.trim();

  // Security validation - dangerous operations
  const dangerousPatterns = [
    /\bDROP\b/i, /\bDELETE\s+FROM\b/i, /\bTRUNCATE\b/i,
    /\bINSERT\s+INTO\b/i, /\bUPDATE\s+.*\bSET\b/i, /\bALTER\b/i,
    /\bCREATE\b/i, /\bEXEC\b/i, /\bEXECUTE\b/i,
    /\bxp_\w+/i, /\bsp_\w+/i, /\bGRANT\b/i, /\bREVOKE\b/i
  ];

  for (const pattern of dangerousPatterns) {
    if (pattern.test(sqlTrimmed)) {
      result.isValid = false;
      result.errors.push('SQL contains dangerous operations that are not allowed');
      return result;
    }
  }

  // Check for CTEs
  result.hasCTEs = /^\s*WITH\b/i.test(sqlTrimmed);
  
  // Check for subqueries
  result.hasSubqueries = /\(\s*SELECT\b/i.test(sqlTrimmed);

  // Validate placeholders
  const placeholderValidation = validatePlaceholders(sqlTrimmed);
  if (!placeholderValidation.isValid) {
    result.isValid = false;
    result.errors.push(...placeholderValidation.errors);
  }
  result.warnings.push(...placeholderValidation.warnings);

  try {
    // Extract final SELECT statement (after placeholder replacement for validation)
    const sqlForValidation = replacePlaceholdersForValidation(sqlTrimmed);
    const finalSelect = extractFinalSelect(sqlForValidation);
    if (!finalSelect) {
      result.isValid = false;
      result.errors.push('Could not identify the final SELECT statement');
      return result;
    }

    // Validate final SELECT structure
    const selectValidation = validateFinalSelect(finalSelect, groupLevel, resultColumn);
    result.errors.push(...selectValidation.errors);
    result.warnings.push(...selectValidation.warnings);
    result.finalSelectColumns = selectValidation.columns;
    result.usedTables = selectValidation.tables;

    if (selectValidation.errors.length > 0) {
      result.isValid = false;
    }

    // Additional validation for complex queries
    if (result.hasCTEs) {
      const cteValidation = validateCTEStructure(sqlForValidation);
      result.warnings.push(...cteValidation.warnings);
      if (cteValidation.errors.length > 0) {
        result.errors.push(...cteValidation.errors);
        result.isValid = false;
      }
    }

  } catch (error) {
    result.isValid = false;
    result.errors.push(`SQL parsing error: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }

  return result;
};

/**
 * Validate SQL placeholders
 */
function validatePlaceholders(sql: string): { isValid: boolean; errors: string[]; warnings: string[] } {
  const errors: string[] = [];
  const warnings: string[] = [];
  
  // Extract placeholders from SQL
  const placeholderPattern = /\{([^}]+)\}/g;
  const placeholders = [...sql.matchAll(placeholderPattern)].map(match => match[1]);
  
  // Define valid placeholders with proper typing
  const validPlaceholders: Record<string, string> = {
    'current_cycle': 'The selected reporting cycle code',
    'previous_cycle': 'The previous reporting cycle (current_cycle - 1)',
    'cycle_minus_2': 'Two cycles before current (current_cycle - 2)',
    'deal_filter': 'WHERE clause for selected deal numbers',
    'tranche_filter': 'WHERE clause for selected tranche IDs',
    'deal_tranche_filter': 'Combined WHERE clause for deal and tranche selections',
    'deal_numbers': 'Comma-separated list of selected deal numbers',
    'tranche_ids': 'Comma-separated list of selected tranche IDs (quoted)',
  };
  
  // Check each placeholder
  for (const placeholder of placeholders) {
    if (!(placeholder in validPlaceholders)) {
      errors.push(`Invalid placeholder '{${placeholder}}'. Valid placeholders: ${Object.keys(validPlaceholders).join(', ')}`);
    }
  }
  
  // Warnings for placeholder usage
  if (placeholders.includes('deal_tranche_filter') && (placeholders.includes('deal_filter') || placeholders.includes('tranche_filter'))) {
    warnings.push('Using both deal_tranche_filter and individual deal/tranche filters may create redundant conditions');
  }
  
  if (placeholders.includes('previous_cycle') || placeholders.includes('cycle_minus_2')) {
    warnings.push('Previous cycle placeholders may return empty results if historical data is not available');
  }
  
  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
}

/**
 * Replace placeholders with sample values for validation purposes
 */
function replacePlaceholdersForValidation(sql: string): string {
  const placeholderValues = {
    '{current_cycle}': '202404',
    '{previous_cycle}': '202403',
    '{cycle_minus_2}': '202402',
    '{deal_filter}': 'dl_nbr IN (101, 102, 103)',
    '{tranche_filter}': '(dl_nbr = 101 AND tr_id IN (\'A\', \'B\')) OR (dl_nbr = 102 AND tr_id IN (\'C\', \'D\'))',
    '{deal_tranche_filter}': '((dl_nbr = 101 AND tr_id IN (\'A\', \'B\')) OR (dl_nbr = 102 AND tr_id IN (\'C\', \'D\')))',
    '{deal_numbers}': '101, 102, 103',
    '{tranche_ids}': 'A\', \'B\', \'C\', \'D',
  };
  
  let validationSql = sql;
  for (const [placeholder, value] of Object.entries(placeholderValues)) {
    validationSql = validationSql.replace(new RegExp(placeholder.replace(/[{}]/g, '\\$&'), 'g'), value);
  }
  
  return validationSql;
}

/**
 * Get enhanced SQL template with placeholder examples
 */
export const getSqlTemplateWithPlaceholders = (groupLevel: string, resultColumn: string = 'result_column'): string => {
  if (groupLevel === 'deal') {
    return `-- Deal-level calculation with placeholders
WITH current_balances AS (
    SELECT 
        deal.dl_nbr,
        SUM(tranchebal.tr_end_bal_amt) as current_balance
    FROM deal
    JOIN tranche ON deal.dl_nbr = tranche.dl_nbr
    JOIN tranchebal ON tranche.dl_nbr = tranchebal.dl_nbr 
        AND tranche.tr_id = tranchebal.tr_id
    WHERE tranchebal.cycle_cde = {current_cycle}
        AND {deal_tranche_filter}
    GROUP BY deal.dl_nbr
),
previous_balances AS (
    SELECT 
        deal.dl_nbr,
        SUM(tranchebal.tr_end_bal_amt) as previous_balance
    FROM deal
    JOIN tranche ON deal.dl_nbr = tranche.dl_nbr
    JOIN tranchebal ON tranche.dl_nbr = tranchebal.dl_nbr 
        AND tranche.tr_id = tranchebal.tr_id
    WHERE tranchebal.cycle_cde = {previous_cycle}
        AND {deal_tranche_filter}
    GROUP BY deal.dl_nbr
)
SELECT 
    c.dl_nbr,
    CASE 
        WHEN p.previous_balance IS NULL THEN 'New Deal'
        WHEN c.current_balance > p.previous_balance * 1.1 THEN 'Growing'
        WHEN c.current_balance < p.previous_balance * 0.9 THEN 'Declining'
        ELSE 'Stable'
    END AS ${resultColumn}
FROM current_balances c
LEFT JOIN previous_balances p ON c.dl_nbr = p.dl_nbr`;
  } else {
    return `-- Tranche-level calculation with placeholders
WITH tranche_performance AS (
    SELECT 
        deal.dl_nbr,
        tranche.tr_id,
        tranchebal.tr_end_bal_amt,
        tranchebal.tr_pass_thru_rte,
        LAG(tranchebal.tr_end_bal_amt) OVER (
            PARTITION BY deal.dl_nbr, tranche.tr_id 
            ORDER BY tranchebal.cycle_cde
        ) as previous_balance
    FROM deal
    JOIN tranche ON deal.dl_nbr = tranche.dl_nbr
    JOIN tranchebal ON tranche.dl_nbr = tranchebal.dl_nbr 
        AND tranche.tr_id = tranchebal.tr_id
    WHERE tranchebal.cycle_cde IN ({current_cycle}, {previous_cycle})
        AND {deal_tranche_filter}
)
SELECT 
    dl_nbr,
    tr_id,
    CASE 
        WHEN tr_end_bal_amt >= 25000000 THEN 'Large'
        WHEN tr_pass_thru_rte > 0.05 THEN 'High Rate'
        WHEN previous_balance IS NOT NULL AND tr_end_bal_amt > previous_balance * 1.2 THEN 'Fast Growing'
        ELSE 'Standard'
    END AS ${resultColumn}
FROM tranche_performance
WHERE cycle_cde = {current_cycle}`;
  }
};

/**
 * Get available placeholders with descriptions
 */
export const getAvailablePlaceholders = (): { [key: string]: string } => {
  return {
    'current_cycle': 'The selected reporting cycle code',
    'previous_cycle': 'The previous reporting cycle (current_cycle - 1)',
    'cycle_minus_2': 'Two cycles before current (current_cycle - 2)',
    'deal_filter': 'WHERE clause for selected deal numbers (e.g., "dl_nbr IN (101, 102)")',
    'tranche_filter': 'WHERE clause for selected tranche IDs (e.g., "(dl_nbr = 101 AND tr_id IN (\'A\', \'B\'))")',
    'deal_tranche_filter': 'Combined WHERE clause for deal and tranche selections',
    'deal_numbers': 'Comma-separated list of selected deal numbers (e.g., "101, 102, 103")',
    'tranche_ids': 'Comma-separated list of selected tranche IDs, quoted (e.g., "A\', \'B\', \'C")',
  };
};

/**
 * Enhanced validation for calculation forms with placeholder support
 */
export const validateCalculationFormEnhanced = (
  calculation: CalculationForm, 
  modalType: 'user-defined' | 'system-field' | 'system-sql'
): string | null => {
  // Basic validation for all types
  if (!calculation.name?.trim()) {
    return 'Calculation name is required';
  }
  
  if (calculation.name.trim().length < 3) {
    return 'Calculation name must be at least 3 characters long';
  }
  
  if (!calculation.level) {
    return 'Group level is required';
  }

  // Type-specific validation
  switch (modalType) {
    case 'user-defined':
      return validateUserDefinedCalculation(calculation);
    case 'system-field':
      return validateSystemFieldCalculation(calculation);
    case 'system-sql':
      return validateSystemSqlCalculation(calculation);
    default:
      return 'Invalid calculation type';
  }
};