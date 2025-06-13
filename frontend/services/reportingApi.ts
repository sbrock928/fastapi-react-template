import apiClient from './apiClient';
import type { 
  ReportRow, 
  Deal, 
  TrancheReportSummary, 
  ReportConfig, 
  ReportSummary, 
  RunReportRequest,
  AvailableCalculation,
  ReportColumnPreferences
} from '@/types/reporting';

// Reporting API service - Updated for calculation-based reporting with column management
const reportingApi = {
  // ===== DEAL & TRANCHE DATA ENDPOINTS =====
  
  // Get available issuer codes for filtering
  getIssuerCodes: (): Promise<{ data: string[] }> => {
    return apiClient.get('/reports/data/issuer-codes');
  },

  // Get available deals for report building
  getDeals: (issuerCode?: string, cycleCode?: number): Promise<{ data: Deal[] }> => {
    const params: any = {};
    if (issuerCode) params.issuer_code = issuerCode;
    if (cycleCode) params.cycle_code = cycleCode;
    return apiClient.get('/reports/data/deals', { params });
  },

  // Get tranches for specific deals
  getTranches: (dlNbrs: number[], cycleCode?: number): Promise<{ data: Record<number, TrancheReportSummary[]> }> => {
    return apiClient.post('/reports/data/tranches', {
      dl_nbrs: dlNbrs,
      cycle_code: cycleCode
    });
  },

  // Get tranches for a single deal
  getDealTranches: (dlNbr: number, cycleCode?: number): Promise<{ data: TrancheReportSummary[] }> => {
    const params = cycleCode ? { cycle_code: cycleCode } : {};
    return apiClient.get(`/reports/data/deals/${dlNbr}/tranches`, { params });
  },

  // ===== REPORT CONFIGURATION ENDPOINTS =====

  // Get all report configurations
  getAllReports: (): Promise<{ data: ReportConfig[] }> => {
    return apiClient.get('/reports/');
  },

  // Get all reports with summary info
  getReportsSummary: (): Promise<{ data: ReportSummary[] }> => {
    return apiClient.get('/reports/summary');
  },

  // Get specific report configuration
  getReport: (reportId: number): Promise<{ data: ReportConfig }> => {
    return apiClient.get(`/reports/${reportId}`);
  },

  // Create new report configuration with column preferences
  createReport: (reportData: Omit<ReportConfig, 'id' | 'created_date' | 'updated_date'>): Promise<{ data: ReportConfig }> => {
    return apiClient.post('/reports/', reportData);
  },

  // Update report configuration with column preferences
  updateReport: (reportId: number, reportData: Partial<ReportConfig>): Promise<{ data: ReportConfig }> => {
    return apiClient.patch(`/reports/${reportId}`, reportData);
  },

  // Delete report configuration
  deleteReport: (reportId: number): Promise<{ data: { message: string } }> => {
    return apiClient.delete(`/reports/${reportId}`);
  },

  // ===== REPORT EXECUTION ENDPOINTS =====

  // Run a saved report configuration (returns formatted data based on column preferences)
  runSavedReport: (request: RunReportRequest): Promise<{ data: ReportRow[] }> => {
    return apiClient.post('/reports/run', request);
  },

  // Run report by ID with cycle parameter (returns formatted data with column metadata)
  runReportById: (reportId: number, cycleCode: number): Promise<{ 
    data: { 
      data: ReportRow[]; 
      columns: Array<{
        field: string;
        header: string;
        format_type: string;
        display_order: number;
      }>;
      total_rows: number;
    } 
  }> => {
    return apiClient.post(`/reports/run/${reportId}`, { cycle_code: cycleCode });
  },

  // Preview SQL for a report
  previewReportSQL: (reportId: number, cycleCode: number): Promise<{ data: any }> => {
    return apiClient.get(`/reports/${reportId}/preview-sql`, { 
      params: { cycle_code: (cycleCode) } 
    });
  },

  // Get execution logs for a report
  getExecutionLogs: (reportId: number, limit: number = 50): Promise<{ data: any[] }> => {
    return apiClient.get(`/reports/${reportId}/execution-logs`, { 
      params: { limit } 
    });
  },

  // ===== STATISTICS AND METADATA =====
  
  // Get available cycles from data warehouse
  getAvailableCycles: (): Promise<{ data: Array<{ label: string; value: string }> }> => {
    return apiClient.get('/reports/data/cycles');
  },

  // Export to Excel with column management support
  exportXlsx: (data: { 
    reportType: string;
    data: ReportRow[];
    fileName: string;
    columnPreferences?: ReportColumnPreferences;
  }) => {
    return apiClient.post('/reports/export-xlsx', data, { responseType: 'blob' });
  },

  // Get available calculations for report building
  getAvailableCalculations: (scope: 'DEAL' | 'TRANCHE'): Promise<{ data: AvailableCalculation[] }> => {
    return apiClient.get('/reports/calculations/available', {
      params: { scope }
    });
  },

  // ===== COLUMN MANAGEMENT UTILITIES =====

  // Validate column preferences (client-side utility)
  validateColumnPreferences: (preferences: ReportColumnPreferences): { isValid: boolean; errors: string[] } => {
    const { validateColumnPreferences } = require('../components/utils/reportBusinessLogic');
    return validateColumnPreferences(preferences);
  },

  // Generate preview of formatted data (client-side utility)  
  previewFormattedData: (rawData: any[], columnPreferences: ReportColumnPreferences): any[] => {
    const { generateFormattedPreview } = require('../components/utils/reportBusinessLogic');
    return generateFormattedPreview(rawData, columnPreferences);
  }
};

export default reportingApi;