import type { 
  ReportBuilderFormState, 
  ReportConfig, 
  ReportColumnPreferences,
  AvailableCalculation,
  ReportCalculation
} from '@/types/reporting';
import { ColumnFormat } from '@/types/reporting';

interface ExtendedFormState extends ReportBuilderFormState {
  columnPreferences?: ReportColumnPreferences;
}

export const transformFormDataForApi = (
  formState: ExtendedFormState
): Omit<ReportConfig, 'id' | 'created_date' | 'updated_date'> => {
  const {
    reportName,
    reportDescription,
    reportScope,
    selectedDeals,
    selectedTranches,
    selectedCalculations,
    columnPreferences
  } = formState;

  // Validate required fields
  if (!reportName?.trim()) {
    throw new Error('Report name is required');
  }
  
  if (!reportScope) {
    throw new Error('Report scope is required');
  }

  if (selectedDeals.length === 0) {
    throw new Error('At least one deal must be selected');
  }

  if (selectedCalculations.length === 0) {
    throw new Error('At least one calculation must be selected');
  }

  // Transform selected deals with tranche information
  const transformedDeals = selectedDeals.map(dealNumber => ({
    dl_nbr: dealNumber,
    selected_tranches: selectedTranches[dealNumber]?.map(trancheId => ({
      tr_id: trancheId,
      dl_nbr: dealNumber
    })) || []
  }));

  return {
    name: reportName,
    description: reportDescription || undefined,
    scope: reportScope,
    selected_deals: transformedDeals,
    selected_calculations: selectedCalculations,
    column_preferences: columnPreferences,
    is_active: true
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
 * Updated to handle new calculation_id format
 */
export const convertAvailableCalculationsToReportCalculations = (
  availableCalculations: AvailableCalculation[]
): ReportCalculation[] => {
  return availableCalculations.map((calc, index) => ({
    calculation_id: calc.id, // Now always a string with proper format
    calculation_type: determineCalculationType(calc),
    display_order: index,
    display_name: undefined
  }));
};

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

/**
 * Find available calculation by report calculation
 * Updated for new string-based ID format
 */
export const findAvailableCalculationByReportCalculation = (
  availableCalculations: AvailableCalculation[],
  reportCalc: ReportCalculation
): AvailableCalculation | undefined => {
  // With new format, we can find directly by string ID
  return availableCalculations.find(calc => calc.id === reportCalc.calculation_id);
};

/**
 * Parse calculation ID to extract type and identifier
 * NEW utility function for the new format
 */
export const parseCalculationIdLocal = (calculationId: string): {
  type: 'user' | 'system' | 'static';
  identifier: string;
} => {
  if (calculationId.startsWith('user.')) {
    return {
      type: 'user',
      identifier: calculationId.substring(5) // Remove "user."
    };
  } else if (calculationId.startsWith('system.')) {
    return {
      type: 'system', 
      identifier: calculationId.substring(7) // Remove "system."
    };
  } else if (calculationId.startsWith('static_')) {
    return {
      type: 'static',
      identifier: calculationId.substring(7) // Remove "static_"
    };
  } else {
    console.warn(`Unknown calculation ID format: ${calculationId}`);
    return {
      type: 'user', // fallback
      identifier: calculationId
    };
  }
};

/**
 * Format calculation ID for display
 * NEW utility function
 */
export const formatCalculationIdForDisplay = (calculationId: string): string => {
  const parsed = parseCalculationIdLocal(calculationId);
  
  switch (parsed.type) {
    case 'user':
      return `User: ${parsed.identifier}`;
    case 'system':
      return `System: ${parsed.identifier}`;
    case 'static':
      return `Static: ${parsed.identifier}`;
    default:
      return calculationId;
  }
};

/**
 * Validate calculation selection for report scope
 */
export const validateCalculationCompatibility = (
  calc: AvailableCalculation,
  reportScope: 'DEAL' | 'TRANCHE'
): { isCompatible: boolean; reason?: string } => {
  // Deal-level reports - only allow deal-level calculations
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
  
  // Tranche-level reports - allow BOTH deal and tranche level calculations
  if (reportScope === 'TRANCHE') {
    // CHANGED: Allow deal-level calculations in tranche reports
    // Deal-level static fields, CDI variables, and system SQL are all compatible
    // They will be repeated across tranches within each deal
    return { isCompatible: true };
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

/**
 * Update column preferences when calculations change
 * NEW helper function for managing column preferences
 */
export const updateColumnPreferencesWithNewCalculations = (
  existingPreferences: ReportColumnPreferences,
  newCalculations: ReportCalculation[]
): ReportColumnPreferences => {
  // Get existing column IDs
  const existingColumnIds = new Set(existingPreferences.columns.map(col => col.column_id));
  
  // Find new calculations that aren't already in preferences
  const newCalculationColumns = newCalculations
    .filter(calc => !existingColumnIds.has(calc.calculation_id))
    .map((calc, index) => ({
      column_id: calc.calculation_id, // String ID directly
      display_name: calc.display_name || `Calculation ${calc.calculation_id}`,
      is_visible: true,
      display_order: existingPreferences.columns.length + index,
      format_type: ColumnFormat.TEXT,
      use_rounding: true,
      precision: 2
    }));

  // Remove columns for calculations that no longer exist
  const currentCalculationIds = new Set(newCalculations.map(calc => calc.calculation_id));
  const validExistingColumns = existingPreferences.columns.filter(col => 
    currentCalculationIds.has(col.column_id) || 
    ['deal_number', 'tranche_id', 'cycle_code'].includes(col.column_id) // Keep default columns
  );

  return {
    ...existingPreferences,
    columns: [...validExistingColumns, ...newCalculationColumns]
  };
};

/**
 * Helper function to generate sample formatted data for preview
 */
export const generateFormattedPreview = (
  rawData: any[],
  columnPreferences: ReportColumnPreferences
): any[] => {
  if (!rawData.length || !columnPreferences) {
    return rawData;
  }

  return rawData.map(row => {
    const formattedRow: any = {};
    
    columnPreferences.columns
      .filter(col => col.is_visible)
      .sort((a, b) => a.display_order - b.display_order)
      .forEach(col => {
        const value = row[col.column_id];
        if (value !== undefined && value !== null) {
          formattedRow[col.display_name] = formatValueByType(value, col.format_type);
        } else {
          formattedRow[col.display_name] = '';
        }
      });
    
    return formattedRow;
  });
};

/**
 * Format a value according to its column format type
 */
function formatValueByType(value: any, formatType: ColumnFormat): string {
  if (value === null || value === undefined) return '';
  
  switch (formatType) {
    case ColumnFormat.CURRENCY:
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
      }).format(Number(value) || 0);
      
    case ColumnFormat.PERCENTAGE:
      return new Intl.NumberFormat('en-US', {
        style: 'percent',
        minimumFractionDigits: 2
      }).format((Number(value) || 0) / 100);
      
    case ColumnFormat.NUMBER:
      return new Intl.NumberFormat('en-US').format(Number(value) || 0);
      
    case ColumnFormat.DATE_MDY:
      const dateMDY = new Date(value);
      return dateMDY.toLocaleDateString('en-US');
      
    case ColumnFormat.DATE_DMY:
      const dateDMY = new Date(value);
      return dateDMY.toLocaleDateString('en-GB');
      
    default:
      return String(value);
  }
}