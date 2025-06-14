import type { ReportCalculation } from '@/types/reporting';

// Updated form state interface for calculations
export interface ReportBuilderFormState {
  reportName: string;
  reportDescription: string;
  reportScope: 'DEAL' | 'TRANCHE' | '';
  selectedDeals: number[];
  selectedTranches: Record<number, string[]>;
  selectedCalculations: ReportCalculation[]; // Changed from selectedFields
}

export interface ValidationError {
  field: string;
  message: string;
}

export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
}

// Validation rules for each step
export const validationRules = {
  step1: (formState: ReportBuilderFormState): ValidationResult => {
    const errors: ValidationError[] = [];

    if (!formState.reportName.trim()) {
      errors.push({
        field: 'reportName',
        message: 'Report name is required'
      });
    }

    if (formState.reportName.trim().length < 3) {
      errors.push({
        field: 'reportName',
        message: 'Report name must be at least 3 characters long'
      });
    }

    if (!formState.reportScope) {
      errors.push({
        field: 'reportScope',
        message: 'Report scope is required'
      });
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  },

  step2: (formState: ReportBuilderFormState): ValidationResult => {
    const errors: ValidationError[] = [];

    if (formState.selectedDeals.length === 0) {
      errors.push({
        field: 'selectedDeals',
        message: 'At least one deal must be selected'
      });
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  },

  step3: (formState: ReportBuilderFormState): ValidationResult => {
    const errors: ValidationError[] = [];

    // Only validate for TRANCHE scope reports
    if (formState.reportScope === 'TRANCHE') {
      const hasSelectedTranches = Object.values(formState.selectedTranches)
        .some((tranches: string[]) => tranches && tranches.length > 0);

      if (!hasSelectedTranches) {
        errors.push({
          field: 'selectedTranches',
          message: 'At least one tranche must be selected for tranche-level reports'
        });
      }
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  },

  step4: (formState: ReportBuilderFormState): ValidationResult => {
    const errors: ValidationError[] = [];

    if (formState.selectedCalculations.length === 0) {
      errors.push({
        field: 'selectedCalculations', // Changed from selectedFields
        message: 'At least one calculation must be selected'
      });
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  },

  step5: (formState: ReportBuilderFormState): ValidationResult => {
    // Final validation - run all previous validations
    const step1Result = validationRules.step1(formState);
    const step2Result = validationRules.step2(formState);
    const step3Result = validationRules.step3(formState);
    const step4Result = validationRules.step4(formState);

    const allErrors = [
      ...step1Result.errors,
      ...step2Result.errors,
      ...step3Result.errors,
      ...step4Result.errors
    ];

    return {
      isValid: allErrors.length === 0,
      errors: allErrors
    };
  }
};

// Helper function to get validation for current step
export const validateStep = (step: number, formState: ReportBuilderFormState): ValidationResult => {
  switch (step) {
    case 1:
      return validationRules.step1(formState);
    case 2:
      return validationRules.step2(formState);
    case 3:
      return validationRules.step3(formState);
    case 4:
      return validationRules.step4(formState);
    case 5:
      return validationRules.step5(formState);
    default:
      return { isValid: false, errors: [] };
  }
};

// Helper function to check if user can proceed to next step
export const canProceedToNextStep = (currentStep: number, formState: ReportBuilderFormState): boolean => {
  // For step 3, skip validation if report scope is DEAL
  if (currentStep === 3 && formState.reportScope === 'DEAL') {
    return true;
  }

  const validation = validateStep(currentStep, formState);
  return validation.isValid;
};