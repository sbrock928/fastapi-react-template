// frontend/types/calculations.ts - Updated with system calculation types
export interface CalculationField {
  value: string;
  label: string;
  type: 'string' | 'number' | 'currency' | 'percentage';
  description?: string;
}

export interface AggregationFunction {
  value: string;
  label: string;
  description: string;
  category: 'aggregated'; // Removed 'raw' category since RAW is now SYSTEM_FIELD
}

export interface SourceModel {
  value: string;
  label: string;
  description: string;
}

export interface GroupLevel {
  value: string;
  label: string;
  description: string;
}

// Enhanced calculation interface with system types
export interface Calculation {
  id: number;
  name: string;
  description?: string;
  
  // Core calculation type
  calculation_type: 'USER_DEFINED' | 'SYSTEM_FIELD' | 'SYSTEM_SQL';
  group_level: string;
  is_system_managed: boolean;
  
  // New API format properties
  category?: string;
  is_default?: boolean;
  display_type?: string;
  source_description?: string;
  
  // Legacy properties (may still exist for backward compatibility)
  aggregation_function?: string;
  source_model?: string;
  source_field?: string;
  weight_field?: string;
  field_name?: string;
  field_type?: string;
  raw_sql?: string;
  result_column_name?: string;
  
  // Metadata
  created_at?: string;
  updated_at?: string;
  created_by?: string;
  is_active?: boolean;
}

export interface CalculationForm {
  name: string;
  description: string;
  function_type: string; // For user-defined: aggregation function, for system: calculation type
  source: string; // Source model for user-defined and system-field
  source_field: string; // Field name for system-field, SQL text for system-sql
  level: string; // Group level
  weight_field: string; // Weight field for user-defined, result column for system-sql
}

export interface PreviewData {
  calculation_name: string;
  aggregation_level: string;
  calculation_type: string; // "User Defined (SUM)", "System Field", "System SQL"
  generated_sql: string;
  sample_parameters?: {
    deals?: string[];
    tranches?: string[];
    cycle?: string;
    deal_tranche_mapping?: Record<string, string[]>; // Add the missing property
  };
}

export interface CalculationConfig {
  field_mappings: Record<string, CalculationField[]>;
  aggregation_functions: AggregationFunction[];
  source_models: SourceModel[];
  group_levels: GroupLevel[];
}

// User-defined calculation request (unchanged)
export interface CreateCalculationRequest {
  name: string;
  description?: string;
  aggregation_function: string;
  source_model: string;
  source_field: string;
  group_level: string;
  weight_field?: string | null;
}

export interface UpdateCalculationRequest extends CreateCalculationRequest {
  id: number;
}

// System SQL calculation request
export interface CreateSystemSqlRequest {
  name: string;
  description?: string;
  group_level: string;
  raw_sql: string;
  result_column_name: string;
}

// SQL validation request and response
export interface SqlValidationRequest {
  sql_text: string;
  group_level: string;
  result_column_name: string;
}

export interface SqlValidationResult {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  extracted_columns: string[];
  detected_tables: string[];
  result_column_name: string;
}

// Helper functions for calculation types
export const isUserDefinedCalculation = (calculation: Calculation): boolean => {
  return calculation.calculation_type === 'USER_DEFINED';
};

export const isSystemSqlCalculation = (calculation: Calculation): boolean => {
  return calculation.calculation_type === 'SYSTEM_SQL';
};

export const isSystemCalculation = (calculation: Calculation): boolean => {
  return calculation.is_system_managed || 
         calculation.calculation_type === 'SYSTEM_SQL';
};

export const getCalculationDisplayType = (calculation: Calculation): string => {
  // Use the new display_type property if available, otherwise fall back to old logic
  if (calculation.display_type) {
    return calculation.display_type;
  }
  
  // Fallback for backward compatibility
  switch (calculation.calculation_type) {
    case 'USER_DEFINED':
      return `User Defined (${calculation.aggregation_function || 'Unknown'})`;
    case 'SYSTEM_FIELD':
      return `System Field (${calculation.field_type || 'Unknown'})`;
    case 'SYSTEM_SQL':
      return 'System SQL';
    default:
      return 'Unknown';
  }
};

export const getCalculationSourceDescription = (calculation: Calculation): string => {
  // Use the new source_description property if available, otherwise fall back to old logic
  if (calculation.source_description) {
    return calculation.source_description;
  }
  
  // Fallback for backward compatibility
  switch (calculation.calculation_type) {
    case 'USER_DEFINED':
      return `${calculation.source_model || 'Unknown'}.${calculation.source_field || 'Unknown'}`;
    case 'SYSTEM_FIELD':
      return `${calculation.source_model || 'Unknown'}.${calculation.field_name || 'Unknown'}`;
    case 'SYSTEM_SQL':
      return `Custom SQL (${calculation.result_column_name || 'Unknown'})`;
    default:
      return 'Unknown source';
  }
};

export const getCalculationCategory = (calculation: Calculation): string => {
  // Use the new category property if available, otherwise fall back to old logic
  if (calculation.category) {
    return calculation.category;
  }
  
  // Fallback for backward compatibility
  if (calculation.calculation_type === 'USER_DEFINED') {
    const sourceModel = calculation.source_model;
    if (sourceModel === 'Deal') {
      return 'Deal Information';
    } else if (sourceModel === 'Tranche') {
      return 'Tranche Structure';
    } else if (sourceModel === 'TrancheBal') {
      if (calculation.source_field?.includes('bal') || calculation.source_field?.includes('amt')) {
        return 'Balance & Amount Calculations';
      } else if (calculation.source_field?.includes('rte')) {
        return 'Rate Calculations';
      } else if (calculation.source_field?.includes('dstrb')) {
        return 'Distribution Calculations';
      } else {
        return 'Performance Calculations';
      }
    }
  } else if (calculation.calculation_type === 'SYSTEM_FIELD') {
    const sourceModel = calculation.source_model;
    if (sourceModel === 'Deal') {
      return 'Deal Fields';
    } else if (sourceModel === 'Tranche') {
      return 'Tranche Fields';
    } else if (sourceModel === 'TrancheBal') {
      return 'Tranche Balance Fields';
    }
  } else if (calculation.calculation_type === 'SYSTEM_SQL') {
    return 'Custom SQL Calculations';
  }
  
  return 'Other';
};

// Enhanced form validation
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
      break;
  }

  return null;
};