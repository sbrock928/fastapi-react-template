// frontend/types/cdi.ts
// TypeScript interfaces for CDI Variable calculations

export interface CDIVariableBase {
    name: string;
    description?: string;
    variable_pattern: string;
    variable_type: string;
    result_column_name: string;
    tranche_mappings: Record<string, string[]>;
  }
  
  export interface CDIVariableCreate extends CDIVariableBase {}
  
  export interface CDIVariableUpdate {
    name?: string;
    description?: string;
    variable_pattern?: string;
    variable_type?: string;
    result_column_name?: string;
    tranche_mappings?: Record<string, string[]>;
  }
  
  export interface CDIVariableResponse extends CDIVariableBase {
    id: number;
    created_by: string;
    created_at: string;
    is_active: boolean;
  }
  
  export interface CDIVariableSummary {
    id: number;
    name: string;
    variable_type: string;
    result_column_name: string;
    tranche_count: number;
    created_by: string;
    created_at: string;
    is_active: boolean;
  }
  
  export interface CDIVariableConfig {
    available_patterns: string[];
    default_tranche_mappings: Record<string, string[]>;
    variable_types: string[];
  }
  
  export interface CDIVariableValidationRequest {
    variable_pattern: string;
    tranche_mappings: Record<string, string[]>;
    cycle_code: number;
    sample_deal_numbers: number[];
  }
  
  export interface CDIVariableValidationResponse {
    is_valid: boolean;
    validation_results: {
      valid_mappings: Record<string, string[]>;
      invalid_mappings: Record<string, string[]>;
      missing_tranches: string[];
      available_tranches: string[];
    };
    warnings: string[];
    errors: string[];
  }
  
  export interface CDIVariableExecutionRequest {
    calculation_id: number;
    cycle_code: number;
    deal_numbers: number[];
  }
  
  export interface CDIVariableExecutionResponse {
    calculation_id: number;
    calculation_name: string;
    cycle_code: number;
    deal_count: number;
    tranche_count: number;
    data: Array<Record<string, any>>;
    execution_time_ms?: number;
  }
  
  // Form interfaces for the UI
  export interface CDIVariableForm extends CDIVariableBase {
    id?: number;
  }
  
  export const INITIAL_CDI_FORM: CDIVariableForm = {
    name: '',
    description: '',
    variable_pattern: '',
    variable_type: '',
    result_column_name: '',
    tranche_mappings: {}
  };
  
  // Helper types
  export type CDIVariableType = 
    | 'investment_income'
    | 'excess_interest'
    | 'fees'
    | 'principal'
    | 'interest'
    | 'other';
  
  export const CDI_VARIABLE_TYPE_OPTIONS: Array<{value: CDIVariableType; label: string}> = [
    { value: 'investment_income', label: 'Investment Income' },
    { value: 'excess_interest', label: 'Excess Interest' },
    { value: 'fees', label: 'Fees' },
    { value: 'principal', label: 'Principal' },
    { value: 'interest', label: 'Interest' },
    { value: 'other', label: 'Other' }
  ];
  
  // Helper functions
  export function createCDIVariableRequest(form: CDIVariableForm): CDIVariableCreate {
    return {
      name: form.name,
      description: form.description,
      variable_pattern: form.variable_pattern,
      variable_type: form.variable_type,
      result_column_name: form.result_column_name,
      tranche_mappings: form.tranche_mappings
    };
  }
  
  export function populateCDIFormFromResponse(response: CDIVariableResponse): CDIVariableForm {
    return {
      id: response.id,
      name: response.name,
      description: response.description || '',
      variable_pattern: response.variable_pattern,
      variable_type: response.variable_type,
      result_column_name: response.result_column_name,
      tranche_mappings: response.tranche_mappings
    };
  }