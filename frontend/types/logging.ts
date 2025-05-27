// Logging-specific types
export interface Log {
  id: number;
  timestamp: string;
  method: string;
  path: string;
  status_code: number;
  client_ip: string;
  processing_time: number;
  request_headers?: string;
  request_body?: string;
  response_body?: string;
  status_category?: string;
  username?: string;
  hostname?: string;
  application_id?: string;
}

export interface StatusDistribution {
  status_code: number;
  count: number;
  description: string;
}