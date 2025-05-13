// Resource Types
export interface ResourceColumn {
  field: string;
  header: string;
  type: string;
  required?: boolean;
  minLength?: number;
  placeholder?: string;
  pattern?: string;
  options?: {value: string, text: string}[];
}

export interface ResourceConfig {
  apiEndpoint: string;
  modelName: string;
  idField: string;
  columns: ResourceColumn[];
  displayName: string;
}

export type ResourceItem = Record<string, any>;

// Reporting Types
export interface ReportColumn {
  field: string;
  header: string;
  type: string;
}

export interface ReportParameter {
  field: string;
  label: string;
  type: string;
  options?: {value: string, label: string}[];
  dynamicOptions?: string; // Used to specify which API to call for dynamic options
}

export interface ReportConfig {
  apiEndpoint: string;
  title: string;
  columns: ReportColumn[];
  parameters: ReportParameter[];
}

export type ReportRow = Record<string, any>;

// Logs Types
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

// Documentation Types
export interface Note {
  id: number;
  title: string;
  content: string;
  category: string;
  created_at: string;
  updated_at: string | null;
}
