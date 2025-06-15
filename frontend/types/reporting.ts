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
}

// Updated calculation reference for reports
export interface ReportCalculation {
  calculation_id: string; // NOW ALWAYS STRING: "user.{source_field}", "system.{result_column}", "static_{table}.{field}"
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
  id: string; // NOW ALWAYS STRING: "user.{source_field}", "system.{result_column}", "static_{table}.{field}"
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
  // With new format, calculation ID is always a string
  return {
    calculation_id: availableCalc.id, // Now always a string in new format
    calculation_type: determineCalculationType(availableCalc),
    display_order: displayOrder,
    display_name: displayName || availableCalc.name
  };
}

/**
 * Determine calculation type from available calculation
 * Updated for new ID format
 */
function determineCalculationType(calc: AvailableCalculation): 'user' | 'system' | 'static' {
  if (calc.calculation_type === 'STATIC_FIELD' || calc.id.startsWith('static_')) {
    return 'static';
  } else if (calc.calculation_type === 'SYSTEM_SQL' || calc.id.startsWith('system.')) {
    return 'system';
  } else if (calc.calculation_type === 'USER_DEFINED' || calc.id.startsWith('user.')) {
    return 'user';
  }
  
  // Fallback logic (shouldn't be needed with new format)
  console.warn(`Unknown calculation type for calc: ${calc.id}`, calc);
  return 'user';
}

// NEW: Helper functions for column management

export function createColumnPreference(
  calculationId: string, // Now always string
  displayName: string,
  displayOrder: number = 0,
  formatType: ColumnFormat = ColumnFormat.TEXT,
  isVisible: boolean = true
): ColumnPreference {
  return {
    column_id: calculationId, // Direct string assignment
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
  const addedColumnIds = new Set<string>(); // Track added columns to prevent duplicates
  let order = 0;

  // Define default column mappings
  const defaultColumns = [
    { id: 'deal_number', name: 'Deal Number', format: ColumnFormat.TEXT },
    ...(scope === 'TRANCHE' ? [{ id: 'tranche_id', name: 'Tranche ID', format: ColumnFormat.TEXT }] : []),
    { id: 'cycle_code', name: 'Cycle Code', format: ColumnFormat.NUMBER }
  ];

  // Add default columns if requested
  if (includeDefaults) {
    defaultColumns.forEach(defaultCol => {
      columns.push(createColumnPreference(defaultCol.id, defaultCol.name, order++, defaultCol.format));
      addedColumnIds.add(defaultCol.id);
    });
  }

  // Add calculation columns, but skip if they duplicate default columns
  calculations.forEach(calc => {
    const columnId = calc.calculation_id;
    
    // Skip if this column would duplicate a default column
    const isDuplicateDefault = (
      (columnId === 'static_deal.dl_nbr' && addedColumnIds.has('deal_number')) ||
      (columnId === 'static_tranche.tr_id' && addedColumnIds.has('tranche_id')) ||
      (columnId === 'static_tranchebal.cycle_cde' && addedColumnIds.has('cycle_code'))
    );
    
    // Skip if we've already added this exact column ID
    if (addedColumnIds.has(columnId) || isDuplicateDefault) {
      return;
    }
    
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
    addedColumnIds.add(columnId);
  });

  return {
    columns,
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
  return calc.calculation_type === 'STATIC_FIELD' || calc.id.startsWith('static_');
}

export function isUserDefinedCalculation(calc: AvailableCalculation): boolean {
  return calc.calculation_type === 'USER_DEFINED' || calc.id.startsWith('user.');
}

export function isSystemSqlCalculation(calc: AvailableCalculation): boolean {
  return calc.calculation_type === 'SYSTEM_SQL' || calc.id.startsWith('system.');
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