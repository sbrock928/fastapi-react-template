// frontend/services/calculationsApi.ts
// Updated API service to work with the new separated calculation system

import apiClient from './apiClient';
import type { AxiosResponse } from 'axios';
import type {
  UserCalculation,
  SystemCalculation,
  StaticFieldInfo,
  CalculationConfig,
  UserCalculationCreateRequest,
  UserCalculationUpdateRequest,
  SystemCalculationCreateRequest,
  SystemCalculationUpdateRequest,
  SystemSqlValidationRequest,
  SystemSqlValidationResponse,
  CalculationUsage
} from '@/types/calculations';
import type {
  CDIVariableCreate,
  CDIVariableUpdate,
  CDIVariableResponse,
  CDIVariableSummary,
  CDIVariableConfig,
  CDIVariableValidationRequest,
  CDIVariableValidationResponse,
  CDIVariableExecutionRequest,
  CDIVariableExecutionResponse
} from '@/types/cdi';
import { parseCalculationId } from '@/types/calculations';

// Add the PreviewData type for individual calculation previews
type PreviewData = {
  sql: string;
  columns: string[];
  calculation_type: string;
  group_level: string;
  parameters: any;
};

// Updated to handle string-based calculation IDs
export const calculationsApi = {
  // ===== CONFIGURATION ENDPOINTS =====
  async getCalculationConfig(): Promise<AxiosResponse<{ data: CalculationConfig }>> {
    return apiClient.get('/calculations/config');
  },

  // ===== USER CALCULATION ENDPOINTS =====
  async getUserCalculationById(id: number): Promise<AxiosResponse<UserCalculation>> {
    return apiClient.get(`/calculations/user/${id}`);
  },

  async createCalculation(data: UserCalculationCreateRequest): Promise<AxiosResponse<UserCalculation>> {
    return apiClient.post('/calculations/user', data);
  },

  async updateCalculation(id: number, data: UserCalculationUpdateRequest): Promise<AxiosResponse<UserCalculation>> {
    return apiClient.patch(`/calculations/user/${id}`, data);
  },

  async deleteCalculation(id: number): Promise<AxiosResponse<{ message: string }>> {
    return apiClient.delete(`/calculations/user/${id}`);
  },

  async getUserCalculationUsage(id: number, reportScope?: string): Promise<AxiosResponse<CalculationUsage>> {
    const params = reportScope ? { report_scope: reportScope } : {};
    return apiClient.get(`/calculations/user/${id}/usage`, { params });
  },

  // ===== UNIFIED CALCULATION USAGE ENDPOINT =====
  async getCalculationUsageByType(id: number, calcType: 'user' | 'system'): Promise<AxiosResponse<CalculationUsage>> {
    return apiClient.get(`/calculations/${id}/usage`, {
      params: { calc_type: calcType }
    });
  },

  // ===== SYSTEM CALCULATION ENDPOINTS =====
  async getSystemCalculationById(id: number): Promise<AxiosResponse<SystemCalculation>> {
    return apiClient.get(`/calculations/system/${id}`);
  },

  async createSystemSqlCalculation(data: SystemCalculationCreateRequest): Promise<AxiosResponse<SystemCalculation>> {
    return apiClient.post('/calculations/system', data);
  },

  async updateSystemCalculation(id: number, data: SystemCalculationUpdateRequest): Promise<AxiosResponse<SystemCalculation>> {
    return apiClient.patch(`/calculations/system/${id}`, data);
  },

  async approveSystemCalculation(id: number, approvedBy: string): Promise<AxiosResponse<SystemCalculation>> {
    return apiClient.post(`/calculations/system/${id}/approve`, { approved_by: approvedBy });
  },

  async deleteSystemCalculation(id: number): Promise<AxiosResponse<{ message: string }>> {
    return apiClient.delete(`/calculations/system/${id}`);
  },

  async getSystemCalculationUsage(id: number, reportScope?: string): Promise<AxiosResponse<CalculationUsage>> {
    const params = reportScope ? { report_scope: reportScope } : {};
    return apiClient.get(`/calculations/system/${id}/usage`, { params });
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
    // Default to user calculation for backward compatibility
    const requestData = {
      calculation_request: {
        calc_type: 'user_calculation',
        calc_id: calculationId
      },
      deal_tranche_map: sampleParams.deal_tranche_mapping || { 101: ['A', 'B'], 102: [], 103: [] },
      cycle_code: sampleParams.cycle || 202404
    };
    
    return apiClient.post('/calculations/preview-single', requestData);
  },

  async previewUserSQL(calculationId: number, sampleParams: any): Promise<AxiosResponse<PreviewData>> {
    const requestData = {
      calculation_request: {
        calc_type: 'user_calculation',
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
      // Use the new unified endpoint instead of separate calls
      const unifiedResponse = await this.getAllCalculations(scope.toLowerCase());
      const staticFieldsResponse = await this.getStaticFields();

      const combined: any[] = [];

      // Add user calculations
      unifiedResponse.data.user_calculations.forEach(calc => {
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
      unifiedResponse.data.system_calculations.forEach(calc => {
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
      staticFieldsResponse.data.forEach(field => {
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

  // ===== UNIFIED CALCULATIONS ENDPOINT =====
  async getAllCalculations(groupLevel?: string): Promise<AxiosResponse<{
    user_calculations: UserCalculation[];
    system_calculations: SystemCalculation[];
    summary: {
      total_calculations: number;
      user_calculation_count: number;
      system_calculation_count: number;
      user_in_use_count: number;
      system_in_use_count: number;
      total_in_use: number;
      group_level_filter?: string;
    };
  }>> {
    const params = groupLevel ? { group_level: groupLevel } : {};
    return apiClient.get('/calculations', { params });
  },

  // User calculations - these methods now need to handle lookup by source_field
  async getUserCalculationBySourceField(sourceField: string): Promise<AxiosResponse<UserCalculation>> {
    return apiClient.get(`/calculations/user/by-source-field/${encodeURIComponent(sourceField)}`);
  },

  // System calculations - these methods now need to handle lookup by result_column
  async getSystemCalculationByResultColumn(resultColumn: string): Promise<AxiosResponse<SystemCalculation>> {
    return apiClient.get(`/calculations/system/by-result-column/${encodeURIComponent(resultColumn)}`);
  },

  // Updated usage endpoints to handle string IDs
  async getCalculationUsageByCalculationId(calculationId: string): Promise<AxiosResponse<CalculationUsage>> {
    const parsed = parseCalculationId(calculationId);
    
    if (parsed.type === 'static') {
      // Static fields don't have usage tracking - create a proper mock AxiosResponse
      return Promise.resolve({
        data: {
          calculation_id: calculationId,
          calculation_name: parsed.identifier,
          is_in_use: false,
          report_count: 0,
          reports: []
        },
        status: 200,
        statusText: 'OK',
        headers: {},
        config: {
          headers: {} as any
        }
      } as AxiosResponse<CalculationUsage>);
    }
    
    // For user and system calculations, use the new endpoint that handles string IDs
    return apiClient.get(`/calculations/usage/${encodeURIComponent(calculationId)}`);
  },

  // NEW: Validation endpoints for new formats
  async validateUserCalculationSourceField(sourceField: string): Promise<AxiosResponse<{ is_available: boolean; existing_calculation?: string }>> {
    return apiClient.post('/calculations/user/validate-source-field', { source_field: sourceField });
  },

  async validateSystemCalculationResultColumn(resultColumn: string): Promise<AxiosResponse<{ is_available: boolean; existing_calculation?: string }>> {
    return apiClient.post('/calculations/system/validate-result-column', { result_column: resultColumn });
  },

  // Legacy method - updated to handle both formats for backward compatibility
  async getCalculationUsage(calcId: number | string): Promise<AxiosResponse<CalculationUsage>> {
    if (typeof calcId === 'string') {
      return this.getCalculationUsageByCalculationId(calcId);
    } else {
      // Legacy numeric ID - determine type and convert to new format
      // We'll need to try both user and system endpoints
      try {
        const userCalc = await this.getUserCalculationById(calcId);
        const newId = `user.${userCalc.data.source_field}`;
        return this.getCalculationUsageByCalculationId(newId);
      } catch {
        try {
          const systemCalc = await this.getSystemCalculationById(calcId);
          const newId = `system.${systemCalc.data.result_column_name}`;
          return this.getCalculationUsageByCalculationId(newId);
        } catch {
          throw new Error(`Could not find calculation with ID: ${calcId}`);
        }
      }
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
    return scope === 'TRANCHE' || fieldGroupLevel === 'deal';
  }
};

// ===== CDI VARIABLE API =====
export const cdiVariableApi = {
  // ===== CDI CONFIGURATION =====
  async getCDIConfig(): Promise<AxiosResponse<CDIVariableConfig>> {
    return apiClient.get('/calculations/cdi-variables/config');
  },

  // ===== CDI VARIABLE CRUD =====
  async getAllCDIVariables(): Promise<AxiosResponse<CDIVariableResponse[]>> {
    return apiClient.get('/calculations/cdi-variables');
  },

  async getCDIVariablesSummary(): Promise<AxiosResponse<CDIVariableSummary[]>> {
    return apiClient.get('/calculations/cdi-variables/summary');
  },

  async getCDIVariableById(id: number): Promise<AxiosResponse<CDIVariableResponse>> {
    return apiClient.get(`/calculations/cdi-variables/${id}`);
  },

  async createCDIVariable(data: CDIVariableCreate): Promise<AxiosResponse<CDIVariableResponse>> {
    return apiClient.post('/calculations/cdi-variables', data);
  },

  async updateCDIVariable(id: number, data: CDIVariableUpdate): Promise<AxiosResponse<CDIVariableResponse>> {
    return apiClient.patch(`/calculations/cdi-variables/${id}`, data);
  },

  async deleteCDIVariable(id: number): Promise<AxiosResponse<{message: string}>> {
    return apiClient.delete(`/calculations/cdi-variables/${id}`);
  },

  // ===== CDI VALIDATION =====
  async validateCDIVariable(data: CDIVariableValidationRequest): Promise<AxiosResponse<CDIVariableValidationResponse>> {
    return apiClient.post('/calculations/cdi-variables/validate', data);
  },

  // ===== CDI EXECUTION =====
  async executeCDIVariable(data: CDIVariableExecutionRequest): Promise<AxiosResponse<CDIVariableExecutionResponse>> {
    return apiClient.post('/calculations/cdi-variables/execute', data);
  },

  // ===== VALIDATION HELPERS =====
  async validateResultColumn(resultColumn: string): Promise<AxiosResponse<{
    result_column: string;
    is_available: boolean;
    existing_calculation?: string;
  }>> {
    return apiClient.post('/calculations/system/validate-result-column', {
      result_column: resultColumn
    });
  }
};

// Updated calculationsApi export with CDI methods included
export const calculationsApiWithCDI = {
  ...calculationsApi,
  cdi: cdiVariableApi
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
  createCalculation: withErrorHandling(calculationsApi.createCalculation),
  updateCalculation: withErrorHandling(calculationsApi.updateCalculation),
  deleteCalculation: withErrorHandling(calculationsApi.deleteCalculation),
  getCalculationUsage: withErrorHandling(calculationsApi.getCalculationUsage),
  getCalculationUsageByType: withErrorHandling(calculationsApi.getCalculationUsageByType),
  getUserCalculationUsage: withErrorHandling(calculationsApi.getUserCalculationUsage),
  getSystemCalculationUsage: withErrorHandling(calculationsApi.getSystemCalculationUsage),
  createSystemSqlCalculation: withErrorHandling(calculationsApi.createSystemSqlCalculation),
  updateSystemCalculation: withErrorHandling(calculationsApi.updateSystemCalculation),
  validateSystemSql: withErrorHandling(calculationsApi.validateSystemSql),
  getStaticFields: withErrorHandling(calculationsApi.getStaticFields),
  getAvailableCalculations: withErrorHandling(calculationsApi.getAvailableCalculations),
  getAllCalculations: withErrorHandling(calculationsApi.getAllCalculations),
  // CDI methods
  getCDIConfig: withErrorHandling(cdiVariableApi.getCDIConfig),
  createCDIVariable: withErrorHandling(cdiVariableApi.createCDIVariable),
  updateCDIVariable: withErrorHandling(cdiVariableApi.updateCDIVariable),
  deleteCDIVariable: withErrorHandling(cdiVariableApi.deleteCDIVariable),
  validateCDIVariable: withErrorHandling(cdiVariableApi.validateCDIVariable),
  executeCDIVariable: withErrorHandling(cdiVariableApi.executeCDIVariable),
};

export default calculationsApi;