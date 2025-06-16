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
  return allAvailableFields[sourceModel] || [];
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
  
  // Use the enhanced validation
  const parseResult = parseAndValidateComplexSQL(
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
 * Get calculation type info for UI display
 */
export const getCalculationTypeInfo = (modalType: 'user-defined' | 'system-field' | 'system-sql') => {
  switch (modalType) {
    case 'user-defined':
      return {
        title: 'User Defined Calculation',
        description: 'Create aggregated calculations using functions like SUM, AVG, COUNT, etc.',
        icon: 'bi-person-gear',
        color: 'primary',
        examples: [
          'Total Ending Balance (SUM)',
          'Average Pass Through Rate (WEIGHTED_AVG)',
          'Tranche Count (COUNT)'
        ]
      };
    case 'system-field':
      return {
        title: 'System Field Calculation',
        description: 'Expose raw model fields for use in reports and other calculations',
        icon: 'bi-database',
        color: 'success',
        examples: [
          'Deal Number (Deal.dl_nbr)',
          'Tranche ID (Tranche.tr_id)',
          'Issuer Code (Deal.issr_cde)'
        ]
      };
    case 'system-sql':
      return {
        title: 'System SQL Calculation',
        description: 'Advanced custom calculations using validated SQL queries',
        icon: 'bi-code-square',
        color: 'warning',
        examples: [
          'Issuer Type Classification',
          'Performance Category',
          'Custom Business Logic'
        ]
      };
    default:
      return {
        title: 'Calculation',
        description: '',
        icon: 'bi-question-circle',
        color: 'secondary',
        examples: []
      };
  }
};

/**
 * Format field name for display
 */
export const formatFieldName = (fieldName: string): string => {
  return fieldName
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase());
};

/**
 * Get SQL template based on group level and result column
 */
export const getSqlTemplate = (groupLevel: string, resultColumn: string = 'result_column'): string => {
  if (groupLevel === 'deal') {
    return `-- Deal-level calculation template
SELECT 
    deal.dl_nbr,
    CASE 
        WHEN deal.issr_cde LIKE '%FHLMC%' THEN 'GSE'
        WHEN deal.issr_cde LIKE '%GNMA%' THEN 'Government'
        ELSE 'Private'
    END AS ${resultColumn}
FROM deal
WHERE deal.dl_nbr IN (101, 102, 103)`;
  } else {
    return `-- Tranche-level calculation template
SELECT 
    deal.dl_nbr,
    tranche.tr_id,
    CASE 
        WHEN tranchebal.tr_end_bal_amt >= 25000000 THEN 'Large'
        WHEN tranchebal.tr_end_bal_amt >= 10000000 THEN 'Medium'
        ELSE 'Small'
    END AS ${resultColumn}
FROM deal
JOIN tranche ON deal.dl_nbr = tranche.dl_nbr
JOIN tranchebal ON tranche.dl_nbr = tranchebal.dl_nbr 
    AND tranche.tr_id = tranchebal.tr_id
WHERE deal.dl_nbr IN (101, 102, 103)
    AND tranche.tr_id IN ('A', 'B')
    AND tranchebal.cycle_cde = 202404`;
  }
};

/**
 * Enhanced SQL templates for complex queries including CTEs
 */
export const getCTESqlTemplate = (groupLevel: string, resultColumn: string = 'result_column'): string => {
  if (groupLevel === 'deal') {
    return `-- CTE Example: Deal-level with complex business logic
WITH deal_metrics AS (
    SELECT 
        deal.dl_nbr,
        COUNT(tranche.tr_id) as tranche_count,
        SUM(tranchebal.tr_end_bal_amt) as total_balance
    FROM deal
    JOIN tranche ON deal.dl_nbr = tranche.dl_nbr
    JOIN tranchebal ON tranche.dl_nbr = tranchebal.dl_nbr 
        AND tranche.tr_id = tranchebal.tr_id
    GROUP BY deal.dl_nbr
),
issuer_categories AS (
    SELECT 
        dl_nbr,
        CASE 
            WHEN issr_cde LIKE '%FHLMC%' THEN 'GSE'
            WHEN issr_cde LIKE '%GNMA%' THEN 'Government'
            ELSE 'Private'
        END as issuer_type
    FROM deal
)
SELECT 
    dm.dl_nbr,
    CASE 
        WHEN dm.total_balance >= 100000000 AND ic.issuer_type = 'GSE' THEN 'Large GSE'
        WHEN dm.total_balance >= 50000000 AND ic.issuer_type = 'Government' THEN 'Large Gov'
        WHEN dm.tranche_count > 5 THEN 'Complex Structure'
        ELSE 'Standard'
    END AS ${resultColumn}
FROM deal_metrics dm
JOIN issuer_categories ic ON dm.dl_nbr = ic.dl_nbr`;
  } else {
    return `-- CTE Example: Tranche-level with window functions
WITH tranche_rankings AS (
    SELECT 
        deal.dl_nbr,
        tranche.tr_id,
        tranchebal.tr_end_bal_amt,
        ROW_NUMBER() OVER (
            PARTITION BY deal.dl_nbr 
            ORDER BY tranchebal.tr_end_bal_amt DESC
        ) as size_rank
    FROM deal
    JOIN tranche ON deal.dl_nbr = tranche.dl_nbr
    JOIN tranchebal ON tranche.dl_nbr = tranchebal.dl_nbr 
        AND tranche.tr_id = tranchebal.tr_id
),
deal_totals AS (
    SELECT 
        dl_nbr,
        SUM(tr_end_bal_amt) as deal_total
    FROM tranche_rankings
    GROUP BY dl_nbr
)
SELECT 
    tr.dl_nbr,
    tr.tr_id,
    CASE 
        WHEN tr.size_rank = 1 THEN 'Senior'
        WHEN tr.tr_end_bal_amt / dt.deal_total > 0.3 THEN 'Major'
        WHEN tr.tr_end_bal_amt / dt.deal_total > 0.1 THEN 'Minor'
        ELSE 'Residual'
    END AS ${resultColumn}
FROM tranche_rankings tr
JOIN deal_totals dt ON tr.dl_nbr = dt.dl_nbr`;
  }
};

/**
 * Get advanced SQL example templates
 */
export const getAdvancedSqlExamples = (): { [key: string]: string } => {
  return {
    'Recursive CTE': `-- Recursive CTE example (use with caution)
WITH RECURSIVE hierarchy AS (
    -- Base case
    SELECT dl_nbr, tr_id, 1 as level
    FROM tranche 
    WHERE tr_id = 'A'
    
    UNION ALL
    
    -- Recursive case
    SELECT t.dl_nbr, t.tr_id, h.level + 1
    FROM tranche t
    JOIN hierarchy h ON t.dl_nbr = h.dl_nbr
    WHERE t.tr_id > h.tr_id AND h.level < 5
)
SELECT 
    dl_nbr,
    tr_id,
    CASE 
        WHEN level = 1 THEN 'Senior'
        WHEN level <= 3 THEN 'Mezzanine'
        ELSE 'Subordinate'
    END AS tranche_level
FROM hierarchy`,

    'Multiple CTEs with Joins': `-- Complex multi-CTE analysis
WITH performance_metrics AS (
    SELECT 
        deal.dl_nbr,
        AVG(tranchebal.tr_pass_thru_rte) as avg_rate,
        STDDEV(tranchebal.tr_pass_thru_rte) as rate_volatility
    FROM deal
    JOIN tranche ON deal.dl_nbr = tranche.dl_nbr
    JOIN tranchebal ON tranche.dl_nbr = tranchebal.dl_nbr 
        AND tranche.tr_id = tranchebal.tr_id
    GROUP BY deal.dl_nbr
),
size_categories AS (
    SELECT 
        dl_nbr,
        CASE 
            WHEN SUM(tr_end_bal_amt) >= 100000000 THEN 'Large'
            WHEN SUM(tr_end_bal_amt) >= 25000000 THEN 'Medium'
            ELSE 'Small'
        END as size_category
    FROM tranchebal
    GROUP BY dl_nbr
)
SELECT 
    pm.dl_nbr,
    CASE 
        WHEN pm.avg_rate > 0.05 AND pm.rate_volatility < 0.01 AND sc.size_category = 'Large' THEN 'Premium'
        WHEN pm.avg_rate > 0.03 AND sc.size_category IN ('Large', 'Medium') THEN 'Standard'
        WHEN pm.rate_volatility > 0.02 THEN 'High Risk'
        ELSE 'Basic'
    END AS risk_rating
FROM performance_metrics pm
JOIN size_categories sc ON pm.dl_nbr = sc.dl_nbr`,

    'Window Functions': `-- Advanced window function example
WITH ranked_tranches AS (
    SELECT 
        deal.dl_nbr,
        tranche.tr_id,
        tranchebal.tr_end_bal_amt,
        RANK() OVER (PARTITION BY deal.dl_nbr ORDER BY tranchebal.tr_end_bal_amt DESC) as balance_rank,
        LAG(tranchebal.tr_end_bal_amt) OVER (PARTITION BY deal.dl_nbr ORDER BY tranche.tr_id) as prev_balance,
        FIRST_VALUE(tranchebal.tr_end_bal_amt) OVER (
            PARTITION BY deal.dl_nbr 
            ORDER BY tranchebal.tr_end_bal_amt DESC
            ROWS UNBOUNDED PRECEDING
        ) as largest_balance
    FROM deal
    JOIN tranche ON deal.dl_nbr = tranche.dl_nbr
    JOIN tranchebal ON tranche.dl_nbr = tranchebal.dl_nbr 
        AND tranche.tr_id = tranchebal.tr_id
)
SELECT 
    dl_nbr,
    tr_id,
    CASE 
        WHEN balance_rank = 1 THEN 'Dominant'
        WHEN tr_end_bal_amt / largest_balance > 0.5 THEN 'Significant'
        WHEN prev_balance IS NOT NULL AND tr_end_bal_amt < prev_balance * 0.5 THEN 'Step Down'
        ELSE 'Standard'
    END AS tranche_profile
FROM ranked_tranches`
  };
};

/**
 * Enhanced SQL syntax validation for the editor
 */
export const validateSqlSyntax = (sql: string): { isValid: boolean; errors: string[]; warnings?: string[] } => {
  if (!sql?.trim()) {
    return { isValid: false, errors: ['SQL query cannot be empty'] };
  }

  const parseResult = parseAndValidateComplexSQL(sql, 'deal', 'result_column');
  
  return {
    isValid: parseResult.isValid,
    errors: parseResult.errors,
    warnings: parseResult.warnings
  };
};

/**
 * Get calculation complexity score for sorting/display purposes
 */
export const getCalculationComplexity = (calculation: CalculationForm): number => {
  let complexity = 0;
  
  // Base complexity by type
  switch (calculation.function_type) {
    case 'SYSTEM_FIELD':
      complexity = 1; // Simplest
      break;
    case 'SUM':
    case 'COUNT':
    case 'MIN':
    case 'MAX':
      complexity = 2; // Simple aggregations
      break;
    case 'AVG':
      complexity = 3; // Medium complexity
      break;
    case 'WEIGHTED_AVG':
      complexity = 4; // More complex
      break;
    case 'SYSTEM_SQL':
      complexity = 5; // Most complex
      break;
    default:
      complexity = 2;
  }
  
  // Add complexity for weight fields
  if (calculation.weight_field && calculation.function_type !== 'SYSTEM_SQL') {
    complexity += 1;
  }
  
  // Add complexity for tranche level (more data)
  if (calculation.level === 'tranche') {
    complexity += 1;
  }
  
  return complexity;
};

/**
 * Generate a suggested calculation name based on configuration
 */
export const suggestCalculationName = (calculation: CalculationForm): string => {
  if (calculation.function_type === 'SYSTEM_FIELD') {
    if (calculation.source && calculation.source_field) {
      return formatFieldName(calculation.source_field);
    }
    return 'System Field';
  }
  
  if (calculation.function_type === 'SYSTEM_SQL') {
    return 'Custom SQL Calculation';
  }
  
  // User-defined calculations
  if (!calculation.function_type || !calculation.source_field) {
    return 'New Calculation';
  }
  
  const fieldName = formatFieldName(calculation.source_field);
  const functionName = calculation.function_type.replace('_', ' ');
  
  if (calculation.function_type === 'WEIGHTED_AVG') {
    return `Weighted Average ${fieldName}`;
  }
  
  return `${functionName} ${fieldName}`;
};

/**
 * Check if calculation has unsaved changes
 */
export const hasUnsavedChanges = (
  current: CalculationForm, 
  original: CalculationForm | null
): boolean => {
  if (!original) {
    // New calculation - check if any meaningful data is entered
    return !!(
      current.name?.trim() ||
      current.description?.trim() ||
      (current.function_type && current.function_type !== 'SUM') ||
      current.source ||
      current.source_field ||
      current.weight_field?.trim()
    );
  }

  // Compare with original
  return (
    current.name !== original.name ||
    current.description !== original.description ||
    current.function_type !== original.function_type ||
    current.source !== original.source ||
    current.source_field !== original.source_field ||
    current.level !== original.level ||
    current.weight_field !== original.weight_field
  );
};

/**
 * Get SQL template for editor based on group level
 */
export const getSqlTemplateForEditor = (groupLevel: string): string => {
  if (groupLevel === 'deal') {
    return `-- SQL Template: Deal-level
SELECT 
    deal.dl_nbr,
    deal.issr_cde,
    SUM(tranchebal.tr_end_bal_amt) AS total_balance
FROM deal
JOIN tranche ON deal.dl_nbr = tranche.dl_nbr
JOIN tranchebal ON tranche.dl_nbr = tranchebal.dl_nbr 
    AND tranche.tr_id = tranchebal.tr_id
GROUP BY deal.dl_nbr, deal.issr_cde
ORDER BY deal.dl_nbr`;
  } else {
    return `-- SQL Template: Tranche-level
SELECT 
    deal.dl_nbr,
    tranche.tr_id,
    tranchebal.tr_end_bal_amt,
    tranchebal.tr_pass_thru_rte
FROM deal
JOIN tranche ON deal.dl_nbr = tranche.dl_nbr
JOIN tranchebal ON tranche.dl_nbr = tranchebal.dl_nbr 
    AND tranche.tr_id = tranchebal.tr_id
WHERE tranchebal.cycle_cde = 202404
ORDER BY deal.dl_nbr, tranche.tr_id`;
  }
};