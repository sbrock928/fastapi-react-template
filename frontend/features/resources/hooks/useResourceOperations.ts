// frontend/features/resources/hooks/useResourceOperations.ts
import { useState } from 'react';
import axios from 'axios';
import { useToast } from '@/context/ToastContext';
import type { ResourceConfig } from '@/types/resources';

interface UseResourceOperationsProps {
  resourceConfig: ResourceConfig;
  onSuccess: () => void;
  setFormErrors: (errors: Record<string, string>) => void;
  setValidationState: (summary: string, show: boolean) => void;
  setSubmitError: (hasError: boolean) => void;
}

export const useResourceOperations = ({
  resourceConfig,
  onSuccess,
  setFormErrors,
  setValidationState,
  setSubmitError
}: UseResourceOperationsProps) => {
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const { showToast } = useToast();

  // Prepare payload for API
  const preparePayload = (formData: Record<string, any>) => {
    const payload = { ...formData };
    
    // Remove the ID from the payload for both new and edit requests
    delete payload.id;
    
    // Format dates for API
    resourceConfig.columns.forEach((column: any) => {
      if (column.type === 'datetime-local' && payload[column.field]) {
        // Ensure date is in ISO format
        const date = new Date(payload[column.field]);
        payload[column.field] = date.toISOString();
      }
    });
    
    return payload;
  };

  // Handle API validation errors
  const handleApiErrors = (error: any) => {
    console.error('Error saving resource:', error);
    
    // Set error state so modal retains focus
    setSubmitError(true);
    
    // Show error toast notification
    showToast(`Error: Failed to save ${resourceConfig.displayName}`, 'error');
    
    // Handle validation errors from API
    if (error.response && error.response.data) {
      const apiError = error.response.data;
      
      if (apiError.detail) {
        if (Array.isArray(apiError.detail)) {
          // Handle Pydantic validation errors (422)
          const errors: Record<string, string> = {};
          apiError.detail.forEach((err: any) => {
            const fieldPath = err.loc;
            // Skip the first element which is usually 'body'
            const apiField = fieldPath[fieldPath.length - 1];
            errors[apiField] = err.msg;
          });
          setFormErrors(errors);
        } else if (typeof apiError.detail === 'object') {
          // Handle custom validation errors (400)
          const errors: Record<string, string> = {};
          Object.entries(apiError.detail).forEach(([apiField, message]: [string, any]) => {
            errors[apiField] = message;
          });
          setFormErrors(errors);
        } else {
          // Handle string error messages
          setValidationState(apiError.detail, true);
        }
      } else if (apiError.errors) {
        // Handle validation errors in newer FastAPI/Pydantic versions
        const errors: Record<string, string> = {};
        apiError.errors.forEach((err: any) => {
          if (err.loc && err.loc.length > 0) {
            // Skip the first element which is usually 'body'
            const apiField = err.loc[err.loc.length - 1];
            errors[apiField] = err.msg;
          }
        });
        setFormErrors(errors);
      } else {
        setValidationState('An unexpected error occurred', true);
      }
    }
  };

  // Save new resource
  const saveResource = async (formData: Record<string, any>): Promise<boolean> => {
    setIsSubmitting(true);
    setSubmitError(false);
    
    try {
      const payload = preparePayload(formData);
      const response = await axios.post(`/api${resourceConfig.apiEndpoint}`, payload);
      
      // Only notify parent if successful (status 200 or 201)
      if (response.status === 200 || response.status === 201) {
        showToast(`Successfully created new ${resourceConfig.displayName}`, 'success');
        onSuccess();
        return true;
      }
      return false;
    } catch (error: any) {
      handleApiErrors(error);
      return false;
    } finally {
      setIsSubmitting(false);
    }
  };

  // Update existing resource
  const updateResource = async (resourceId: string | number, formData: Record<string, any>): Promise<boolean> => {
    setIsSubmitting(true);
    setSubmitError(false);
    
    try {
      const payload = preparePayload(formData);
      const response = await axios.patch(`/api${resourceConfig.apiEndpoint}/${resourceId}`, payload);
      
      // Only notify parent if successful (status 200 or 201)
      if (response.status === 200 || response.status === 201) {
        showToast(`Successfully updated ${resourceConfig.displayName}`, 'success');
        onSuccess();
        return true;
      }
      return false;
    } catch (error: any) {
      handleApiErrors(error);
      return false;
    } finally {
      setIsSubmitting(false);
    }
  };

  // Save or update based on mode
  const saveOrUpdateResource = async (
    formData: Record<string, any>, 
    editingResource?: any | null
  ): Promise<boolean> => {
    if (editingResource) {
      return await updateResource(editingResource.id, formData);
    } else {
      return await saveResource(formData);
    }
  };

  return {
    isSubmitting,
    saveResource,
    updateResource,
    saveOrUpdateResource
  };
};