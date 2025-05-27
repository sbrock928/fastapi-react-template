import apiClient from './apiClient';
import type { ResourceItem } from '@/types/resources';

// Resources API service
const resourcesApi = {
  getAll: (endpoint: string) => apiClient.get(endpoint),
  getById: (endpoint: string, id: number) => apiClient.get(`${endpoint}/${id}`),
  create: (endpoint: string, data: ResourceItem) => apiClient.post(endpoint, data),
  update: (endpoint: string, id: number, data: ResourceItem) => apiClient.patch(`${endpoint}/${id}`, data),
  delete: (endpoint: string, id: number) => apiClient.delete(`${endpoint}/${id}`),
};

export default resourcesApi;