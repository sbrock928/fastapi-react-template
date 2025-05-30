// Reporting-specific types
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

// Report Configuration Types (Updated to match backend normalized schema)
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
}

export interface ReportSummary {
  id: number;
  name: string;
  description?: string;
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

// Form and UI State Types
export interface ReportBuilderState {
  currentStep: number;
  reportName: string;
  reportScope: 'DEAL' | 'TRANCHE' | '';
  selectedDeals: number[]; // Changed back to number[] for dl_nbr
  selectedTranches: Record<number, Array<{dl_nbr: number, tr_id: string}>>;
}
