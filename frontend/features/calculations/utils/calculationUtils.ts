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
 * Validate system SQL calculation
 */
const validateSystemSqlCalculation = (calculation: CalculationForm): string | null => {
  if (!calculation.source_field?.trim()) {
    return 'SQL query is required';
  }
  
  if (!calculation.weight_field?.trim()) {
    return 'Result column name is required';
  }
  
  // Enhanced basic SQL validation
  const sql = calculation.source_field.trim().toLowerCase();
  
  if (!sql.startsWith('select')) {
    return 'SQL must be a SELECT statement';
  }
  
  if (!sql.includes('from')) {
    return 'SQL must include a FROM clause';
  }
  
  // Check for dangerous operations - enhanced patterns
  const dangerousPatterns = [
    /\bdrop\b/i,  // Any DROP statement
    /\bdelete\s+from\b/i,
    /\binsert\s+into\b/i,
    /\bupdate\s+.*\bset\b/i,
    /\balter\s+table\b/i,
    /\btruncate\s+table\b/i,
    /\bcreate\s+table\b/i,
    /\bexec\s*\(/i,
    /\bexecute\s*\(/i,
    /\bunion\s+select\b/i,
    /\bxp_cmdshell\b/i,
    /\bsp_\w+/i,  // Stored procedures
    /\bxp_\w+/i,  // Extended procedures
    /\bgrant\b/i,
    /\brevoke\b/i,
    /\bshutdown\b/i,
    /--/,  // SQL comments
    /\/\*.*\*\//  // Block comments
  ];
  
  for (const pattern of dangerousPatterns) {
    if (pattern.test(sql)) {
      return 'SQL contains dangerous operations or patterns that are not allowed';
    }
  }
  
  // Enhanced required fields validation - now check SELECT clause specifically
  const selectMatch = sql.match(/select\s+(.*?)\s+from/is);
  if (!selectMatch) {
    return 'Could not parse SELECT clause properly';
  }
  
  const selectClause = selectMatch[1].toLowerCase();
  
  // Check for required fields based on level - must be in SELECT clause
  if (calculation.level === 'deal') {
    if (!selectClause.includes('deal.dl_nbr') && !selectClause.includes('dl_nbr')) {
      return 'Deal-level SQL must include deal.dl_nbr in SELECT clause for proper grouping';
    }
  }
  
  if (calculation.level === 'tranche') {
    const hasDealNumber = selectClause.includes('deal.dl_nbr') || selectClause.includes('dl_nbr');
    const hasTrancheId = selectClause.includes('tranche.tr_id') || selectClause.includes('tr_id');
    
    if (!hasDealNumber) {
      return 'Tranche-level SQL must include deal.dl_nbr in SELECT clause for proper grouping';
    }
    
    if (!hasTrancheId) {
      return 'Tranche-level SQL must include tranche.tr_id in SELECT clause for proper grouping';
    }
  }
  
  // Validate result column name format
  const resultColumnName = calculation.weight_field.trim();
  if (!/^[a-zA-Z][a-zA-Z0-9_]*$/.test(resultColumnName)) {
    return 'Result column name must be a valid SQL identifier (letters, numbers, underscores, starting with letter)';
  }
  
  // Check for multiple statements
  const statements = sql.split(';').filter(s => s.trim());
  if (statements.length > 1) {
    return 'Multiple SQL statements are not allowed - only single SELECT statements permitted';
  }
  
  // Basic structure validation
  const columnCount = (selectClause.match(/,/g) || []).length + 1;
  if (columnCount < 2) {
    return 'SQL must select at least the required grouping fields plus one result column';
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
 * Get field type icon for UI display
 */
export const getFieldTypeIcon = (fieldType: string): string => {
  switch (fieldType.toLowerCase()) {
    case 'string':
    case 'text':
      return 'bi-type';
    case 'number':
    case 'integer':
      return 'bi-123';
    case 'currency':
    case 'money':
      return 'bi-currency-dollar';
    case 'percentage':
    case 'rate':
      return 'bi-percent';
    case 'date':
    case 'datetime':
      return 'bi-calendar';
    case 'boolean':
      return 'bi-toggle-on';
    default:
      return 'bi-question-circle';
  }
};

/**
 * Get aggregation function icon for UI display
 */
export const getAggregationFunctionIcon = (functionType: string): string => {
  switch (functionType.toUpperCase()) {
    case 'SUM':
      return 'bi-plus-circle';
    case 'AVG':
    case 'WEIGHTED_AVG':
      return 'bi-bar-chart';
    case 'COUNT':
      return 'bi-hash';
    case 'MIN':
      return 'bi-arrow-down-circle';
    case 'MAX':
      return 'bi-arrow-up-circle';
    case 'SYSTEM_FIELD':
      return 'bi-database';
    case 'SYSTEM_SQL':
      return 'bi-code-square';
    default:
      return 'bi-calculator';
  }
};

/**
 * Get source model icon for UI display
 */
export const getSourceModelIcon = (sourceModel: string): string => {
  switch (sourceModel) {
    case 'Deal':
      return 'bi-building';
    case 'Tranche':
      return 'bi-layers';
    case 'TrancheBal':
      return 'bi-graph-up';
    default:
      return 'bi-table';
  }
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
 * Validate SQL syntax (basic check)
 */
export const validateSqlSyntax = (sql: string): { isValid: boolean; errors: string[] } => {
  const errors: string[] = [];
  const trimmedSql = sql.trim().toLowerCase();
  
  if (!trimmedSql) {
    errors.push('SQL query cannot be empty');
    return { isValid: false, errors };
  }
  
  // Must start with SELECT
  if (!trimmedSql.startsWith('select')) {
    errors.push('SQL must start with SELECT');
  }
  
  // Must have FROM clause
  if (!trimmedSql.includes('from')) {
    errors.push('SQL must include a FROM clause');
  }
  
  // Check for dangerous operations
  const dangerousKeywords = ['drop', 'delete', 'insert', 'update', 'alter', 'truncate'];
  for (const keyword of dangerousKeywords) {
    if (trimmedSql.includes(keyword)) {
      errors.push(`Dangerous operation detected: ${keyword.toUpperCase()}`);
    }
  }
  
  // Check for basic SQL structure issues
  const selectCount = (trimmedSql.match(/\bselect\b/g) || []).length;
  const fromCount = (trimmedSql.match(/\bfrom\b/g) || []).length;
  
  if (selectCount > fromCount) {
    errors.push('Each SELECT must have a corresponding FROM clause');
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
};