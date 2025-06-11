// frontend/services/calculationsApi.ts
// Updated API service to work with the new separated calculation system

import axios, { AxiosResponse } from 'axios';
import type {
  UserCalculation,
  SystemCalculation,
  StaticFieldInfo,
  CalculationConfig,
  UserCalculationCreateRequest,
  UserCalculationUpdateRequest,
  SystemCalculationCreateRequest,
  SystemSqlValidationRequest,
  SystemSqlValidationResponse,
  CalculationUsage,
  PreviewData
} from '@/types/calculations';

const API_BASE_URL = '/api';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const calculationsApi = {
  // ===== CONFIGURATION ENDPOINTS =====
  async getCalculationConfig(): Promise<AxiosResponse<{ data: CalculationConfig }>> {
    return apiClient.get('/calculations/config');
  },

  // ===== USER CALCULATION ENDPOINTS =====
  async getUserDefinedCalculations(groupLevel?: string): Promise<AxiosResponse<UserCalculation[]>> {
    const params = groupLevel ? { group_level: groupLevel } : {};
    return apiClient.get('/calculations/user', { params });
  },

  async getUserCalculationById(id: number): Promise<AxiosResponse<UserCalculation>> {
    return apiClient.get(`/calculations/user/${id}`);
  },

  async createCalculation(data: UserCalculationCreateRequest): Promise<AxiosResponse<UserCalculation>> {
    return apiClient.post('/calculations/user', data);
  },

  async updateCalculation(id: number, data: UserCalculationUpdateRequest): Promise<AxiosResponse<UserCalculation>> {
    return apiClient.put(`/calculations/user/${id}`, data);
  },

  async deleteCalculation(id: number): Promise<AxiosResponse<{ message: string }>> {
    return apiClient.delete(`/calculations/user/${id}`);
  },

  async getCalculationUsage(id: number): Promise<AxiosResponse<CalculationUsage>> {
    return apiClient.get(`/calculations/user/${id}/usage`);
  },

  // ===== SYSTEM CALCULATION ENDPOINTS =====
  async getSystemCalculations(groupLevel?: string, approvedOnly?: boolean): Promise<AxiosResponse<SystemCalculation[]>> {
    const params: Record<string, any> = {};
    if (groupLevel) params.group_level = groupLevel;
    if (approvedOnly) params.approved_only = approvedOnly;
    return apiClient.get('/calculations/system', { params });
  },

  async getSystemCalculationById(id: number): Promise<AxiosResponse<SystemCalculation>> {
    return apiClient.get(`/calculations/system/${id}`);
  },

  async createSystemSqlCalculation(data: SystemCalculationCreateRequest): Promise<AxiosResponse<SystemCalculation>> {
    return apiClient.post('/calculations/system', data);
  },

  async approveSystemCalculation(id: number, approvedBy: string): Promise<AxiosResponse<SystemCalculation>> {
    return apiClient.post(`/calculations/system/${id}/approve`, { approved_by: approvedBy });
  },

  async deleteSystemCalculation(id: number): Promise<AxiosResponse<{ message: string }>> {
    return apiClient.delete(`/calculations/system/${id}`);
  },

  async validateSystemSql(data: SystemSqlValidationRequest): Promise<AxiosResponse<SystemSqlValidationResponse>> {
    return apiClient.post('/calculations/validate-system-sql', data);
  },

  // ===== STATIC FIELD ENDPOINTS =====
  async getStaticFields(model?: string): Promise<AxiosResponse<StaticFieldInfo[]>> {
    const params = model ? { model } : {};
    return apiClient.get('/calculations/static-fields', { params });
  },

  async getStaticFieldByPath(fieldPath: string): Promise<AxiosResponse<StaticFieldInfo>> {
    return apiClient.get(`/calculations/static-fields/${encodeURIComponent(fieldPath)}`);
  },

  // ===== SQL PREVIEW ENDPOINTS =====
  async previewSQL(calculationId: number, sampleParams: any): Promise<AxiosResponse<PreviewData>> {
    // For individual calculation preview
    const requestData = {
      calculation_request: {
        calc_type: 'user_calculation', // This will be determined dynamically
        calc_id: calculationId
      },
      deal_tranche_map: sampleParams.deal_tranche_mapping || { 101: ['A', 'B'], 102: [], 103: [] },
      cycle_code: sampleParams.cycle || 202404
    };
    
    return apiClient.post('/calculations/preview-single', requestData);
  },

  async previewSystemSql(calculationId: number, sampleParams: any): Promise<AxiosResponse<PreviewData>> {
    // For system calculation preview
    const requestData = {
      calculation_request: {
        calc_type: 'system_calculation',
        calc_id: calculationId
      },
      deal_tranche_map: sampleParams.deal_tranche_mapping || { 101: ['A', 'B'], 102: [], 103: [] },
      cycle_code: sampleParams.cycle || 202404
    };
    
    return apiClient.post('/calculations/preview-single', requestData);
  },

  // ===== STATISTICS ENDPOINTS =====
  async getCalculationCounts(): Promise<AxiosResponse<any>> {
    return apiClient.get('/calculations/stats/counts');
  },

  // ===== HEALTH CHECK =====
  async getCalculationSystemHealth(): Promise<AxiosResponse<any>> {
    return apiClient.get('/calculations/health');
  },

  // ===== COMPATIBILITY METHODS (for gradual migration) =====
  // These methods help maintain compatibility with existing code that expects the old API format
  
  async getAvailableCalculations(scope: 'DEAL' | 'TRANCHE'): Promise<AxiosResponse<any[]>> {
    // This combines user calculations, system calculations, and static fields
    // to match the old AvailableCalculation format expected by reporting components
    try {
      const [userCalcs, systemCalcs, staticFields] = await Promise.all([
        this.getUserDefinedCalculations(scope.toLowerCase()),
        this.getSystemCalculations(scope.toLowerCase(), true), // Only approved system calcs
        this.getStaticFields()
      ]);

      const combined: any[] = [];

      // Add user calculations
      userCalcs.data.forEach(calc => {
        combined.push({
          id: calc.id,
          name: calc.name,
          description: calc.description,
          aggregation_function: calc.aggregation_function,
          source_model: calc.source_model,
          source_field: calc.source_field,
          group_level: calc.group_level,
          weight_field: calc.weight_field,
          scope: scope,
          category: this.categorizeCalculation(calc),
          is_default: this.isDefaultCalculation(calc.name),
          calculation_type: 'USER_DEFINED'
        });
      });

      // Add approved system calculations
      systemCalcs.data.forEach(calc => {
        if (calc.approved_by) { // Only include approved system calculations
          combined.push({
            id: calc.id,
            name: calc.name,
            description: calc.description,
            aggregation_function: null,
            source_model: null,
            source_field: null,
            group_level: calc.group_level,
            weight_field: null,
            scope: scope,
            category: 'Custom SQL Calculations',
            is_default: false,
            calculation_type: 'SYSTEM_SQL'
          });
        }
      });

      // Add static fields (filtered by scope)
      staticFields.data.forEach(field => {
        const fieldGroupLevel = this.determineFieldGroupLevel(field.field_path);
        const isCompatible = this.isStaticFieldCompatibleWithScope(field, scope);
        
        if (isCompatible) {
          combined.push({
            id: `static_${field.field_path}`,
            name: field.name,
            description: field.description,
            aggregation_function: 'RAW',
            source_model: null,
            source_field: field.field_path,
            group_level: fieldGroupLevel,
            weight_field: null,
            scope: scope,
            category: this.categorizeStaticField(field),
            is_default: this.isDefaultField(field.name),
            calculation_type: 'STATIC_FIELD'
          });
        }
      });

      return { data: combined } as AxiosResponse<any[]>;
    } catch (error) {
      console.error('Error combining calculations:', error);
      return { data: [] } as unknown as AxiosResponse<any[]>;
    }
  },

  // Helper methods for compatibility
  categorizeCalculation(calc: UserCalculation): string {
    if (calc.source_model === 'Deal') {
      return 'Deal Information';
    } else if (calc.source_model === 'Tranche') {
      return 'Tranche Structure';
    } else if (calc.source_model === 'TrancheBal') {
      if (calc.source_field.includes('bal') || calc.source_field.includes('amt')) {
        return 'Balance & Amount Calculations';
      } else if (calc.source_field.includes('rte')) {
        return 'Rate Calculations';
      } else {
        return 'Performance Calculations';
      }
    }
    return 'Other';
  },

  categorizeStaticField(field: StaticFieldInfo): string {
    if (field.field_path.startsWith('deal.')) {
      return 'Deal Information';
    } else if (field.field_path.startsWith('tranche.')) {
      return 'Tranche Structure';
    } else if (field.field_path.startsWith('tranchebal.')) {
      return 'Balance & Performance Data';
    }
    return 'Other';
  },

  isDefaultCalculation(name: string): boolean {
    return ['Total Ending Balance', 'Average Pass Through Rate'].includes(name);
  },

  isDefaultField(name: string): boolean {
    return ['Deal Number', 'Tranche ID'].includes(name);
  },

  determineFieldGroupLevel(fieldPath: string): string {
    if (fieldPath.startsWith('tranche.') || fieldPath.startsWith('tranchebal.')) {
      return 'tranche';
    }
    return 'deal';
  },

  isStaticFieldCompatibleWithScope(field: StaticFieldInfo, scope: 'DEAL' | 'TRANCHE'): boolean {
    const fieldGroupLevel = this.determineFieldGroupLevel(field.field_path);
    
    if (scope === 'DEAL') {
      // Deal-level reports can only include deal-level fields
      return fieldGroupLevel === 'deal';
    } else {
      // Tranche-level reports can include both deal and tranche level fields
      return true;
    }
  }
};

// Error handling wrapper
export const withErrorHandling = <T extends any[], R>(
  fn: (...args: T) => Promise<R>
) => {
  return async (...args: T): Promise<R> => {
    try {
      return await fn(...args);
    } catch (error: any) {
      console.error('API Error:', error);
      if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      } else if (error.response?.data?.message) {
        throw new Error(error.response.data.message);
      } else if (error.message) {
        throw new Error(error.message);
      } else {
        throw new Error('An unknown error occurred');
      }
    }
  };
};

// Export wrapped API for better error handling
export const safeCalculationsApi = {
  getCalculationConfig: withErrorHandling(calculationsApi.getCalculationConfig),
  getUserDefinedCalculations: withErrorHandling(calculationsApi.getUserDefinedCalculations),
  createCalculation: withErrorHandling(calculationsApi.createCalculation),
  updateCalculation: withErrorHandling(calculationsApi.updateCalculation),
  deleteCalculation: withErrorHandling(calculationsApi.deleteCalculation),
  getCalculationUsage: withErrorHandling(calculationsApi.getCalculationUsage),
  getSystemCalculations: withErrorHandling(calculationsApi.getSystemCalculations),
  createSystemSqlCalculation: withErrorHandling(calculationsApi.createSystemSqlCalculation),
  validateSystemSql: withErrorHandling(calculationsApi.validateSystemSql),
  getStaticFields: withErrorHandling(calculationsApi.getStaticFields),
  previewSQL: withErrorHandling(calculationsApi.previewSQL),
  getAvailableCalculations: withErrorHandling(calculationsApi.getAvailableCalculations),
};

export default calculationsApi;