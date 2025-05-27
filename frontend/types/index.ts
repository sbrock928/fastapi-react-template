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

// Deal & Tranche Data Types (Updated for new data model)
export interface Deal {
  id: number;
  name: string;
  originator: string;
  deal_type: string;
  total_principal: number;
  credit_rating: string;
  yield_rate: number;
  closing_date: string;
  // Note: cycle_code removed - deals are now static
}

export interface Tranche {
  id: number;
  deal_id: number;
  name: string;
  class_name: string;
  subordination_level: number;
  credit_rating: string;
  payment_priority: number;
  maturity_date?: string;
  // Note: cycle_code, principal_amount, interest_rate moved to TrancheHistorical
}

// New Historical Data Type
export interface TrancheHistorical {
  id: number;
  tranche_id: number;
  cycle_code: string;
  principal_amount: number;
  interest_rate: number;
  created_date: string;
  updated_date: string;
  is_active: boolean;
}

// Combined data for reporting (includes both static and historical data)
export interface TrancheWithHistorical extends Tranche {
  cycle_code: string;
  principal_amount: number;
  interest_rate: number;
}

// Summary schemas with cycle data for reporting (matches backend TrancheReportSummary)
export interface TrancheReportSummary {
  id: number;
  deal_id: number;
  deal_name: string;
  name: string;
  class_name: string;
  credit_rating: string;
  cycle_code: string;
  principal_amount: number;
  interest_rate: number;
  payment_priority?: number; // Add this for sorting compatibility
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
  cycle_code: string; // This comes from the report execution context
  // Aggregated tranche data
  tranche_count?: number;
  total_tranche_principal?: number;
  avg_tranche_interest_rate?: number;
  [key: string]: any; // Allow additional dynamic fields
}

export interface TrancheReportRow {
  // Deal information (static)
  deal_id: number;
  deal_name: string;
  deal_originator: string;
  deal_type: string;
  deal_credit_rating: string;
  deal_yield_rate: number;
  // Tranche static information
  tranche_id: number;
  tranche_name: string;
  class_name: string;
  subordination_level: number;
  credit_rating: string;
  payment_priority: number;
  maturity_date?: string;
  // Historical/cycle-specific data
  cycle_code: string;
  principal_amount: number;
  interest_rate: number;
  [key: string]: any; // Allow additional dynamic fields
}

// Cycle Selection Types
export interface CycleOption {
  code: string;
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