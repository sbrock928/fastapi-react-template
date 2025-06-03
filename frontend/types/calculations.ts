// Calculation-specific types
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