import { useMemo } from 'react';
import type { 
  ReportBuilderFormState, 
  ValidationError, 
  ValidationResult,
  ColumnPreference
} from '@/types/reporting';

interface UseReportBuilderValidationProps {
  formState: ReportBuilderFormState;
  currentStep: number;
}

export const useReportBuilderValidation = ({ formState, currentStep }: UseReportBuilderValidationProps) => {
  
  const validateStep = (step: number): ValidationResult => {
    const errors: ValidationError[] = [];

    switch (step) {
      case 1:
        if (!formState.reportName?.trim()) {
          errors.push({ field: 'reportName', message: 'Report name is required' });
        }
        if (!formState.reportScope) {
          errors.push({ field: 'reportScope', message: 'Report scope is required' });
        }
        break;

      case 2:
        if (formState.selectedDeals.length === 0) {
          errors.push({ field: 'selectedDeals', message: 'At least one deal must be selected' });
        }
        break;

      case 3:
        if (formState.selectedCalculations.length === 0) {
          errors.push({ field: 'selectedCalculations', message: 'At least one calculation must be selected' });
        }
        break;

      case 4:
        // Validate column preferences
        if (formState.columnPreferences) {
          const { columns, include_default_columns } = formState.columnPreferences;
          
          // Check for duplicate display names
          const displayNames = columns.map((col: ColumnPreference) => col.display_name.toLowerCase().trim());
          const duplicates = displayNames.filter((name: string, index: number) => 
            name && displayNames.indexOf(name) !== index
          );
          
          if (duplicates.length > 0) {
            errors.push({
              field: 'columnPreferences',
              message: 'Column display names must be unique'
            });
          }

          // Check for empty display names
          const emptyNames = columns.filter((col: ColumnPreference) => !col.display_name?.trim());
          if (emptyNames.length > 0) {
            errors.push({
              field: 'columnPreferences',
              message: 'All columns must have display names'
            });
          }
          
          // Check that at least one column is visible
          const visibleColumns = columns.filter((col: ColumnPreference) => col.is_visible);
          if (visibleColumns.length === 0 && !include_default_columns) {
            errors.push({
              field: 'columnPreferences',
              message: 'At least one column must be visible in the output'
            });
          }
        }
        break;
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  };

  const currentStepValidation = useMemo(() => 
    validateStep(currentStep), 
    [formState, currentStep]
  );

  const canProceed = currentStepValidation.isValid;

  const hasFieldError = (fieldName: string): boolean => {
    return currentStepValidation.errors.some(error => error.field === fieldName);
  };

  const getFieldErrorMessage = (fieldName: string): string => {
    const error = currentStepValidation.errors.find(error => error.field === fieldName);
    return error ? error.message : '';
  };

  const validateSpecificStep = (step: number): boolean => {
    return validateStep(step).isValid;
  };

  return {
    canProceed,
    hasFieldError,
    getFieldErrorMessage,
    validateSpecificStep,
    currentStepValidation
  };
};