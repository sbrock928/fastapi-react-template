// frontend/features/reporting/components/utils/reportBusinessLogic.ts
// Updated to work with the new separated calculation system

import type { ReportBuilderFormState } from '../hooks/useReportBuilderForm';
import type { AvailableCalculation, ReportCalculation } from '@/types/reporting';

/**
 * Transform form state data into the format expected by the API (simplified structure)
 * Smart tranche handling for both DEAL and TRANCHE scope reports:
 * - Only include tranches if they represent explicit exclusions from "all selected" default
 * - If all available tranches are selected, don't include tranches (means "all included")
 * - If some tranches are deselected, include only the remaining selected ones (exclusionary behavior)
 */
export const transformFormDataForApi = (formState: ReportBuilderFormState, availableTranches?: Record<number, any[]>) => {
  const { selectedDeals, selectedTranches, selectedCalculations, reportName, reportDescription, reportScope } = formState;

  const transformedSelectedDeals = selectedDeals.map((dlNbr: number) => {
    const dealTranches = selectedTranches[dlNbr] || [];
    const availableTrancheCount = availableTranches?.[dlNbr]?.length || 0;
    
    // Smart tranche handling: only include tranches if user explicitly excluded some
    // This applies to both DEAL and TRANCHE scope reports for consistency
    let shouldIncludeTranches = false;
    
    if (availableTrancheCount > 0 && dealTranches.length < availableTrancheCount) {
      // User has explicitly deselected some tranches - include the remaining selected ones
      shouldIncludeTranches = true;
    }
    // If dealTranches.length === availableTrancheCount, it means all are selected (default)
    // If dealTranches.length === 0, it means none are selected (also don't store - let backend handle)

    const dealData: any = {
      dl_nbr: dlNbr
    };

    // Only add selected_tranches if they represent explicit exclusions
    if (shouldIncludeTranches) {
      dealData.selected_tranches = dealTranches.map((trId: string) => ({
        tr_id: trId
      }));
    }

    return dealData;
  });

  // Transform calculations for the new API format
  const transformedCalculations = selectedCalculations.map((calc, index) => ({
    calculation_id: calc.calculation_id, // Keep as number, not string
    calculation_type: calc.calculation_type,
    display_order: calc.display_order ?? index,
    display_name: calc.display_name || undefined
  }));

  return {
    name: reportName,
    description: reportDescription || undefined,
    scope: reportScope as 'DEAL' | 'TRANCHE',
    selected_deals: transformedSelectedDeals,
    selected_calculations: transformedCalculations
  };
};

/**
 * Create new report configuration payload
 */
export const createReportConfigPayload = (formState: ReportBuilderFormState) => {
  const baseData = transformFormDataForApi(formState);
  
  return {
    ...baseData,
    created_by: 'current_user' // This could be made dynamic based on auth context
  };
};

/**
 * Create update report configuration payload
 */
export const createUpdateReportPayload = (formState: ReportBuilderFormState) => {
  return transformFormDataForApi(formState);
};

/**
 * Parse API error response into a user-friendly message
 */
export const parseApiError = (error: any, operation: 'saving' | 'updating'): string => {
  let errorMessage = `Error ${operation} report configuration`;
  
  if (error.response?.data?.detail) {
    const detail = error.response.data.detail;
    
    if (detail.errors && Array.isArray(detail.errors)) {
      const errorMessages = detail.errors.join(', ');
      errorMessage = `${errorMessage}: ${errorMessages}`;
    } else if (typeof detail === 'string') {
      errorMessage = `${errorMessage}: ${detail}`;
    } else if (typeof detail === 'object' && detail.message) {
      errorMessage = `${errorMessage}: ${detail.message}`;
    }
  } else if (error.response?.data?.message) {
    errorMessage = `${errorMessage}: ${error.response.data.message}`;
  } else if (error.message) {
    errorMessage = `${errorMessage}: ${error.message}`;
  }
  
  return errorMessage;
};

/**
 * Validate report configuration before save (calculation-based)
 */
export const validateReportBeforeSave = (formState: ReportBuilderFormState): { isValid: boolean; errors: string[] } => {
  const errors: string[] = [];

  // Basic validation
  if (!formState.reportName.trim()) {
    errors.push('Report name is required');
  }

  if (!formState.reportScope) {
    errors.push('Report scope is required');
  }

  if (formState.selectedDeals.length === 0) {
    errors.push('At least one deal must be selected');
  }

  if (formState.selectedCalculations.length === 0) {
    errors.push('At least one calculation must be selected');
  }

  return {
    isValid: errors.length === 0,
    errors
  };
};

/**
 * Get success message for report operations
 */
export const getSuccessMessage = (operation: 'create' | 'update'): string => {
  return operation === 'create' 
    ? 'Report configuration saved successfully!' 
    : 'Report configuration updated successfully!';
};

/**
 * Convert available calculations to report calculations for form state
 * This helps when editing existing reports
 */
export const convertAvailableCalculationsToReportCalculations = (
  availableCalculations: AvailableCalculation[]
): ReportCalculation[] => {
  return availableCalculations.map((calc, index) => ({
    calculation_id: typeof calc.id === 'number' ? calc.id : hashStringToNumber(calc.id as string),
    calculation_type: determineCalculationType(calc),
    display_order: index,
    display_name: undefined
  }));
};

/**
 * Determine calculation type from available calculation
 */
function determineCalculationType(calc: AvailableCalculation): 'user' | 'system' | 'static' {
  if (calc.calculation_type === 'STATIC_FIELD' || (typeof calc.id === 'string' && calc.id.startsWith('static_'))) {
    return 'static';
  } else if (calc.calculation_type === 'SYSTEM_SQL') {
    return 'system';
  } else {
    return 'user';
  }
}

/**
 * Convert string ID to number for static fields
 */
function hashStringToNumber(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  return Math.abs(hash);
}

/**
 * Find available calculation by report calculation
 * This is useful for displaying calculation details in forms
 */
export const findAvailableCalculationByReportCalculation = (
  availableCalculations: AvailableCalculation[],
  reportCalc: ReportCalculation
): AvailableCalculation | undefined => {
  if (reportCalc.calculation_type === 'static') {
    // For static fields, find by the static_ prefix pattern
    return availableCalculations.find(calc => 
      typeof calc.id === 'string' && 
      calc.id.startsWith('static_') &&
      hashStringToNumber(calc.id) === reportCalc.calculation_id
    );
  } else {
    // For user/system calculations, find by numeric ID
    return availableCalculations.find(calc => 
      typeof calc.id === 'number' && 
      calc.id === reportCalc.calculation_id
    );
  }
};

/**
 * Validate calculation selection for report scope
 */
export const validateCalculationCompatibility = (
  calc: AvailableCalculation,
  reportScope: 'DEAL' | 'TRANCHE'
): { isCompatible: boolean; reason?: string } => {
  // Deal-level reports
  if (reportScope === 'DEAL') {
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
  if (reportScope === 'TRANCHE') {
    if (calc.group_level === 'deal' && calc.calculation_type !== 'STATIC_FIELD') {
      return {
        isCompatible: false,
        reason: 'Deal-level calculations are designed for deal-level aggregation only'
      };
    }
  }
  
  return { isCompatible: true };
};

/**
 * Filter calculations by compatibility with report scope
 */
export const filterCalculationsByCompatibility = (
  calculations: AvailableCalculation[],
  reportScope: 'DEAL' | 'TRANCHE'
): { compatible: AvailableCalculation[]; incompatible: AvailableCalculation[] } => {
  const compatible: AvailableCalculation[] = [];
  const incompatible: AvailableCalculation[] = [];
  
  calculations.forEach(calc => {
    const { isCompatible } = validateCalculationCompatibility(calc, reportScope);
    if (isCompatible) {
      compatible.push(calc);
    } else {
      incompatible.push(calc);
    }
  });
  
  return { compatible, incompatible };
};