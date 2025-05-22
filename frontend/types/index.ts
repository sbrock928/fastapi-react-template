// ===== EXISTING TYPES (preserved) =====

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

// ===== NEW ENHANCED REPORTING TYPES =====

// Deal & Tranche Data Types
export interface Deal {
  id: number;
  name: string;
  originator: string;
  deal_type: string;
  total_principal: number;
  credit_rating: string;
  yield_rate: number;
  closing_date: string;
  cycle_code: string;
}

export interface Tranche {
  id: number;
  deal_id: number;
  name: string;
  class_name: string;
  principal_amount: number;
  interest_rate: number;
  credit_rating: string;
  payment_priority: number;
  cycle_code: string;
}

// Report Configuration Types
export interface ReportConfig {
  id?: number;
  name: string;
  scope: 'DEAL' | 'TRANCHE';
  created_by: string;
  created_date?: string;
  updated_date?: string;
  selected_deals: number[];
  selected_tranches: Record<number, number[]>; // dealId -> trancheIds[]
}

export interface ReportSummary {
  id: number;
  name: string;
  scope: 'DEAL' | 'TRANCHE';
  created_date: string;
  deal_count: number;
  tranche_count: number;
}

// Report Execution Types
export interface RunReportRequest {
  report_id: number;
  cycle_code: string;
}

export interface DealReportRow {
  deal_id: number;
  deal_name: string;
  originator: string;
  deal_type: string;
  total_principal: number;
  credit_rating: string;
  yield_rate: number;
  closing_date: string;
  cycle_code: string;
  [key: string]: any; // Allow additional dynamic fields
}

export interface TrancheReportRow {
  tranche_id: number;
  tranche_name: string;
  deal_id: number;
  deal_name: string;
  class_name: string;
  principal_amount: number;
  interest_rate: number;
  credit_rating: string;
  payment_priority: number;
  cycle_code: string;
  [key: string]: any; // Allow additional dynamic fields
}

// Cycle Selection Types
export interface CycleOption {
  value: string;
  label: string;
}

// Form and UI State Types
export interface ReportBuilderState {
  currentStep: number;
  reportName: string;
  reportScope: 'DEAL' | 'TRANCHE' | '';
  selectedDeals: number[];
  selectedTranches: Record<number, number[]>;
}

// API Response Types for better type safety
export interface ApiResponse<T> {
  data: T;
  message?: string;
  status?: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}