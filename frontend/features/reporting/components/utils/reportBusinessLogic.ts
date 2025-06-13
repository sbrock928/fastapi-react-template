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

  // Transform deals with their selected tranches
  const selected_deals = selectedDeals.map(dlNbr => ({
    dl_nbr: dlNbr,
    selected_tranches: (selectedTranches[dlNbr] || []).map(trId => ({
      tr_id: trId,
      dl_nbr: dlNbr
    }))
  }));

  // Ensure column preferences are valid if provided
  let validatedColumnPreferences: ReportColumnPreferences | undefined = columnPreferences;
  
  if (columnPreferences) {
    // Validate and clean column preferences
    const cleanedColumns = columnPreferences.columns
      .filter(col => col.display_name?.trim()) // Remove columns without names
      .map((col, index) => ({
        ...col,
        display_name: col.display_name.trim(),
        display_order: index // Ensure sequential ordering
      }));

    validatedColumnPreferences = {
      ...columnPreferences,
      columns: cleanedColumns
    };

    // Ensure at least one column is visible or default columns are included
    const hasVisibleColumns = cleanedColumns.some(col => col.is_visible);
    if (!hasVisibleColumns && !columnPreferences.include_default_columns) {
      validatedColumnPreferences.include_default_columns = true;
    }
  }

  return {
    name: reportName.trim(),
    description: reportDescription?.trim() || undefined,
    scope: reportScope as 'DEAL' | 'TRANCHE',
    selected_deals,
    selected_calculations: selectedCalculations,
    column_preferences: validatedColumnPreferences,
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
 * This helps when editing existing reports
 */
export const convertAvailableCalculationsToReportCalculations = (
  availableCalculations: AvailableCalculation[]
): ReportCalculation[] => {
  return availableCalculations.map((calc, index) => ({
    calculation_id: typeof calc.id === 'string' ? calc.id : calc.id, // Keep string IDs as strings!
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
 * Find available calculation by report calculation
 * This is useful for displaying calculation details in forms
 */
export const findAvailableCalculationByReportCalculation = (
  availableCalculations: AvailableCalculation[],
  reportCalc: ReportCalculation
): AvailableCalculation | undefined => {
  if (reportCalc.calculation_type === 'static') {
    // For static fields, find by string ID directly (no more hashing)
    return availableCalculations.find(calc => 
      typeof calc.id === 'string' && 
      calc.id === reportCalc.calculation_id
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

/**
 * Helper function to validate column preferences
 */
export const validateColumnPreferences = (
  preferences: ReportColumnPreferences
): { isValid: boolean; errors: string[] } => {
  const errors: string[] = [];

  // Check for duplicate display names
  const displayNames = preferences.columns.map(col => col.display_name.toLowerCase().trim());
  const duplicates = displayNames.filter((name, index) => 
    name && displayNames.indexOf(name) !== index
  );
  
  if (duplicates.length > 0) {
    errors.push('Column display names must be unique');
  }

  // Check for empty display names
  const emptyNames = preferences.columns.filter(col => !col.display_name?.trim());
  if (emptyNames.length > 0) {
    errors.push('All columns must have display names');
  }

  // Check that at least one column is visible
  const visibleColumns = preferences.columns.filter(col => col.is_visible);
  if (visibleColumns.length === 0 && !preferences.include_default_columns) {
    errors.push('At least one column must be visible in the output');
  }

  return {
    isValid: errors.length === 0,
    errors
  };
};

/**
 * Helper function to merge column preferences when editing reports
 */
export const mergeColumnPreferences = (
  existingPreferences: ReportColumnPreferences | undefined,
  newCalculations: any[],
  reportScope: 'DEAL' | 'TRANCHE'
): ReportColumnPreferences => {
  if (!existingPreferences) {
    // Create new preferences from scratch
    const { getDefaultColumnPreferences } = require('@/types/reporting');
    return getDefaultColumnPreferences(newCalculations, reportScope, true);
  }

  // Get existing column IDs
  const existingColumnIds = new Set(existingPreferences.columns.map(col => col.column_id));
  
  // Find new calculations that don't have column preferences yet
  const newCalculationColumns = newCalculations
    .filter(calc => !existingColumnIds.has(String(calc.calculation_id)))
    .map((calc, index) => ({
      column_id: String(calc.calculation_id),
      display_name: calc.display_name || `Calculation ${calc.calculation_id}`,
      is_visible: true,
      display_order: existingPreferences.columns.length + index,
      format_type: ColumnFormat.TEXT
    }));

  // Remove columns for calculations that no longer exist
  const currentCalculationIds = new Set(newCalculations.map(calc => String(calc.calculation_id)));
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

    // Apply column preferences
    columnPreferences.columns
      .filter(col => col.is_visible)
      .sort((a, b) => a.display_order - b.display_order)
      .forEach(colPref => {
        const originalValue = row[colPref.column_id];
        const displayName = colPref.display_name;
        
        // Apply formatting based on format type
        let formattedValue = originalValue;
        
        if (originalValue !== null && originalValue !== undefined) {
          switch (colPref.format_type) {
            case ColumnFormat.CURRENCY:
              if (typeof originalValue === 'number') {
                formattedValue = `$${originalValue.toLocaleString('en-US', { 
                  minimumFractionDigits: 2, 
                  maximumFractionDigits: 2 
                })}`;
              }
              break;
              
            case ColumnFormat.PERCENTAGE:
              if (typeof originalValue === 'number') {
                formattedValue = `${originalValue.toFixed(1)}%`;
              }
              break;
              
            case ColumnFormat.NUMBER:
              if (typeof originalValue === 'number') {
                formattedValue = originalValue.toLocaleString('en-US');
              }
              break;
              
            case ColumnFormat.DATE_MDY:
              if (originalValue instanceof Date) {
                formattedValue = originalValue.toLocaleDateString('en-US');
              } else if (typeof originalValue === 'string') {
                try {
                  const date = new Date(originalValue);
                  formattedValue = date.toLocaleDateString('en-US');
                } catch {
                  // Keep original value if parsing fails
                }
              }
              break;
              
            case ColumnFormat.DATE_DMY:
              if (originalValue instanceof Date) {
                formattedValue = originalValue.toLocaleDateString('en-GB');
              } else if (typeof originalValue === 'string') {
                try {
                  const date = new Date(originalValue);
                  formattedValue = date.toLocaleDateString('en-GB');
                } catch {
                  // Keep original value if parsing fails
                }
              }
              break;
              
            default:
              // TEXT format - keep as is
              break;
          }
        }
        
        formattedRow[displayName] = formattedValue;
      });

    return formattedRow;
  });
};