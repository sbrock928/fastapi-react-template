import { useState, useEffect, useRef } from 'react';
import axios from 'axios';

interface ResourceModalProps {
  resourceType: string;
  resourceConfig: any;
  onClose: () => void;
  onSave: () => void;
  editingResource?: any | null;
}

const ResourceModal = ({ 
  resourceConfig, 
  onClose, 
  onSave,
  editingResource = null 
}: ResourceModalProps) => {
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [validationSummary, setValidationSummary] = useState<string>('Please fix the validation errors below.');
  const [showValidationSummary, setShowValidationSummary] = useState<boolean>(false);
  
  const modalRef = useRef<HTMLDivElement>(null);
  const bootstrapModalRef = useRef<any>(null);
  
  // Initialize form data when the component mounts or editingResource changes
  useEffect(() => {
    if (editingResource) {
      setFormData({...editingResource});
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
      setFormData(initialData);
    }
  }, [editingResource, resourceConfig]);

  // Initialize Bootstrap modal
  useEffect(() => {
    if (modalRef.current) {
      // Create and show a new Bootstrap modal
      // @ts-ignore - Bootstrap is loaded globally
      bootstrapModalRef.current = new window.bootstrap.Modal(modalRef.current);
      bootstrapModalRef.current.show();
      
      // Add event listener for when modal is hidden
      modalRef.current.addEventListener('hidden.bs.modal', onClose);
    }
    
    return () => {
      if (bootstrapModalRef.current) {
        bootstrapModalRef.current.dispose();
      }
      if (modalRef.current) {
        modalRef.current.removeEventListener('hidden.bs.modal', onClose);
      }
    };
  }, [onClose]);

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
      
      // Minimum length validation
      else if (column.minLength && typeof value === 'string' && value.trim().length < column.minLength) {
        errors[column.field] = `${column.header} must be at least ${column.minLength} characters`;
        isValid = false;
      }
      
      // Pattern validation
      else if (column.pattern && typeof value === 'string' && value.trim() !== '' && !new RegExp(column.pattern).test(value)) {
        errors[column.field] = `${column.header} must match pattern: ${column.pattern}`;
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    try {
      const payload = {...formData};
      
      // Remove the ID from the payload for both new and edit requests
      // The ID should be in the URL for edit requests, not in the payload
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
        await axios.patch(`/api${resourceConfig.apiEndpoint}/${editingResource.id}`, payload);
      } else {
        // Create new resource
        await axios.post(`/api${resourceConfig.apiEndpoint}`, payload);
      }
      
      // Close modal and notify parent of the specific resource type that was changed
      if (bootstrapModalRef.current) {
        bootstrapModalRef.current.hide();
      }
      // Pass the resource type that was modified so parent can selectively refresh
      onSave();
      
    } catch (error: any) {
      console.error('Error saving resource:', error);
      
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
    >
      <div className="modal-dialog">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title" id="resourceModalLabel">
              {editingResource ? `Edit ${resourceConfig.displayName}` : `Add ${resourceConfig.displayName}`}
            </h5>
            <button 
              type="button" 
              className="btn-close" 
              data-bs-dismiss="modal" 
              aria-label="Close"
            ></button>
          </div>
          <div className="modal-body">
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
              data-bs-dismiss="modal"
            >
              Cancel
            </button>
            <button 
              type="button" 
              className="btn btn-primary"
              onClick={handleSubmit}
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ResourceModal;
