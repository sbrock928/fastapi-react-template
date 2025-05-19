import axios from 'axios';
import type { ResourceItem, Note, ReportRow } from '@/types';

// Create an axios instance with common configuration
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

// Reports API
export const reportsApi = {
  getReportConfigurations: () => api.get('/reports/configurations'),
  runReport: (endpoint: string, params: Record<string, string>) => 
    api.post(endpoint, params),
  exportXlsx: (data: { reportType: string, data: ReportRow[], fileName: string }) => 
    api.post('/reports/export-xlsx', data, { responseType: 'blob' }),
  getCycleCodes: () => api.get('/reports/cycle-codes'),
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

export default api;
