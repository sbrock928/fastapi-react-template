import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import useModal from '@/hooks/useModal';
import { useToast } from '@/context/ToastContext';

interface ResourceModalProps {
  resourceType: string;
  resourceConfig: any;
  editingResource?: any | null;
  show: boolean;
  onClose: () => void;
  onSave: () => void;
}

const ResourceModal = ({ 
  resourceConfig, 
  onClose, 
  onSave,
  editingResource = null,
  show 
}: ResourceModalProps) => {
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [validationSummary, setValidationSummary] = useState<string>('Please fix the validation errors below.');
  const [showValidationSummary, setShowValidationSummary] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [hasSubmitError, setHasSubmitError] = useState<boolean>(false);
  const modalMounted = useRef(false);
  
  // New state for dynamic options and loading state
  const [dynamicOptions, setDynamicOptions] = useState<Record<string, any[]>>({});
  const [loadingFields, setLoadingFields] = useState<Record<string, boolean>>({});
  
  // Use the toast context
  const { showToast } = useToast();
  
  // Use the useModal hook to handle the Bootstrap modal
  const { modalRef, closeModal } = useModal(show, onClose);
  
  // Mark when modal is mounted
  useEffect(() => {
    modalMounted.current = true;
    return () => {
      modalMounted.current = false;
    };
  }, []);
  
  // Handle modal container click to isolate its event bubble
  const handleModalClick = useCallback((e: React.MouseEvent) => {
    // Prevent event propagation from modal dialog clicks
    e.stopPropagation();
  }, []);
  
  // Handle manual close of the modal
  const handleClose = useCallback((e: React.MouseEvent) => {
    // Prevent default behavior
    e.preventDefault();
    // Stop event propagation
    e.stopPropagation();
    // Use our direct closeModal function to ensure the modal closes
    closeModal();
  }, [closeModal]);

  // Fetch dependent options based on parent field value
  const fetchDependentOptions = async (parentField: string, parentValue: string) => {
    // Find all fields that depend on this parent
    resourceConfig.columns.forEach(async (column: any) => {
      if (column.dependsOn === parentField) {
        try {
          // Set loading state for this field
          setLoadingFields(prev => ({ ...prev, [column.field]: true }));
          
          // Clear previous options
          setDynamicOptions(prev => ({ 
            ...prev, 
            [column.field]: [] 
          }));
          
          // Clear the field value
          setFormData(prev => ({
            ...prev,
            [column.field]: ''
          }));

          // Different endpoints based on dependency type
          let endpoint = '';
          if (parentField === 'department' && column.field === 'position') {
            endpoint = `/api/departments/${encodeURIComponent(parentValue)}/positions`;
          }
          // Add more conditions for other dependent fields as needed

          if (endpoint) {
            const response = await axios.get(endpoint);
            if (response.data) {
              setDynamicOptions(prev => ({
                ...prev,
                [column.field]: response.data
              }));
            }
          }
        } catch (error) {
          console.error(`Error fetching dependent options for ${column.field}:`, error);
          showToast(`Failed to load options for ${column.header}`, 'error');
        } finally {
          setLoadingFields(prev => ({ ...prev, [column.field]: false }));
        }
      }
    });
  };

  // Initialize form data when the component mounts or editingResource changes
  useEffect(() => {
    if (editingResource) {
      setFormData({...editingResource});
      
      // If editing, also fetch any dependent fields' options
      resourceConfig.columns.forEach((column: any) => {
        if (column.hasDependents && editingResource[column.field]) {
          fetchDependentOptions(column.field, editingResource[column.field]);
        }
      });
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
          
          // If this field has dependents, trigger fetching dependent options
          if (column.hasDependents) {
            fetchDependentOptions(column.field, column.options[0].value);
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
      setFormData(initialData);
    }
  }, [editingResource, resourceConfig]);

  // Handle form input changes
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target as HTMLInputElement;
    
    if (type === 'checkbox') {
      const checked = (e.target as HTMLInputElement).checked;
      setFormData(prev => ({
        ...prev,
        [name]: checked
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
      
      // Check if this field has dependencies
      const column = resourceConfig.columns.find((col: any) => col.field === name);
      if (column?.hasDependents && value) {
        // Fetch dependent options when parent value changes
        fetchDependentOptions(name, value);
      }
    }
    
    // Clear error when user makes changes
    if (formErrors[name]) {
      setFormErrors(prev => {
        const newErrors = {...prev};
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  // Validate form data
  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};
    let isValid = true;
    
    resourceConfig.columns.forEach((column: any) => {
      // Skip ID field
      if (column.field === 'id') return;
      
      const value = formData[column.field];
      
      // Required field validation
      if (column.required && (!value || (typeof value === 'string' && value.trim() === ''))) {
        errors[column.field] = `${column.header} is required`;
        isValid = false;
      }
      
    });
    
    if (!isValid) {
      setShowValidationSummary(true);
    } else {
      setShowValidationSummary(false);
    }
    
    setFormErrors(errors);
    return isValid;
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      setHasSubmitError(true);
      return;
    }

    // Set submitting state to true at the start
    setIsSubmitting(true);
    setHasSubmitError(false);
    
    try {
      const payload = {...formData};
      
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
      
      if (editingResource) {
        // Update existing resource
        const response = await axios.patch(`/api${resourceConfig.apiEndpoint}/${editingResource.id}`, payload);
        // Only notify parent if successful (status 200 or 201)
        if (response.status === 200 || response.status === 201) {
          // Show success toast notification
          showToast(`Successfully updated ${resourceConfig.displayName}`, 'success');
          
          // Clear the form data
          setFormData({});
          // Reset any form errors
          setFormErrors({});
          setShowValidationSummary(false);
          
          // Let parent component handle modal closing completely
          onSave();
        }
      } else {
        // Create new resource
        const response = await axios.post(`/api${resourceConfig.apiEndpoint}`, payload);
        // Only notify parent if successful (status 200 or 201)
        if (response.status === 200 || response.status === 201) {
          // Show success toast notification
          showToast(`Successfully created new ${resourceConfig.displayName}`, 'success');
          
          // Clear the form data
          setFormData({});
          // Reset any form errors
          setFormErrors({});
          setShowValidationSummary(false);
          
          // IMPORTANT: Only call onSave() - do NOT call onClose() here
          // Let the parent component handle the state changes
          onSave();
        }
      }
      
    } catch (error: any) {
      console.error('Error saving resource:', error);
      
      // Set error state so modal retains focus
      setHasSubmitError(true);
      
      // Show error toast notification
      showToast(`Error: Failed to save ${resourceConfig.displayName}`, 'error');
      
      // Handle validation errors from API
      if (error.response && error.response.data) {
        const apiError = error.response.data;
        
        if (apiError.detail) {
          if (Array.isArray(apiError.detail)) {
            // Handle Pydantic validation errors (422)
            apiError.detail.forEach((err: any) => {
              const fieldPath = err.loc;
              // Skip the first element which is usually 'body'
              const apiField = fieldPath[fieldPath.length - 1];
              setFormErrors(prev => ({
                ...prev,
                [apiField]: err.msg
              }));
            });
          } else if (typeof apiError.detail === 'object') {
            // Handle custom validation errors (400)
            Object.entries(apiError.detail).forEach(([apiField, message]: [string, any]) => {
              setFormErrors(prev => ({
                ...prev,
                [apiField]: message
              }));
            });
          } else {
            // Handle string error messages
            setValidationSummary(apiError.detail);
            setShowValidationSummary(true);
          }
        } else if (apiError.errors) {
          // Handle validation errors in newer FastAPI/Pydantic versions
          apiError.errors.forEach((err: any) => {
            if (err.loc && err.loc.length > 0) {
              // Skip the first element which is usually 'body'
              const apiField = err.loc[err.loc.length - 1];
              setFormErrors(prev => ({
                ...prev,
                [apiField]: err.msg
              }));
            }
          });
        } else {
          setValidationSummary('An unexpected error occurred');
          setShowValidationSummary(true);
        }
      } else {
        alert('An error occurred while saving. Please try again.');
      }
    } finally {
      // Always set submitting to false when the operation completes
      setIsSubmitting(false);
    }
  };

  const renderFormField = (column: any) => {
    if (column.field === 'id') return null; // Don't show ID field in the form
    
    const error = formErrors[column.field];
    
    if (column.type === 'checkbox') {
      return (
        <div className="mb-3 form-check" key={column.field}>
          <input 
            id={column.field}
            name={column.field}
            type="checkbox"
            className={`form-check-input ${error ? 'is-invalid' : ''}`}
            checked={!!formData[column.field]}
            onChange={handleInputChange}
            required={column.required}
          />
          <label className="form-check-label" htmlFor={column.field}>
            {column.header}
          </label>
          {error && <div className="invalid-feedback">{error}</div>}
        </div>
      );
    } else {
      // Handle dependent fields
      if (column.dependsOn) {
        const isLoading = loadingFields[column.field];
        const options = dynamicOptions[column.field] || [];
        const parentField = column.dependsOn;
        const parentValue = formData[parentField];
        const disabled = !parentValue || isLoading;
        
        return (
          <div className="mb-3" key={column.field}>
            <label htmlFor={column.field} className="form-label">
              {column.header} {column.required && <span className="text-danger">*</span>}
            </label>
            <select
              id={column.field}
              name={column.field}
              className={`form-select ${error ? 'is-invalid' : ''}`}
              value={formData[column.field] || ''}
              onChange={handleInputChange}
              required={column.required}
              disabled={disabled}
            >
              <option value="">{isLoading ? 'Loading...' : `Select ${column.header}`}</option>
              {!isLoading && options.map((option: any) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            {error && <div className="invalid-feedback">{error}</div>}
          </div>
        );
      }
      
      return (
        <div className="mb-3" key={column.field}>
          <label htmlFor={column.field} className="form-label">
            {column.header} {column.required && <span className="text-danger">*</span>}
          </label>
          
          {column.type === 'select' ? (
            <select 
              id={column.field}
              name={column.field}
              className={`form-select ${error ? 'is-invalid' : ''}`}
              value={formData[column.field] || ''}
              onChange={handleInputChange}
              required={column.required}
            >
              <option value="">Select {column.header}</option>
              {column.options?.map((option: any) => (
                <option key={option.value} value={option.value}>
                  {option.text}
                </option>
              ))}
            </select>
          ) : (
            <input 
              id={column.field}
              name={column.field}
              type={column.type}
              className={`form-control ${error ? 'is-invalid' : ''}`}
              value={formData[column.field] || ''}
              onChange={handleInputChange}
              required={column.required}
              minLength={column.minLength}
              pattern={column.pattern}
              placeholder={column.placeholder}
              step={column.type === 'datetime-local' ? 1 : undefined} // Allow seconds in datetime-local
            />
          )}
          
          {error && <div className="invalid-feedback">{error}</div>}
        </div>
      );
    }
  };

  return (
    <div 
      className="modal fade" 
      tabIndex={-1}
      aria-labelledby="resourceModalLabel"
      aria-hidden="true"
      ref={modalRef}
      onClick={handleModalClick}
      data-bs-backdrop="static"
      data-bs-keyboard="false"
    >
      <div className="modal-dialog">
        <div className="modal-content">
          <div className="modal-header text-white" style={{ backgroundColor: '#93186C' }}>
            <h5 className="modal-title" id="resourceModalLabel">
              {editingResource ? `Edit ${resourceConfig.displayName}` : `Add ${resourceConfig.displayName}`}
            </h5>
            <button 
              type="button" 
              className="btn-close btn-close-white" 
              onClick={handleClose}
              aria-label="Close"
            ></button>
          </div>
          <div className={`modal-body ${hasSubmitError ? 'modal-body-error' : ''}`}>
            {/* Validation Summary */}
            {showValidationSummary && (
              <div 
                className="alert alert-danger" 
                role="alert"
              >
                {validationSummary}
              </div>
            )}
            
            <form onSubmit={handleSubmit}>
              <input type="hidden" name="id" value={editingResource?.id || ''} />
              
              <div>
                {resourceConfig.columns.map(renderFormField)}
              </div>
            </form>
          </div>
          <div className="modal-footer">
            <button 
              type="button" 
              className="btn btn-secondary" 
              onClick={handleClose}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button 
              type="button" 
              className="btn btn-primary"
              onClick={handleSubmit}
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                  Saving...
                </>
              ) : (
                'Save'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ResourceModal;
