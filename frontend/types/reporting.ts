// Reporting-specific types - Updated for calculation-based reporting
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

// Calculation Selection Types (replacing field selection)
export interface AvailableCalculation {
  id: number;
  name: string;
  description?: string;
  aggregation_function: string;
  source_model: string;
  source_field: string;
  group_level: string;
  weight_field?: string;
  scope: 'DEAL' | 'TRANCHE';
  category: string;
  is_default: boolean;
}

export interface ReportCalculation {
  id?: number;
  report_id?: number;
  calculation_id: number;
  display_order: number;
  display_name?: string;
}

// Deal & Tranche Data Types (Updated for new schema)
export interface Deal {
  dl_nbr: number;
  issr_cde: string;
  cdi_file_nme: string;
  CDB_cdi_file_nme: string;
}

export interface Tranche {
  dl_nbr: number;
  tr_id: string;
}

// TrancheBal Data Type
export interface TrancheBal {
  dl_nbr: number;
  tr_id: string;
  cycle_date: string;
}

// Report summary types for listing tranches
export interface TrancheReportSummary {
  dl_nbr: number;
  tr_id: string;
  deal_issr_cde: string;
}

// Report Configuration Types (Updated to use calculations instead of fields)
export interface ReportTranche {
  id?: number;
  report_deal_id?: number;
  dl_nbr: number;
  tr_id: string;
}

export interface ReportDeal {
  id?: number;
  report_id?: number;
  dl_nbr: number;
  selected_tranches: ReportTranche[];
}

export interface ReportConfig {
  id?: number;
  name: string;
  description?: string;
  scope: 'DEAL' | 'TRANCHE';
  created_by: string;
  created_date?: string;
  updated_date?: string;
  selected_deals: ReportDeal[];
  selected_calculations: ReportCalculation[]; // Changed from selected_fields
}

export interface ReportSummary {
  id: number;
  name: string;
  description?: string;
  scope: 'DEAL' | 'TRANCHE';
  created_by: string;
  created_date: string;
  deal_count: number;
  tranche_count: number;
  calculation_count: number; // Changed from field_count
  is_active: boolean;
}

// Report Execution Types
export interface RunReportRequest {
  report_id: number;
  cycle_code: number;
}

export interface DealReportRow {
  dl_nbr: number;
  issr_cde: string;
  cdi_file_nme: string;
  CDB_cdi_file_nme: string;
  // Aggregated tranche data
  tranche_count?: number;
  [key: string]: any; // Allow additional dynamic fields
}

export interface TrancheReportRow {
  // Deal information (static)
  dl_nbr: number;
  deal_issr_cde: string;
  deal_cdi_file_nme: string;
  deal_CDB_cdi_file_nme: string;
  // Tranche information
  tr_id: string;
  [key: string]: any; // Allow additional dynamic fields
}

// Cycle Selection Types (simplified for new schema)
export interface CycleOption {
  value: number;
  label: string;
}

// Form and UI State Types (Updated for calculations)
export interface ReportFormState {
  reportName: string;
  reportDescription: string;
  reportScope: 'DEAL' | 'TRANCHE' | '';
  selectedDeals: number[];
  selectedTranches: Record<number, string[]>;
  selectedCalculations: ReportCalculation[]; // Changed from selectedFields
  currentStep: number;
}

export interface ValidationErrors {
  reportName?: string;
  reportScope?: string;
  selectedDeals?: string;
  selectedTranches?: string;
  selectedCalculations?: string; // Changed from selectedFields
}