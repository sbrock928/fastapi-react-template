// frontend/features/resources/components/ResourceModalRefactored.tsx
import React, { useEffect, useRef, useCallback } from 'react';
import useModal from '@/hooks/useModal';
import { useResourceForm, useDependentFields, useResourceOperations } from '../hooks';
import styles from '@/styles/components/ResourceModal.module.css';

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
  const modalMounted = useRef(false);
  const isEditMode = !!editingResource;
  
  // Use the useModal hook to handle the Bootstrap modal
  const { modalRef, closeModal } = useModal(show, onClose);
  
  // Form management hook
  const {
    formData,
    formErrors,
    validationSummary,
    showValidationSummary,
    hasSubmitError,
    updateField,
    setFormErrors,
    setValidationState,
    setSubmitError,
    validateForm,
    resetForm
  } = useResourceForm({ resourceConfig, editingResource, isEditMode });

  // Dependent fields hook
  const {
    dynamicOptions,
    loadingFields,
    fetchDependentOptions,
    handleFieldChangeWithDependencies,
    isDependentField,
    getParentField
  } = useDependentFields({ resourceConfig, updateField });

  // Resource operations hook
  const {
    isSubmitting,
    saveOrUpdateResource
  } = useResourceOperations({
    resourceConfig,
    onSuccess: onSave,
    setFormErrors,
    setValidationState,
    setSubmitError
  });
  
  // Mark when modal is mounted
  useEffect(() => {
    modalMounted.current = true;
    return () => {
      modalMounted.current = false;
    };
  }, []);

  // Load dependent options for edit mode
  useEffect(() => {
    if (isEditMode && editingResource) {
      resourceConfig.columns.forEach((column: any) => {
        if (column.hasDependents && editingResource[column.field]) {
          fetchDependentOptions(column.field, editingResource[column.field]);
        }
      });
    }
  }, [isEditMode, editingResource, resourceConfig.columns, fetchDependentOptions]);
  
  // Handle modal container click to isolate its event bubble
  const handleModalClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
  }, []);
  
  // Handle manual close of the modal
  const handleClose = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    closeModal();
  }, [closeModal]);

  // Enhanced input change handler for dependencies
  const handleEnhancedInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target as HTMLInputElement;
    
    let finalValue: any = value;
    if (type === 'checkbox') {
      finalValue = (e.target as HTMLInputElement).checked;
    }
    
    // Use the dependent fields handler which also updates the field
    handleFieldChangeWithDependencies(name, finalValue);
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      setSubmitError(true);
      return;
    }

    const success = await saveOrUpdateResource(formData, editingResource);
    
    if (success) {
      resetForm();
    }
  };

  // Render form field
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
            onChange={handleEnhancedInputChange}
            required={column.required}
          />
          <label className="form-check-label" htmlFor={column.field}>
            {column.header}
          </label>
          {error && <div className="invalid-feedback">{error}</div>}
        </div>
      );
    }

    // Handle dependent fields
    if (isDependentField(column.field)) {
      const parentField = getParentField(column.field);
      const isLoading = loadingFields[column.field];
      const options = dynamicOptions[column.field] || [];
      const parentValue = parentField ? formData[parentField] : null;
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
            onChange={handleEnhancedInputChange}
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
            onChange={handleEnhancedInputChange}
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
            onChange={handleEnhancedInputChange}
            required={column.required}
            minLength={column.minLength}
            pattern={column.pattern}
            placeholder={column.placeholder}
            step={column.type === 'datetime-local' ? 1 : undefined}
          />
        )}
        
        {error && <div className="invalid-feedback">{error}</div>}
      </div>
    );
  };

  return (
    <div 
      className={`modal fade ${styles.modal}`}
      tabIndex={-1}
      aria-labelledby="resourceModalLabel"
      aria-hidden="true"
      ref={modalRef}
      onClick={handleModalClick}
      data-bs-backdrop="static"
      data-bs-keyboard="false"
    >
      <div className={`modal-dialog ${styles.modalDialog}`}>
        <div className={`modal-content ${styles.modalContent}`}>
          <div className={`modal-header text-white ${styles.modalHeader}`}>
            <h5 className="modal-title" id="resourceModalLabel">
              {editingResource ? `Edit ${resourceConfig.displayName}` : `Add ${resourceConfig.displayName}`}
            </h5>
            <button 
              type="button" 
              className={`btn-close btn-close-white ${styles.closeButton}`}
              onClick={handleClose}
              aria-label="Close"
            ></button>
          </div>
          <div className={`modal-body ${hasSubmitError ? styles.modalBodyError : styles.modalBody}`}>
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
                  <span className={`spinner-border spinner-border-sm ${styles.loadingSpinner}`} role="status" aria-hidden="true"></span>
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