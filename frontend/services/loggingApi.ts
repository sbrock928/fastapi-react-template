import apiClient from './apiClient';
import type { Log, StatusDistribution } from '@/types/logging';

// Logging API response types that match the actual backend responses
interface LogsResponse {
  data: Log[];
  headers: {
    'x-total-count'?: string;
    [key: string]: string | undefined;
  };
}

interface StatusDistributionResponse {
  data: {
    status_distribution: StatusDistribution[];
  };
}

// Logging API service
const loggingApi = {
  getLogs: (params: Record<string, string | number>): Promise<LogsResponse> => 
    apiClient.get('/logs/', { params }),
  getLogDetail: (logId: number): Promise<LogsResponse> => 
    apiClient.get(`/logs/?limit=1&offset=0&log_id=${logId}`),
  getStatusDistribution: (hours: string): Promise<StatusDistributionResponse> => 
    apiClient.get(`/logs/status-distribution?hours=${hours}`),
};

export default loggingApi;