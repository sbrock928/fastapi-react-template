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
  hasDependents?: boolean;  // Indicates this field affects other fields
  dependsOn?: string;       // Indicates this field depends on another field
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

// Dynamic report configuration from API
export interface DynamicReportConfig {
  apiEndpoint: string;
  title: string;
  columns: ReportColumn[];
}

export interface ReportConfigurationResponse {
  [key: string]: DynamicReportConfig;
}

// Report parameter types preserved for historical purposes/future flexibility
export interface ReportParameter {
  field: string;
  label: string;
  type: string;
  options?: {value: string, label: string}[];
  dynamicOptions?: string;
}

// Legacy ReportConfig maintained for backward compatibility
export interface ReportConfig {
  apiEndpoint: string;
  title: string;
  columns: ReportColumn[];
}

export type ReportRow = Record<string, any>;

// New types for task queue integration
export interface ScheduledReport {
  id: number;
  report_id: number;
  report_name?: string;
  user_id: number;
  name: string;
  description?: string;
  parameters: Record<string, any>;
  frequency: 'DAILY' | 'WEEKLY' | 'MONTHLY';
  day_of_week?: 'MONDAY' | 'TUESDAY' | 'WEDNESDAY' | 'THURSDAY' | 'FRIDAY' | 'SATURDAY' | 'SUNDAY';
  day_of_month?: number;
  time_of_day: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ReportExecution {
  id: number;
  report_id: number;
  report_name?: string;
  scheduled_report_id?: number;
  task_id?: string;
  user_id?: number;
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  parameters: Record<string, any>;
  started_at?: string;
  completed_at?: string;
  result_path?: string;
  error?: string;
}

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
