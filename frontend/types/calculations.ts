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
  calculation_id: number;
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

// SQL Preview
export interface PreviewData {
  calculation_name: string;
  calculation_type: string;
  aggregation_level: string;
  generated_sql: string;
  sample_parameters: {
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