// Enhanced api.ts - Add these new endpoints to your existing api.ts file

import axios from 'axios';
import type { 
  ResourceItem, 
  Note, 
  ReportRow, 
  Deal, 
  Tranche, 
  ReportConfig, 
  ReportSummary, 
  RunReportRequest,
  DealReportRow,
  TrancheReportRow 
} from '@/types';

// ===== EXISTING API SETUP (keep unchanged) =====
const api = axios.create({
  baseURL: '',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for smart API path handling that works in all environments
api.interceptors.request.use(
  (config) => {
    // Skip external URLs
    if (config.url && config.url.startsWith('http')) {
      return config;
    }

    // Handle API prefixing consistently across environments
    if (config.url) {
      // First, normalize the path by removing any existing /api prefix
      let url = config.url;
      while (url.startsWith('/api/')) {
        url = url.substring(4); // Remove /api/
      }
      
      // Ensure the path starts with a slash
      if (!url.startsWith('/')) {
        url = '/' + url;
      }
      
      // In all environments, we want a single /api prefix
      config.url = '/api' + url;
    }
    
    return config;
  },
  (error) => Promise.reject(error)
);

// Add response interceptor for global error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response || error);
    return Promise.reject(error);
  }
);

// ===== EXISTING APIs (keep unchanged) =====

// Resources API
export const resourcesApi = {
  getAll: (endpoint: string) => api.get(endpoint),
  getById: (endpoint: string, id: number) => api.get(`${endpoint}/${id}`),
  create: (endpoint: string, data: ResourceItem) => api.post(endpoint, data),
  update: (endpoint: string, id: number, data: ResourceItem) => api.patch(`${endpoint}/${id}`, data),
  delete: (endpoint: string, id: number) => api.delete(`${endpoint}/${id}`),
};

// Logs API
export const logsApi = {
  getLogs: (params: Record<string, string | number>) => 
    api.get('/logs/', { params }),
  getLogDetail: (logId: number) => 
    api.get(`/logs/?limit=1&offset=0&log_id=${logId}`),
  getStatusDistribution: (hours: string) => 
    api.get(`/logs/status-distribution?hours=${hours}`),
};

// Documentation API
export const documentationApi = {
  getNotes: () => api.get('/user-guide/notes'),
  getNoteById: (id: number) => api.get(`/user-guide/notes/${id}`),
  createNote: (note: Omit<Note, 'id' | 'created_at' | 'updated_at'>) => 
    api.post('/user-guide/notes', note),
  updateNote: (id: number, note: Omit<Note, 'id' | 'created_at' | 'updated_at'>) => 
    api.put(`/user-guide/notes/${id}`, note),
  deleteNote: (id: number) => api.delete(`/user-guide/notes/${id}`),
};

// ===== ENHANCED REPORTS API =====

export const reportsApi = {
  // ===== LEGACY ENDPOINTS (backward compatibility) =====
  getReportConfigurations: () => api.get('/reports/configurations'),
  runReport: (endpoint: string, params: Record<string, string>) => 
    api.post(endpoint, params),
  exportXlsx: (data: { reportType: string, data: ReportRow[], fileName: string }) => 
    api.post('/reports/export-xlsx', data, { responseType: 'blob' }),
  getCycleCodes: () => api.get('/reports/cycle-codes'),

  // ===== NEW DEAL & TRANCHE DATA ENDPOINTS =====
  
  // Get available deals for report building
  getDeals: (cycleCode?: string): Promise<{ data: Deal[] }> => {
    const params = cycleCode ? { cycle_code: cycleCode } : {};
    return api.get('/reports/data/deals', { params });
  },

  // Get tranches for specific deals
  getTranches: (dealIds: number[], cycleCode?: string): Promise<{ data: Record<number, Tranche[]> }> => {
    return api.post('/reports/data/tranches', {
      deal_ids: dealIds,
      cycle_code: cycleCode
    });
  },

  // Get tranches for a single deal
  getDealTranches: (dealId: number, cycleCode?: string): Promise<{ data: Tranche[] }> => {
    const params = cycleCode ? { cycle_code: cycleCode } : {};
    return api.get(`/reports/data/deals/${dealId}/tranches`, { params });
  },

  // ===== NEW REPORT CONFIGURATION ENDPOINTS =====

  // Get all report configurations
  getAllReports: (): Promise<{ data: ReportConfig[] }> => {
    return api.get('/reports/');
  },

  // Get user's saved reports with summary info
  getUserReports: (userId: string): Promise<{ data: ReportSummary[] }> => {
    return api.get(`/reports/user/${userId}`);
  },

  // Get specific report configuration
  getReport: (reportId: number): Promise<{ data: ReportConfig }> => {
    return api.get(`/reports/${reportId}`);
  },

  // Create new report configuration
  createReport: (reportData: Omit<ReportConfig, 'id' | 'created_date' | 'updated_date'>): Promise<{ data: ReportConfig }> => {
    return api.post('/reports/', reportData);
  },

  // Update report configuration
  updateReport: (reportId: number, reportData: Partial<ReportConfig>): Promise<{ data: ReportConfig }> => {
    return api.patch(`/reports/${reportId}`, reportData);
  },

  // Delete report configuration
  deleteReport: (reportId: number): Promise<{ data: { message: string } }> => {
    return api.delete(`/reports/${reportId}`);
  },

  // ===== NEW REPORT EXECUTION ENDPOINTS =====

  // Run a saved report configuration
  runSavedReport: (request: RunReportRequest): Promise<{ data: DealReportRow[] | TrancheReportRow[] }> => {
    return api.post('/reports/run', request);
  },

  // Run report by ID with cycle parameter
  runReportById: (reportId: number, cycleCode: string): Promise<{ data: DealReportRow[] | TrancheReportRow[] }> => {
    return api.post(`/reports/run/${reportId}`, { cycle_code: cycleCode });
  },

  // ===== STATISTICS AND METADATA =====

  // Get summary statistics
  getStats: (): Promise<{ data: { total_deals: number; total_tranches: number; total_reports: number; timestamp: string } }> => {
    return api.get('/reports/stats/summary');
  },

  // Get available cycles from data warehouse
  getAvailableCycles: (): Promise<{ data: Array<{ code: string; label: string }> }> => {
    return api.get('/reports/data/cycles');
  },

  // NEW: Column management endpoints
  getAvailableColumns: (scope: 'deal' | 'tranche'): Promise<{ data: Record<string, ColumnDefinition[]> }> => {
    return api.get(`/reports/columns/${scope}`);
  },

  getDefaultColumns: (scope: 'deal' | 'tranche'): Promise<{ data: string[] }> => {
    return api.get(`/reports/columns/${scope}/defaults`);
  },
  
};

export default api;