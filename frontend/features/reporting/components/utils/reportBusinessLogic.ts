import type { ReportBuilderFormState } from '../hooks/useReportBuilderForm';

/**
 * Transform form state data into the format expected by the API (simplified structure)
 */
export const transformFormDataForApi = (formState: ReportBuilderFormState) => {
  const { selectedDeals, selectedTranches, selectedCalculations, reportName, reportDescription, reportScope } = formState;

  // Updated to remove redundant dl_nbr from tranches
  const transformedSelectedDeals = selectedDeals.map((dlNbr: number) => ({
    dl_nbr: dlNbr,
    selected_tranches: (selectedTranches[dlNbr] || []).map((trId: string) => ({
      tr_id: trId  // Removed dl_nbr - backend will infer from parent deal
    }))
  }));

  return {
    name: reportName,
    description: reportDescription || undefined,
    scope: reportScope as 'DEAL' | 'TRANCHE',
    selected_deals: transformedSelectedDeals,
    selected_calculations: selectedCalculations.map((calc, index) => ({
      calculation_id: calc.calculation_id,
      display_order: calc.display_order ?? index,
      display_name: calc.display_name || undefined
    }))
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

  if (formState.reportScope === 'TRANCHE') {
    const hasSelectedTranches = Object.values(formState.selectedTranches)
      .some((tranches: string[]) => tranches && tranches.length > 0);
    
    if (!hasSelectedTranches) {
      errors.push('At least one tranche must be selected for tranche-level reports');
    }
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