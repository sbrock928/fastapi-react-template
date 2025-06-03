// frontend/features/resources/hooks/useResourceForm.ts
import { useState, useEffect } from 'react';
import type { ResourceConfig } from '@/types/resources';

export interface ResourceFormState {
  formData: Record<string, any>;
  formErrors: Record<string, string>;
  validationSummary: string;
  showValidationSummary: boolean;
  hasSubmitError: boolean;
}

interface UseResourceFormProps {
  resourceConfig: ResourceConfig;
  editingResource?: any | null;
  isEditMode: boolean;
}

export const useResourceForm = ({ 
  resourceConfig, 
  editingResource, 
  isEditMode 
}: UseResourceFormProps) => {
  const [formState, setFormState] = useState<ResourceFormState>({
    formData: {},
    formErrors: {},
    validationSummary: 'Please fix the validation errors below.',
    showValidationSummary: false,
    hasSubmitError: false
  });

  // Initialize form data when component mounts or editingResource changes
  useEffect(() => {
    if (isEditMode && editingResource) {
      setFormState(prev => ({
        ...prev,
        formData: { ...editingResource }
      }));
    } else {
      // Initialize with default values
      const initialData: Record<string, any> = {};
      resourceConfig.columns.forEach((column: any) => {
        if (column.type === 'checkbox') {
          // Default checkboxes to true for specific fields
          if (column.field === 'is_active') {
            initialData[column.field] = true;
          } else {
            initialData[column.field] = false;
          }
        } else if (column.type === 'select' && column.options && column.options.length > 0) {
          // For subscription_tier, default to 'free'
          if (column.field === 'subscription_tier') {
            initialData[column.field] = 'free';
          } else {
            initialData[column.field] = column.options[0].value;
          }
        } else if (column.type === 'datetime-local') {
          // Initialize datetime fields with current time
          if (column.field === 'signup_date') {
            const now = new Date();
            const isoString = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
                .toISOString()
                .substring(0, 19);
            initialData[column.field] = isoString;
          } else {
            initialData[column.field] = '';
          }
        } else {
          initialData[column.field] = '';
        }
      });
      
      setFormState(prev => ({
        ...prev,
        formData: initialData,
        formErrors: {},
        showValidationSummary: false,
        hasSubmitError: false
      }));
    }
  }, [editingResource, resourceConfig, isEditMode]);

  // Update form field
  const updateField = (name: string, value: any) => {
    setFormState(prev => {
      // Clear error when user makes changes by creating new object without the error
      const newFormErrors = { ...prev.formErrors };
      delete newFormErrors[name];
      
      return {
        ...prev,
        formData: {
          ...prev.formData,
          [name]: value
        },
        formErrors: newFormErrors
      };
    });
  };

  // Set form errors
  const setFormErrors = (errors: Record<string, string>) => {
    setFormState(prev => ({
      ...prev,
      formErrors: errors
    }));
  };

  // Set validation summary
  const setValidationState = (summary: string, show: boolean) => {
    setFormState(prev => ({
      ...prev,
      validationSummary: summary,
      showValidationSummary: show
    }));
  };

  // Set submit error state
  const setSubmitError = (hasError: boolean) => {
    setFormState(prev => ({
      ...prev,
      hasSubmitError: hasError
    }));
  };

  // Validate form
  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};
    let isValid = true;
    
    resourceConfig.columns.forEach((column: any) => {
      // Skip ID field
      if (column.field === 'id') return;
      
      const value = formState.formData[column.field];
      
      // Required field validation
      if (column.required && (!value || (typeof value === 'string' && value.trim() === ''))) {
        errors[column.field] = `${column.header} is required`;
        isValid = false;
      }
    });
    
    if (!isValid) {
      setValidationState('Please fix the validation errors below.', true);
    } else {
      setValidationState('', false);
    }
    
    setFormErrors(errors);
    return isValid;
  };

  // Reset form
  const resetForm = () => {
    setFormState({
      formData: {},
      formErrors: {},
      validationSummary: 'Please fix the validation errors below.',
      showValidationSummary: false,
      hasSubmitError: false
    });
  };

  // Handle input change (can be used by components)
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target as HTMLInputElement;
    
    if (type === 'checkbox') {
      const checked = (e.target as HTMLInputElement).checked;
      updateField(name, checked);
    } else {
      updateField(name, value);
    }
  };

  return {
    // State
    formData: formState.formData,
    formErrors: formState.formErrors,
    validationSummary: formState.validationSummary,
    showValidationSummary: formState.showValidationSummary,
    hasSubmitError: formState.hasSubmitError,
    
    // Actions
    updateField,
    setFormErrors,
    setValidationState,
    setSubmitError,
    validateForm,
    resetForm,
    handleInputChange
  };
};