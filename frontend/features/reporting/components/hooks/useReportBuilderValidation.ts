import { useState, useEffect } from 'react';
import { validateStep, canProceedToNextStep } from '../validation/validationRules';
import type { ValidationError, ValidationResult } from '../validation/validationRules';
import type { ReportBuilderFormState } from './useReportBuilderForm';

interface UseReportBuilderValidationProps {
  formState: ReportBuilderFormState;
  currentStep: number;
}

export const useReportBuilderValidation = ({ formState, currentStep }: UseReportBuilderValidationProps) => {
  const [errors, setErrors] = useState<ValidationError[]>([]);
  const [isValid, setIsValid] = useState<boolean>(true);

  // Validate current step whenever form state or step changes
  useEffect(() => {
    const validation = validateStep(currentStep, formState);
    setErrors(validation.errors);
    setIsValid(validation.isValid);
  }, [formState, currentStep]);

  // Check if user can proceed to next step
  const canProceed = canProceedToNextStep(currentStep, formState);

  // Get errors for a specific field
  const getFieldErrors = (fieldName: string): ValidationError[] => {
    return errors.filter(error => error.field === fieldName);
  };

  // Check if a specific field has errors
  const hasFieldError = (fieldName: string): boolean => {
    return getFieldErrors(fieldName).length > 0;
  };

  // Get the first error message for a field
  const getFieldErrorMessage = (fieldName: string): string | null => {
    const fieldErrors = getFieldErrors(fieldName);
    return fieldErrors.length > 0 ? fieldErrors[0].message : null;
  };

  // Validate a specific step (useful for manual validation)
  const validateSpecificStep = (step: number): ValidationResult => {
    return validateStep(step, formState);
  };

  // Clear all errors
  const clearErrors = () => {
    setErrors([]);
    setIsValid(true);
  };

  // Get validation summary for display
  const getValidationSummary = (): string => {
    if (errors.length === 0) return '';
    if (errors.length === 1) return errors[0].message;
    return `${errors.length} validation errors found`;
  };

  return {
    // Current validation state
    errors,
    isValid,
    canProceed,

    // Field-specific helpers
    getFieldErrors,
    hasFieldError,
    getFieldErrorMessage,

    // Utility functions
    validateSpecificStep,
    clearErrors,
    getValidationSummary
  };
};