import axios from 'axios';
import type { ResourceItem, Note, ReportRow } from '@/types';

// Create an axios instance with common configuration
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for global handling
api.interceptors.request.use(
  (config) => {
    // You can add auth token here
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

// Path helper to ensure API prefix
const ensureApiPrefix = (path: string) => {
  // If path already starts with /api, return as is
  if (path.startsWith('c')) return path;
  // If path starts with / but not /api/, add /api prefix
  if (path.startsWith('/')) return `/api${path}`;
  // If path doesn't start with /, add /api/ prefix
  return `/api/${path}`;
};

// Resources API
export const resourcesApi = {
  getAll: (endpoint: string) => api.get(ensureApiPrefix(endpoint)),
  getById: (endpoint: string, id: number) => api.get(ensureApiPrefix(`${endpoint}/${id}`)),
  create: (endpoint: string, data: ResourceItem) => api.post(ensureApiPrefix(endpoint), data),
  update: (endpoint: string, id: number, data: ResourceItem) => api.patch(ensureApiPrefix(`${endpoint}/${id}`), data),
  delete: (endpoint: string, id: number) => api.delete(ensureApiPrefix(`${endpoint}/${id}`)),
};

// Logs API
export const logsApi = {
  getLogs: (params: Record<string, string | number>) => 
    api.get(ensureApiPrefix('/logs/'), { params }),
  getLogDetail: (logId: number) => 
    api.get(ensureApiPrefix(`/logs/?limit=1&offset=0&log_id=${logId}`)),
  getStatusDistribution: (hours: string) => 
    api.get(ensureApiPrefix(`/reports/status-distribution?hours=${hours}`)),
};

// Reports API
export const reportsApi = {
  runReport: (endpoint: string, params: Record<string, string>) => 
    api.post(ensureApiPrefix(endpoint), params),
  exportXlsx: (data: { reportType: string, data: ReportRow[], fileName: string }) => 
    api.post(ensureApiPrefix('/reports/export-xlsx'), data, { responseType: 'blob' }),
  getCycleCodes: () => api.get(ensureApiPrefix('/reports/cycle-codes')),
};

// Documentation API
export const documentationApi = {
  getNotes: () => api.get(ensureApiPrefix('/user-guide/notes')),
  getNoteById: (id: number) => api.get(ensureApiPrefix(`/user-guide/notes/${id}`)),
  createNote: (note: Omit<Note, 'id' | 'created_at' | 'updated_at'>) => 
    api.post(ensureApiPrefix('/user-guide/notes'), note),
  updateNote: (id: number, note: Omit<Note, 'id' | 'created_at' | 'updated_at'>) => 
    api.put(ensureApiPrefix(`/user-guide/notes/${id}`), note),
  deleteNote: (id: number) => api.delete(ensureApiPrefix(`/user-guide/notes/${id}`)),
};

export default api;
