import apiClient from './apiClient';
import type { 
  ReportRow, 
  Deal, 
  TrancheReportSummary, 
  ReportConfig, 
  ReportSummary, 
  RunReportRequest,
  DealReportRow,
  TrancheReportRow,
  AvailableCalculation // Changed from AvailableField
} from '@/types/reporting';

// Reporting API service - Updated for calculation-based reporting
const reportingApi = {
  // ===== DEAL & TRANCHE DATA ENDPOINTS =====
  
  // Get available deals for report building
  getDeals: (cycleCode?: number): Promise<{ data: Deal[] }> => {
    const params = cycleCode ? { cycle_code: cycleCode } : {};
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

  // Create new report configuration
  createReport: (reportData: Omit<ReportConfig, 'id' | 'created_date' | 'updated_date'>): Promise<{ data: ReportConfig }> => {
    return apiClient.post('/reports/', reportData);
  },

  // Update report configuration
  updateReport: (reportId: number, reportData: Partial<ReportConfig>): Promise<{ data: ReportConfig }> => {
    return apiClient.patch(`/reports/${reportId}`, reportData);
  },

  // Delete report configuration
  deleteReport: (reportId: number): Promise<{ data: { message: string } }> => {
    return apiClient.delete(`/reports/${reportId}`);
  },

  // ===== REPORT EXECUTION ENDPOINTS =====

  // Run a saved report configuration
  runSavedReport: (request: RunReportRequest): Promise<{ data: DealReportRow[] | TrancheReportRow[] }> => {
    return apiClient.post('/reports/run', request);
  },

  // Run report by ID with cycle parameter
  runReportById: (reportId: number, cycleCode: string): Promise<{ data: DealReportRow[] | TrancheReportRow[] }> => {
    return apiClient.post(`/reports/run/${reportId}`, { cycle_code: cycleCode });
  },

  // ===== STATISTICS AND METADATA =====
  
  // Get available cycles from data warehouse
  getAvailableCycles: (): Promise<{ data: Array<{ label: string; value: string }> }> => {
    return apiClient.get('/reports/data/cycles');
  },

  // Export to Excel
  exportXlsx: (data: { reportType: string, data: ReportRow[], fileName: string }) => 
    apiClient.post('/reports/export-xlsx', data, { responseType: 'blob' }),

  // Get available calculations for report building (UPDATED)
  getAvailableCalculations: (scope: 'DEAL' | 'TRANCHE'): Promise<{ data: AvailableCalculation[] }> => {
    return apiClient.get('/reports/calculations/available', {
      params: { scope }
    });
  }
};

export default reportingApi;