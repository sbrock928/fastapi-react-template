// frontend/types/reporting.ts
// Updated reporting types to work with the new separated calculation system

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
  value: string | number; // Allow both string and number for flexibility
}

// Updated calculation reference for reports
// Now supports multiple calculation types with flexible ID system
export interface ReportCalculation {
  calculation_id: number; // For user/system calculations, or composite ID for static fields
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

// Core report configuration
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
}

// Available calculations for report building
// This combines all calculation types into a unified interface
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
  calculation_type?: 'USER_DEFINED' | 'SYSTEM_SQL' | 'STATIC_FIELD'; // Added for new system
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

// Form state for report builder wizard
export interface ReportBuilderFormState {
  reportName: string;
  reportDescription: string;
  reportScope: ReportScope | '';
  selectedDeals: number[];
  selectedTranches: Record<number, string[]>;
  selectedCalculations: ReportCalculation[]; // Updated for new system
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

// Helper functions for working with the new calculation system

export function createReportCalculation(
  availableCalc: AvailableCalculation,
  displayOrder: number = 0,
  displayName?: string
): ReportCalculation {
  let calculationId: number;
  let calculationType: 'user' | 'system' | 'static';

  if (typeof availableCalc.id === 'string' && availableCalc.id.startsWith('static_')) {
    // Static field - use a special encoding
    calculationId = hashStringToNumber(availableCalc.id);
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
    display_name: displayName
  };
}

export function isStaticFieldCalculation(calc: AvailableCalculation): boolean {
  return typeof calc.id === 'string' && calc.id.startsWith('static_');
}

export function isUserDefinedCalculation(calc: AvailableCalculation): boolean {
  return calc.calculation_type === 'USER_DEFINED';
}

export function isSystemSqlCalculation(calc: AvailableCalculation): boolean {
  return calc.calculation_type === 'SYSTEM_SQL';
}

export function getCalculationDisplayName(calc: AvailableCalculation): string {
  return calc.name;
}

export function getCalculationDescription(calc: AvailableCalculation): string {
  if (calc.description) {
    return calc.description;
  }
  
  if (isStaticFieldCalculation(calc)) {
    return `Raw field value: ${calc.source_field}`;
  } else if (isUserDefinedCalculation(calc)) {
    return `${calc.aggregation_function} of ${calc.source_model}.${calc.source_field}`;
  } else if (isSystemSqlCalculation(calc)) {
    return 'Custom SQL calculation';
  }
  
  return 'No description available';
}

export function getCalculationCompatibilityInfo(calc: AvailableCalculation, reportScope: ReportScope): {
  isCompatible: boolean;
  reason?: string;
} {
  // Deal-level reports
  if (reportScope === 'DEAL') {
    if (isStaticFieldCalculation(calc) && calc.group_level === 'tranche') {
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
  if (reportScope === 'TRANCHE') {
    if (calc.group_level === 'deal' && !isStaticFieldCalculation(calc)) {
      return {
        isCompatible: false,
        reason: 'Deal-level calculations are designed for deal-level aggregation only'
      };
    }
  }
  
  return { isCompatible: true };
}

export function filterCalculationsByCompatibility(
  calculations: AvailableCalculation[],
  reportScope: ReportScope
): {
  compatible: AvailableCalculation[];
  incompatible: AvailableCalculation[];
} {
  const compatible: AvailableCalculation[] = [];
  const incompatible: AvailableCalculation[] = [];
  
  calculations.forEach(calc => {
    const { isCompatible } = getCalculationCompatibilityInfo(calc, reportScope);
    if (isCompatible) {
      compatible.push(calc);
    } else {
      incompatible.push(calc);
    }
  });
  
  return { compatible, incompatible };
}

// Utility function to convert string IDs to numbers (for static fields)
function hashStringToNumber(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash);
}

// Export utility for dealing with mixed calculation types in forms
export function convertFormCalculationsToReportCalculations(
  selectedCalculations: AvailableCalculation[]
): ReportCalculation[] {
  return selectedCalculations.map((calc, index) => 
    createReportCalculation(calc, index)
  );
}

export function findAvailableCalculationById(
  calculations: AvailableCalculation[],
  reportCalc: ReportCalculation
): AvailableCalculation | undefined {
  if (reportCalc.calculation_type === 'static') {
    // For static fields, find by the static_ prefix pattern
    return calculations.find(calc => 
      typeof calc.id === 'string' && 
      hashStringToNumber(calc.id) === reportCalc.calculation_id
    );
  } else {
    // For user/system calculations, find by numeric ID
    return calculations.find(calc => 
      typeof calc.id === 'number' && 
      calc.id === reportCalc.calculation_id
    );
  }
}