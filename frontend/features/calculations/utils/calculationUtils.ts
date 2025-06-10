import type { CalculationField, CalculationForm } from '@/types/calculations';

/**
 * Generate preview formula for calculation
 */
export const getPreviewFormula = (calculation: CalculationForm): string => {
  if (!calculation.function_type || !calculation.source_field) {
    return 'Select aggregation function and field to see preview';
  }

  const field = `${calculation.source}.${calculation.source_field}`;
  
  if (calculation.function_type === 'WEIGHTED_AVG') {
    const weightField = calculation.weight_field ? `${calculation.source}.${calculation.weight_field}` : '[weight_field]';
    return `SUM(${field} * ${weightField}) / NULLIF(SUM(${weightField}), 0)`;
  }
  
  return `${calculation.function_type}(${field})`;
};

/**
 * Get scope compatibility warning for calculation
 */
export const getScopeCompatibilityWarning = (calculation: CalculationForm): string | null => {
  if (!calculation.function_type || !calculation.source || !calculation.source_field || !calculation.level) {
    return null;
  }

  // Check for potential compatibility issues
  if (calculation.function_type === 'RAW') {
    if (calculation.level === 'deal' && calculation.source !== 'Deal') {
      return `Warning: Raw ${calculation.source} fields in deal-level reports will create multiple rows per deal. Consider using an aggregated function instead.`;
    }
  }

  // Check for tranche-level calculations that might be problematic in deal reports
  if (calculation.level === 'tranche' && calculation.source === 'Tranche') {
    return `Note: This tranche-level calculation will only be suitable for tranche-level reports. It cannot be used in deal-level reports.`;
  }

  return null;
};

/**
 * Get recommended level based on calculation configuration
 */
export const getRecommendedLevel = (calculation: CalculationForm): string | null => {
  if (!calculation.function_type || !calculation.source) {
    return null;
  }

  // Provide intelligent recommendations based on source and function
  if (calculation.function_type === 'RAW') {
    if (calculation.source === 'Deal') {
      return 'deal'; // Raw deal fields work at both levels, but deal is more natural
    } else if (calculation.source === 'Tranche' || calculation.source === 'TrancheBal') {
      return 'tranche'; // Raw tranche fields should typically be tranche-level
    }
  } else {
    // For aggregated functions, consider the typical use case
    if (calculation.source === 'Deal') {
      return 'deal'; // Deal fields typically aggregate at deal level
    } else if (calculation.source === 'TrancheBal') {
      // TrancheBal can aggregate at either level depending on use case
      return calculation.level || 'deal'; // Default to deal for most financial calculations
    }
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
 * Validate calculation form
 */
export const validateCalculationForm = (calculation: CalculationForm): string | null => {
  if (!calculation.name || !calculation.function_type || !calculation.source || !calculation.source_field) {
    return 'Please fill in all required fields (Name, Function Type, Source, and Source Field)';
  }

  if (calculation.function_type === 'WEIGHTED_AVG' && !calculation.weight_field) {
    return 'Weight field is required for weighted average calculations';
  }

  return null;
};