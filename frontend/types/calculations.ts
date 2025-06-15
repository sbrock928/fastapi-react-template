// frontend/types/calculations.ts
// Updated types to match the new separated calculation system

export interface BaseCalculation {
  id: number;
  name: string;
  description?: string;
  group_level: 'deal' | 'tranche';
  created_by: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

// User-defined calculations (simple aggregations)
export interface UserCalculation extends BaseCalculation {
  calculation_type: 'USER_DEFINED';
  aggregation_function: AggregationFunction;
  source_model: SourceModel;
  source_field: string;
  weight_field?: string;
  advanced_config?: Record<string, any>;
}

// System calculations (custom SQL)
export interface SystemCalculation extends BaseCalculation {
  calculation_type: 'SYSTEM_SQL';
  raw_sql: string;
  result_column_name: string;
  metadata_config?: Record<string, any>;
  approved_by?: string;
  approval_date?: string;
}

// Static field information (no database storage)
export interface StaticFieldInfo {
  field_path: string; // e.g., "deal.dl_nbr", "tranche.tr_id"
  name: string;
  description: string;
  type: FieldType;
  required_models: string[];
  nullable: boolean;
}

// Union type for all calculation types
export type Calculation = UserCalculation | SystemCalculation;

// Enums matching backend
export enum AggregationFunction {
  SUM = 'SUM',
  AVG = 'AVG',
  COUNT = 'COUNT',
  MIN = 'MIN',
  MAX = 'MAX',
  WEIGHTED_AVG = 'WEIGHTED_AVG'
}

export enum SourceModel {
  DEAL = 'Deal',
  TRANCHE = 'Tranche',
  TRANCHE_BAL = 'TrancheBal'
}

export enum GroupLevel {
  DEAL = 'deal',
  TRANCHE = 'tranche'
}

export enum FieldType {
  STRING = 'string',
  NUMBER = 'number',
  CURRENCY = 'currency',
  PERCENTAGE = 'percentage',
  DATE = 'date',
  BOOLEAN = 'boolean'
}

// Configuration schemas
export interface CalculationField {
  value: string;
  label: string;
  type: FieldType;
  description: string;
  nullable: boolean;
}

export interface AggregationFunctionInfo {
  value: string;
  label: string;
  description: string;
  category: 'aggregated' | 'raw';
}

export interface SourceModelInfo {
  value: string;
  label: string;
  description: string;
}

export interface GroupLevelInfo {
  value: string;
  label: string;
  description: string;
}

export interface CalculationConfig {
  aggregation_functions: AggregationFunctionInfo[];
  source_models: SourceModelInfo[];
  group_levels: GroupLevelInfo[];
  static_fields: StaticFieldInfo[];
}

// API Request/Response schemas
export interface UserCalculationCreateRequest {
  name: string;
  description?: string;
  aggregation_function: AggregationFunction;
  source_model: SourceModel;
  source_field: string;
  weight_field?: string;
  group_level: 'deal' | 'tranche';
  advanced_config?: Record<string, any>;
}

export interface UserCalculationUpdateRequest {
  name?: string;
  description?: string;
  aggregation_function?: AggregationFunction;
  source_model?: SourceModel;
  source_field?: string;
  weight_field?: string;
  group_level?: 'deal' | 'tranche';
  advanced_config?: Record<string, any>;
}

export interface SystemCalculationCreateRequest {
  name: string;
  description?: string;
  raw_sql: string;
  result_column_name: string;
  group_level: 'deal' | 'tranche';
  metadata_config?: Record<string, any>;
}

export interface SystemCalculationUpdateRequest {
  name?: string;
  description?: string;
  raw_sql?: string;
  result_column_name?: string;
  group_level?: 'deal' | 'tranche';
  metadata_config?: Record<string, any>;
}

export interface SystemSqlValidationRequest {
  sql_text: string;
  group_level: 'deal' | 'tranche';
  result_column_name: string;
}

export interface SystemSqlValidationResult {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface SystemSqlValidationResponse {
  validation_result: SystemSqlValidationResult;
}

// Calculation usage information
export interface CalculationUsage {
  calculation_id: number | string; // UPDATED: Now supports both numeric (legacy) and string (new format)
  calculation_name: string;
  is_in_use: boolean;
  report_count: number;
  reports: {
    report_id: number;
    report_name: string;
    report_description?: string;
    scope: string;
    created_by: string;
    created_date: string;
    display_name?: string;
  }[];
}

// NEW: Available calculation interface for reporting (with new ID format)
export interface AvailableCalculation {
  id: string; // NOW ALWAYS STRING: "user.{source_field}", "system.{result_column}", "static_{table}.{field}"
  name: string;
  description?: string;
  aggregation_function?: string; // undefined for system calcs, 'RAW' for static fields
  source_model?: string; // undefined for system calcs and static fields
  source_field?: string; // field name for static fields, undefined for system calcs
  group_level: string;
  weight_field?: string;
  scope: 'DEAL' | 'TRANCE'; // FIXED: Use specific type instead of string
  category: string;
  is_default: boolean;
  calculation_type: 'USER_DEFINED' | 'SYSTEM_SQL' | 'STATIC_FIELD';
}

// SQL Preview
export interface PreviewData {
  // New API format (actual backend response)
  sql?: string;
  columns?: string[];
  calculation_type?: string;
  group_level?: string;
  parameters?: {
    deal_tranche_map?: Record<string, string[]>;
    cycle_code?: number;
  };
  
  // Legacy format (for backward compatibility)
  calculation_name?: string;
  aggregation_level?: string;
  generated_sql?: string;
  sample_parameters?: {
    deal_tranche_mapping?: Record<string, string[]>;
    cycle?: string;
  };
}

// Form state for calculation creation/editing
export interface CalculationForm {
  name: string;
  description: string;
  function_type: string; // Can be aggregation function or special types like 'SYSTEM_SQL'
  source: string; // Source model
  source_field: string; // For user calcs: field name, for system calcs: SQL text
  level: string; // Group level
  weight_field: string; // For weighted avg or system calcs: result column name
}

// Initial form state constant
export const INITIAL_CALCULATION_FORM: CalculationForm = {
  name: '',
  description: '',
  function_type: '',
  source: '',
  source_field: '',
  level: '',
  weight_field: ''
};

// Helper functions for type checking
export function isUserDefinedCalculation(calc: Calculation): calc is UserCalculation {
  return calc.calculation_type === 'USER_DEFINED';
}

export function isSystemSqlCalculation(calc: Calculation): calc is SystemCalculation {
  return calc.calculation_type === 'SYSTEM_SQL';
}

export function isSystemCalculation(calc: Calculation): boolean {
  return calc.calculation_type === 'SYSTEM_SQL';
}

// Helper functions for display
export function getCalculationDisplayType(calc: Calculation): string {
  if (isUserDefinedCalculation(calc)) {
    return `User Defined (${calc.aggregation_function})`;
  } else if (isSystemSqlCalculation(calc)) {
    return 'System SQL';
  }
  return 'Unknown';
}

export function getCalculationSourceDescription(calc: Calculation): string {
  if (isUserDefinedCalculation(calc)) {
    return `${calc.source_model}.${calc.source_field}`;
  } else if (isSystemSqlCalculation(calc)) {
    return `Custom SQL (${calc.result_column_name})`;
  }
  return 'Unknown';
}

export function getCalculationCategory(calc: Calculation): string {
  if (isUserDefinedCalculation(calc)) {
    const sourceModel = calc.source_model;
    if (sourceModel === SourceModel.DEAL) {
      return 'Deal Information';
    } else if (sourceModel === SourceModel.TRANCHE) {
      return 'Tranche Structure';
    } else if (sourceModel === SourceModel.TRANCHE_BAL) {
      return 'Balance & Performance';
    }
    return 'Other';
  } else if (isSystemSqlCalculation(calc)) {
    return 'Custom SQL Calculations';
  }
  return 'Other';
}

// Helper functions for type checking AvailableCalculation
export function isUserDefinedAvailableCalculation(calc: AvailableCalculation): boolean {
  return calc.calculation_type === 'USER_DEFINED' || calc.id.startsWith('user.');
}

export function isSystemSqlAvailableCalculation(calc: AvailableCalculation): boolean {
  return calc.calculation_type === 'SYSTEM_SQL' || calc.id.startsWith('system.');
}

export function isStaticFieldAvailableCalculation(calc: AvailableCalculation): boolean {
  return calc.calculation_type === 'STATIC_FIELD' || calc.id.startsWith('static_');
}

/**
 * Parse calculation ID to extract type and identifier
 * NEW utility function for the new format
 */
export const parseCalculationId = (calculationId: string): {
  type: 'user' | 'system' | 'static';
  identifier: string;
} => {
  if (calculationId.startsWith('user.')) {
    return {
      type: 'user',
      identifier: calculationId.substring(5) // Remove "user."
    };
  } else if (calculationId.startsWith('system.')) {
    return {
      type: 'system', 
      identifier: calculationId.substring(7) // Remove "system."
    };
  } else if (calculationId.startsWith('static_')) {
    return {
      type: 'static',
      identifier: calculationId.substring(7) // Remove "static_"
    };
  } else {
    console.warn(`Unknown calculation ID format: ${calculationId}`);
    return {
      type: 'user', // fallback
      identifier: calculationId
    };
  }
};

/**
 * Format calculation ID for display
 * NEW utility function
 */
export const formatCalculationIdForDisplay = (calculationId: string): string => {
  const parsed = parseCalculationId(calculationId);
  
  switch (parsed.type) {
    case 'user':
      return `User: ${parsed.identifier}`;
    case 'system':
      return `System: ${parsed.identifier}`;
    case 'static':
      return `Static: ${parsed.identifier}`;
    default:
      return calculationId;
  }
};