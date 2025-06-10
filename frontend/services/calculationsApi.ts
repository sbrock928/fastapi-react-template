// frontend/services/calculationsApi.ts
import apiClient from './apiClient';
import type {
  Calculation,
  CalculationConfig,
  CreateCalculationRequest,
  UpdateCalculationRequest,
  PreviewData
} from '@/types/calculations';

export const calculationsApi = {
  // ===== UNIFIED RETRIEVAL ENDPOINTS =====
  
  // Get all calculations (unified endpoint)
  getCalculations: async (
    group_level?: string,
    calculation_type?: string
  ) => {
    const params: any = {};
    if (group_level) params.group_level = group_level;
    if (calculation_type) params.calculation_type = calculation_type;
    
    return apiClient.get<Calculation[]>('/calculations', { params });
  },

  // Get user-defined calculations only
  getUserDefinedCalculations: async (group_level?: string) => {
    const params: any = {};
    if (group_level) params.group_level = group_level;
    
    return apiClient.get<Calculation[]>('/calculations/user-defined', { params });
  },

  // Get system calculations (both field and SQL types)
  getSystemCalculations: async (group_level?: string) => {
    const params: any = {};
    if (group_level) params.group_level = group_level;
    
    return apiClient.get<Calculation[]>('/calculations/system', { params });
  },

  // Get single calculation by ID
  getCalculationById: async (id: number) => {
    return apiClient.get<Calculation>(`/calculations/${id}`);
  },

  // ===== USER-DEFINED CALCULATION ENDPOINTS =====

  // Create new user-defined calculation
  createCalculation: async (data: CreateCalculationRequest) => {
    return apiClient.post<Calculation>('/calculations/user-defined', data);
  },

  // Update existing user-defined calculation
  updateCalculation: async (id: number, data: UpdateCalculationRequest) => {
    return apiClient.put<Calculation>(`/calculations/user-defined/${id}`, data);
  },

  // ===== SYSTEM FIELD CALCULATION ENDPOINTS =====

  // Create system field calculation
  createSystemFieldCalculation: async (data: {
    name: string;
    description?: string;
    source_model: string;
    field_name: string;
    field_type: string;
    group_level: string;
  }) => {
    return apiClient.post<Calculation>('/calculations/system-field', data);
  },

  // Auto-generate system field calculations
  autoGenerateSystemFields: async () => {
    return apiClient.post<{
      success: boolean;
      message: string;
      details: {
        generated_count: number;
        skipped_count: number;
        errors: string[];
      };
    }>('/calculations/system-field/auto-generate');
  },

  // ===== SYSTEM SQL CALCULATION ENDPOINTS =====

  // Create system SQL calculation
  createSystemSqlCalculation: async (data: {
    name: string;
    description?: string;
    group_level: string;
    raw_sql: string;
    result_column_name: string;
  }) => {
    return apiClient.post<Calculation>('/calculations/system-sql', data);
  },

  // Validate system SQL without saving
  validateSystemSql: async (data: {
    sql_text: string;
    group_level: string;
    result_column_name: string;
  }) => {
    return apiClient.post<{
      success: boolean;
      validation_result: {
        is_valid: boolean;
        errors: string[];
        warnings: string[];
        extracted_columns: string[];
        detected_tables: string[];
        result_column_name: string;
      };
    }>('/calculations/system-sql/validate', data);
  },

  // ===== CONFIGURATION ENDPOINTS =====

  // Get calculation configuration (field mappings, functions, etc.)
  getCalculationConfig: async () => {
    return apiClient.get<{ 
      success: boolean;
      data: CalculationConfig;
      message: string;
    }>('/calculations/configuration');
  },

  // ===== PREVIEW AND USAGE ENDPOINTS =====

  // Preview SQL for calculation
  previewSQL: async (
    id: number,
    params: {
      aggregation_level?: string;
      sample_deals?: string;
      sample_tranches?: string;
      sample_cycle?: string;
    } = {}
  ) => {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value) searchParams.append(key, value);
    });
    
    const url = `/calculations/${id}/preview-sql${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
    return apiClient.get<PreviewData>(url);
  },

  // Get calculation usage in report templates
  getCalculationUsage: async (id: number) => {
    return apiClient.get<{
      calculation_id: number;
      is_in_use: boolean;
      report_count: number;
      reports: Array<{
        report_id: number;
        report_name: string;
        report_description?: string;
        scope: string;
        created_by: string;
        created_date?: string;
        display_order: number;
        display_name?: string;
      }>;
    }>(`/calculations/${id}/usage`);
  },

  // ===== DELETE ENDPOINT =====

  // Delete calculation (only user-defined calculations can be deleted)
  deleteCalculation: async (id: number) => {
    return apiClient.delete<{ message: string }>(`/calculations/${id}`);
  },

  // ===== STATISTICS ENDPOINTS =====

  // Get calculation counts by type
  getCalculationCounts: async () => {
    return apiClient.get<{
      success: boolean;
      counts: Record<string, number>;
      total: number;
    }>('/calculations/stats/counts');
  },

  // ===== DEBUG ENDPOINTS (DEVELOPMENT) =====

  // Get model fields for debugging
  getModelFields: async (modelName: string) => {
    return apiClient.get<{
      model_name: string;
      all_available_fields: string[];
      currently_exposed_fields: string[];
      unexposed_fields: string[];
    }>(`/calculations/debug/model-fields/${modelName}`);
  }
};