// frontend/features/calculations/utils/calculationUtils.ts
import type { CalculationField, CalculationForm } from '@/types/calculations';

/**
 * Generate preview formula for calculation - updated for system types
 */
export const getPreviewFormula = (calculation: CalculationForm): string => {
  if (!calculation.function_type || !calculation.source_field) {
    return 'Select function type and field to see preview';
  }

  // Handle different calculation types
  if (calculation.function_type === 'SYSTEM_FIELD') {
    return `${calculation.source}.${calculation.source_field}`;
  }
  
  if (calculation.function_type === 'SYSTEM_SQL') {
    return `Custom SQL → ${calculation.weight_field || 'result_column'}`;
  }

  // User-defined calculations
  const field = `${calculation.source}.${calculation.source_field}`;
  
  if (calculation.function_type === 'WEIGHTED_AVG') {
    const weightField = calculation.weight_field ? `${calculation.source}.${calculation.weight_field}` : '[weight_field]';
    return `SUM(${field} * ${weightField}) / NULLIF(SUM(${weightField}), 0)`;
  }
  
  return `${calculation.function_type}(${field})`;
};

/**
 * Get scope compatibility warning for calculation - updated for system types
 */
export const getScopeCompatibilityWarning = (calculation: CalculationForm): string | null => {
  if (!calculation.function_type || !calculation.source || !calculation.source_field || !calculation.level) {
    return null;
  }

  // System field calculations have different compatibility rules
  if (calculation.function_type === 'SYSTEM_FIELD') {
    if (calculation.level === 'deal' && calculation.source !== 'Deal') {
      return `Warning: ${calculation.source} fields in deal-level reports may create multiple rows per deal. Consider the appropriate grouping level.`;
    }
  }

  // System SQL calculations - warn about complexity
  if (calculation.function_type === 'SYSTEM_SQL') {
    if (calculation.level === 'deal') {
      return `Note: Ensure your SQL aggregates data properly to maintain one row per deal.`;
    } else {
      return `Note: Ensure your SQL includes proper JOIN conditions for tranche-level data.`;
    }
  }

  // User-defined calculations (no RAW function anymore)
  if (calculation.level === 'tranche' && calculation.source === 'Tranche') {
    return `Note: This tranche-level calculation will only be suitable for tranche-level reports.`;
  }

  return null;
};

/**
 * Get recommended level based on calculation configuration - updated for system types
 */
export const getRecommendedLevel = (calculation: CalculationForm): string | null => {
  if (!calculation.function_type || !calculation.source) {
    return null;
  }

  // System field recommendations
  if (calculation.function_type === 'SYSTEM_FIELD') {
    if (calculation.source === 'Deal') {
      return 'deal';
    } else if (calculation.source === 'Tranche' || calculation.source === 'TrancheBal') {
      return 'tranche';
    }
  }

  // System SQL recommendations based on level (no change needed)
  if (calculation.function_type === 'SYSTEM_SQL') {
    return calculation.level; // User should choose based on their SQL design
  }

  // User-defined calculation recommendations
  if (calculation.source === 'Deal') {
    return 'deal';
  } else if (calculation.source === 'TrancheBal') {
    return calculation.level || 'deal'; // Default to deal for most financial calculations
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
 * Validate calculation form - enhanced for system types
 */
export const validateCalculationForm = (
  calculation: CalculationForm, 
  modalType: 'user-defined' | 'system-field' | 'system-sql'
): string | null => {
  if (!calculation.name || !calculation.level) {
    return 'Please fill in name and group level';
  }

  switch (modalType) {
    case 'user-defined':
      if (!calculation.function_type || !calculation.source || !calculation.source_field) {
        return 'Please fill in all required fields (Function Type, Source, and Source Field)';
      }
      if (calculation.function_type === 'WEIGHTED_AVG' && !calculation.weight_field) {
        return 'Weight field is required for weighted average calculations';
      }
      break;
      
    case 'system-field':
      if (!calculation.source || !calculation.source_field) {
        return 'Please select source model and field';
      }
      break;
      
    case 'system-sql':
      if (!calculation.source_field || !calculation.weight_field) {
        return 'Please provide SQL query and result column name';
      }
      // Basic SQL validation
      const sql = calculation.source_field.trim().toLowerCase();
      if (!sql.startsWith('select')) {
        return 'SQL must be a SELECT statement';
      }
      if (!sql.includes('from')) {
        return 'SQL must include a FROM clause';
      }
      // Check for required fields based on level
      if (calculation.level === 'deal' && !sql.includes('deal.dl_nbr')) {
        return 'Deal-level SQL must include deal.dl_nbr in SELECT clause';
      }
      if (calculation.level === 'tranche' && (!sql.includes('deal.dl_nbr') || !sql.includes('tranche.tr_id'))) {
        return 'Tranche-level SQL must include both deal.dl_nbr and tranche.tr_id in SELECT clause';
      }
      break;
  }

  return null;
};

/**
 * Get calculation type info for UI
 */
export const getCalculationTypeInfo = (modalType: 'user-defined' | 'system-field' | 'system-sql') => {
  switch (modalType) {
    case 'user-defined':
      return {
        title: 'User Defined Calculation',
        description: 'Create aggregated calculations using functions like SUM, AVG, COUNT, etc.',
        icon: 'bi-person-gear',
        color: 'primary'
      };
    case 'system-field':
      return {
        title: 'System Field Calculation',
        description: 'Expose raw model fields for use in reports and other calculations',
        icon: 'bi-database',
        color: 'success'
      };
    case 'system-sql':
      return {
        title: 'System SQL Calculation',
        description: 'Advanced custom calculations using validated SQL queries',
        icon: 'bi-code-square',
        color: 'warning'
      };
    default:
      return {
        title: 'Calculation',
        description: '',
        icon: 'bi-question-circle',
        color: 'secondary'
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
 * Get SQL template based on group level
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