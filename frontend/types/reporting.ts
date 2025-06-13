// frontend/types/reporting.ts - Updated with column management support

// Base reporting types
export interface ReportRow {
  [key: string]: any;
}

export interface DynamicReportConfig {
  apiEndpoint: string;
  title: string;
  columns: ReportColumn[];
}

export interface ReportColumn {
  field: string;
  header: string;
  type: 'string' | 'number' | 'currency' | 'percentage' | 'date';
}

// Report scope
export type ReportScope = 'DEAL' | 'TRANCHE';

// Cycle option for dropdown selections
export interface CycleOption {
  label: string;
  value: string | number;
}

// NEW: Column formatting options
export enum ColumnFormat {
  TEXT = "text",
  NUMBER = "number", 
  CURRENCY = "currency",
  PERCENTAGE = "percentage",
  DATE_MDY = "date_mdy",  // MM/DD/YYYY
  DATE_DMY = "date_dmy"   // DD/MM/YYYY
}

// NEW: Individual column preference
export interface ColumnPreference {
  column_id: string;           // Matches calculation_id or static field name
  display_name: string;        // User-friendly column name
  is_visible: boolean;         // Whether to include in final output
  display_order: number;       // Order in the final output
  format_type: ColumnFormat;   // How to format values
}

// NEW: Complete column preferences for a report
export interface ReportColumnPreferences {
  columns: ColumnPreference[];
  include_default_columns: boolean; // Whether to include Deal Number, TR ID, Cycle Code
}

// Updated calculation reference for reports
export interface ReportCalculation {
  calculation_id: number | string; // Support both numeric IDs (user/system) and string IDs (static fields)
  calculation_type?: 'user' | 'system' | 'static'; // Optional type hint
  display_order: number;
  display_name?: string; // Optional override for display name
}

// Tranche selection for reports
export interface ReportTranche {
  tr_id: string;
  dl_nbr?: number; // Auto-populated from parent deal
}

// Deal selection for reports  
export interface ReportDeal {
  dl_nbr: number;
  selected_tranches?: ReportTranche[]; // Empty means all tranches
}

// Core report configuration with column preferences
export interface ReportConfig {
  id?: number;
  name: string;
  description?: string;
  scope: ReportScope;
  created_by?: string;
  created_date?: string;
  updated_date?: string;
  is_active?: boolean;
  selected_deals: ReportDeal[];
  selected_calculations: ReportCalculation[];
  column_preferences?: ReportColumnPreferences; // NEW: Column management
}

// Available calculations for report building
export interface AvailableCalculation {
  id: number | string; // Number for user/system calcs, string for static fields
  name: string;
  description?: string;
  aggregation_function?: string; // undefined for system calcs, 'RAW' for static fields
  source_model?: string; // undefined for system calcs and static fields
  source_field?: string; // field name for static fields, undefined for system calcs
  group_level: string;
  weight_field?: string;
  scope: ReportScope;
  category: string; // For UI grouping
  is_default: boolean;
  calculation_type?: 'USER_DEFINED' | 'SYSTEM_SQL' | 'STATIC_FIELD';
}

// Deal information (from data warehouse)
export interface Deal {
  dl_nbr: number;
  issr_cde: string;
  cdi_file_nme: string;
  CDB_cdi_file_nme?: string | null;
}

// Tranche information (from data warehouse)
export interface TrancheReportSummary {
  tr_id: string;
  dl_nbr?: number;
  tr_cusip_id?: string;
}

// Report summary for listings
export interface ReportSummary {
  id: number;
  name: string;
  description?: string;
  scope: ReportScope;
  created_by: string;
  created_date: string;
  deal_count: number;
  tranche_count: number;
  calculation_count: number;
  is_active: boolean;
  total_executions: number;
  last_executed?: string;
  last_execution_success?: boolean;
  column_preferences?: ReportColumnPreferences; // NEW: Add column preferences to summary
}

// Report execution
export interface RunReportRequest {
  report_id: number;
  cycle_code: number;
}

export interface ReportExecutionLog {
  id: number;
  report_id: number;
  cycle_code: number;
  executed_by?: string;
  execution_time_ms?: number;
  row_count?: number;
  success: boolean;
  error_message?: string;
  executed_at: string;
}

// Form state for report builder wizard with column preferences
export interface ReportBuilderFormState {
  reportName: string;
  reportDescription: string;
  reportScope: ReportScope | '';
  selectedDeals: number[];
  selectedTranches: Record<number, string[]>;
  selectedCalculations: ReportCalculation[];
  columnPreferences?: ReportColumnPreferences; // NEW: Column preferences
}

// Validation types
export interface ValidationError {
  field: string;
  message: string;
}

export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
}

// Helper functions for working with the calculation system

export function createReportCalculation(
  availableCalc: AvailableCalculation,
  displayOrder: number = 0,
  displayName?: string
): ReportCalculation {
  let calculationId: number | string;
  let calculationType: 'user' | 'system' | 'static';

  if (typeof availableCalc.id === 'string' && availableCalc.id.startsWith('static_')) {
    calculationId = availableCalc.id;
    calculationType = 'static';
  } else if (typeof availableCalc.id === 'number') {
    calculationId = availableCalc.id;
    calculationType = availableCalc.calculation_type === 'SYSTEM_SQL' ? 'system' : 'user';
  } else {
    throw new Error(`Invalid calculation ID: ${availableCalc.id}`);
  }

  return {
    calculation_id: calculationId,
    calculation_type: calculationType,
    display_order: displayOrder,
    display_name: displayName || availableCalc.name
  };
}

// NEW: Helper functions for column management

export function createColumnPreference(
  calculationId: string | number,
  displayName: string,
  displayOrder: number = 0,
  formatType: ColumnFormat = ColumnFormat.TEXT,
  isVisible: boolean = true
): ColumnPreference {
  return {
    column_id: String(calculationId),
    display_name: displayName,
    is_visible: isVisible,
    display_order: displayOrder,
    format_type: formatType
  };
}

export function getDefaultColumnPreferences(
  calculations: ReportCalculation[],
  scope: ReportScope,
  includeDefaults: boolean = true
): ReportColumnPreferences {
  const columns: ColumnPreference[] = [];
  let order = 0;

  // Add default columns if requested
  if (includeDefaults) {
    columns.push(createColumnPreference('deal_number', 'Deal Number', order++, ColumnFormat.NUMBER));
    
    if (scope === 'TRANCHE') {
      columns.push(createColumnPreference('tranche_id', 'Tranche ID', order++, ColumnFormat.TEXT));
    }
    
    columns.push(createColumnPreference('cycle_code', 'Cycle Code', order++, ColumnFormat.NUMBER));
  }

  // Add calculation columns
  calculations.forEach(calc => {
    const columnId = String(calc.calculation_id);
    const displayName = calc.display_name || `Calculation ${calc.calculation_id}`;
    
    // Try to guess format based on calculation type/name
    let formatType = ColumnFormat.TEXT;
    if (displayName.toLowerCase().includes('balance') || 
        displayName.toLowerCase().includes('amount') ||
        displayName.toLowerCase().includes('value')) {
      formatType = ColumnFormat.CURRENCY;
    } else if (displayName.toLowerCase().includes('rate') || 
               displayName.toLowerCase().includes('percent')) {
      formatType = ColumnFormat.PERCENTAGE;
    } else if (displayName.toLowerCase().includes('date')) {
      formatType = ColumnFormat.DATE_MDY;
    } else if (displayName.toLowerCase().includes('count') ||
               displayName.toLowerCase().includes('number')) {
      formatType = ColumnFormat.NUMBER;
    }

    columns.push(createColumnPreference(columnId, displayName, order++, formatType));
  });

  return {
    columns,
    include_default_columns: includeDefaults
  };
}

export function getColumnFormatLabel(format: ColumnFormat): string {
  switch (format) {
    case ColumnFormat.TEXT:
      return 'Text';
    case ColumnFormat.NUMBER:
      return 'Number (1,000)';
    case ColumnFormat.CURRENCY:
      return 'Currency ($1,000.00)';
    case ColumnFormat.PERCENTAGE:
      return 'Percentage (25.5%)';
    case ColumnFormat.DATE_MDY:
      return 'Date (MM/DD/YYYY)';
    case ColumnFormat.DATE_DMY:
      return 'Date (DD/MM/YYYY)';
    default:
      return 'Text';
  }
}

// NEW: Add missing helper functions for calculation compatibility
export function isStaticFieldCalculation(calc: AvailableCalculation): boolean {
  return typeof calc.id === 'string' && calc.id.startsWith('static_');
}

export function isUserDefinedCalculation(calc: AvailableCalculation): boolean {
  return typeof calc.id === 'number' && calc.calculation_type === 'USER_DEFINED';
}

export function isSystemSqlCalculation(calc: AvailableCalculation): boolean {
  return typeof calc.id === 'number' && calc.calculation_type === 'SYSTEM_SQL';
}

export function getCalculationCompatibilityInfo(
  calc: AvailableCalculation,
  scope: ReportScope
): { isCompatible: boolean; reason?: string } {
  // Deal-level reports
  if (scope === 'DEAL') {
    if (calc.calculation_type === 'STATIC_FIELD' && calc.group_level === 'tranche') {
      return {
        isCompatible: false,
        reason: 'Raw tranche fields would create multiple rows per deal'
      };
    }
    
    if (calc.group_level === 'tranche' && calc.aggregation_function !== 'RAW') {
      return {
        isCompatible: false,
        reason: 'Tranche-level calculations are not designed for deal-level aggregation'
      };
    }
  }
  
  // Tranche-level reports
  if (scope === 'TRANCHE') {
    if (calc.group_level === 'deal' && calc.calculation_type !== 'STATIC_FIELD') {
      return {
        isCompatible: false,
        reason: 'Deal-level calculations are designed for deal-level aggregation only'
      };
    }
  }
  
  return { isCompatible: true };
}