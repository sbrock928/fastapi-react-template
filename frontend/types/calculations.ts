// frontend/types/calculations.ts - Updated with raw field support
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
  category: 'aggregated' | 'raw'; // New: distinguish between aggregated and raw functions
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

export interface Calculation {
  id: number;
  name: string;
  description?: string;
  aggregation_function: string;
  source_model: string;
  source_field: string;
  group_level: string;
  weight_field?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CalculationForm {
  name: string;
  description: string;
  function_type: string;
  source: string;
  source_field: string;
  level: string;
  weight_field: string;
}

export interface PreviewData {
  calculation_name: string;
  aggregation_level: string;
  calculation_type: string; // New: "Raw Field" or "Aggregated Calculation"
  generated_sql: string;
  sample_parameters?: {
    deals?: string[];
    tranches?: string[];
    cycle?: string;
  };
}

export interface CalculationConfig {
  field_mappings: Record<string, CalculationField[]>;
  aggregation_functions: AggregationFunction[];
  source_models: SourceModel[];
  group_levels: GroupLevel[];
}

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

// Helper functions to work with raw vs aggregated calculations
export const isRawCalculation = (calculation: Calculation): boolean => {
  return calculation.aggregation_function === 'RAW';
};

export const isAggregatedCalculation = (calculation: Calculation): boolean => {
  return calculation.aggregation_function !== 'RAW';
};

export const getCalculationType = (calculation: Calculation): 'raw' | 'aggregated' => {
  return isRawCalculation(calculation) ? 'raw' : 'aggregated';
};

export const getCalculationDisplayType = (calculation: Calculation): string => {
  return isRawCalculation(calculation) ? 'Raw Field' : 'Aggregated Calculation';
};