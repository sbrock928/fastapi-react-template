import apiClient from './apiClient';
import type {
  Calculation,
  CalculationConfig,
  CreateCalculationRequest,
  UpdateCalculationRequest,
  PreviewData
} from '@/types/calculations';

export const calculationsApi = {
  // Get all calculations
  getCalculations: async () => {
    return apiClient.get<Calculation[]>('/calculations');
  },

  // Get calculation configuration (field mappings, functions, etc.)
  getCalculationConfig: async () => {
    return apiClient.get<{ data: CalculationConfig }>('/calculations/configuration');
  },

  // Create new calculation
  createCalculation: async (data: CreateCalculationRequest) => {
    return apiClient.post<Calculation>('/calculations', data);
  },

  // Update existing calculation
  updateCalculation: async (id: number, data: UpdateCalculationRequest) => {
    return apiClient.put<Calculation>(`/calculations/${id}`, data);
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

  // Delete calculation
  deleteCalculation: async (id: number) => {
    return apiClient.delete(`/calculations/${id}`);
  },

  // Preview SQL for calculation
  previewSQL: async (
    id: number,
    params: {
      group_level?: string;
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
  }
};