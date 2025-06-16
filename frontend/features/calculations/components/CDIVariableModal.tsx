// frontend/features/calculations/components/CDIVariableModal.tsx
// Modal component for creating and editing CDI Variable calculations

import React, { useState, useEffect } from 'react';
import { useToast } from '@/context/ToastContext';
import { cdiVariableApi } from '@/services/calculationsApi';
import type { 
  CDIVariableForm, 
  CDIVariableConfig, 
  CDIVariableResponse
} from '@/types/cdi';
import { 
  INITIAL_CDI_FORM,
  CDI_GROUP_LEVEL_OPTIONS,
  createCDIVariableRequest,
  populateCDIFormFromResponse,
  requiresTrancheMapping,
  getVariablePatternPlaceholder
} from '@/types/cdi';

interface CDIVariableModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (savedVariable: CDIVariableResponse) => void;
  editingVariable?: CDIVariableResponse | null;
  mode: 'create' | 'edit';
}

const CDIVariableModal: React.FC<CDIVariableModalProps> = ({
  isOpen,
  onClose,
  onSave,
  editingVariable = null,
  mode
}) => {
  const { showToast } = useToast();
  const isEditMode = mode === 'edit' && editingVariable !== null;

  // State management
  const [form, setForm] = useState<CDIVariableForm>(INITIAL_CDI_FORM);
  const [config, setConfig] = useState<CDIVariableConfig | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [newMappingKey, setNewMappingKey] = useState('');
  const [newMappingValues, setNewMappingValues] = useState('');

  // Load configuration data
  useEffect(() => {
    if (isOpen) {
      loadConfig();
    }
  }, [isOpen]);

  // Load form data when editing
  useEffect(() => {
    if (isOpen && isEditMode && editingVariable) {
      setForm(populateCDIFormFromResponse(editingVariable));
      setHasUnsavedChanges(false);
    } else if (isOpen && !isEditMode) {
      resetForm();
    }
  }, [isOpen, isEditMode, editingVariable]);

  // Track changes for unsaved warning
  useEffect(() => {
    if (isOpen) {
      const hasChanges = isEditMode 
        ? formHasChanges(form, editingVariable!)
        : formHasContent(form);
      setHasUnsavedChanges(hasChanges);
    }
  }, [form, isOpen, isEditMode, editingVariable]);

  const loadConfig = async () => {
    try {
      const response = await cdiVariableApi.getCDIConfig();
      setConfig(response.data);
    } catch (error) {
      console.error('Failed to load CDI configuration:', error);
      showToast('Failed to load CDI configuration', 'error');
    }
  };

  const resetForm = () => {
    setForm({ ...INITIAL_CDI_FORM });
    setHasUnsavedChanges(false);
    setNewMappingKey('');
    setNewMappingValues('');
  };

  const handleFormChange = (field: keyof CDIVariableForm, value: any) => {
    setForm(prev => ({ ...prev, [field]: value }));
  };

  const loadDefaultMappings = () => {
    if (config?.default_tranche_mappings) {
      handleFormChange('tranche_mappings', { ...config.default_tranche_mappings });
      showToast('Default tranche mappings loaded', 'success');
    }
  };

  const addTrancheMapping = () => {
    if (!newMappingKey.trim() || !newMappingValues.trim()) {
      showToast('Please enter both suffix and tranche IDs', 'error');
      return;
    }

    const trancheIds = newMappingValues
      .split(',')
      .map(id => id.trim())
      .filter(id => id.length > 0);

    if (trancheIds.length === 0) {
      showToast('Please enter at least one tranche ID', 'error');
      return;
    }

    const newMappings = {
      ...form.tranche_mappings,
      [newMappingKey.trim()]: trancheIds
    };

    handleFormChange('tranche_mappings', newMappings);
    setNewMappingKey('');
    setNewMappingValues('');
    showToast('Tranche mapping added', 'success');
  };

  const removeTrancheMapping = (suffix: string) => {
    const { [suffix]: removed, ...remaining } = form.tranche_mappings;
    handleFormChange('tranche_mappings', remaining);
    showToast('Tranche mapping removed', 'success');
  };

  const validateForm = (): boolean => {
    if (!form.name.trim()) {
      showToast('Name is required', 'error');
      return false;
    }

    if (!form.variable_pattern.trim()) {
      showToast('Variable pattern is required', 'error');
      return false;
    }

    // Only validate tranche suffix placeholder for tranche-level calculations
    if (form.group_level === 'tranche' && !form.variable_pattern.includes('{tranche_suffix}')) {
      showToast('Tranche-level variable pattern must contain {tranche_suffix} placeholder', 'error');
      return false;
    }

    // Deal-level patterns should not contain tranche suffix placeholder
    if (form.group_level === 'deal' && form.variable_pattern.includes('{tranche_suffix}')) {
      showToast('Deal-level variable pattern should not contain {tranche_suffix} placeholder', 'error');
      return false;
    }

    if (!form.result_column_name.trim()) {
      showToast('Result column name is required', 'error');
      return false;
    }

    if (!/^[a-zA-Z][a-zA-Z0-9_]*$/.test(form.result_column_name)) {
      showToast('Result column name must start with a letter and contain only letters, numbers, and underscores', 'error');
      return false;
    }

    // Only require tranche mappings for tranche-level calculations
    if (requiresTrancheMapping(form.group_level) && Object.keys(form.tranche_mappings).length === 0) {
      showToast('At least one tranche mapping is required for tranche-level calculations', 'error');
      return false;
    }

    return true;
  };

  const handleSave = async () => {
    if (!validateForm()) return;

    try {
      setIsSaving(true);

      let savedVariable: CDIVariableResponse;

      if (isEditMode && editingVariable) {
        const updateData = {
          name: form.name,
          description: form.description,
          variable_pattern: form.variable_pattern,
          result_column_name: form.result_column_name,
          tranche_mappings: form.tranche_mappings
        };
        const response = await cdiVariableApi.updateCDIVariable(editingVariable.id, updateData);
        savedVariable = response.data;
        showToast('CDI variable updated successfully', 'success');
      } else {
        const createData = createCDIVariableRequest(form);
        const response = await cdiVariableApi.createCDIVariable(createData);
        savedVariable = response.data;
        showToast('CDI variable created successfully', 'success');
      }

      onSave(savedVariable);
      handleClose();
    } catch (error: any) {
      console.error('Failed to save CDI variable:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to save CDI variable';
      showToast(errorMessage, 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const handleClose = () => {
    if (hasUnsavedChanges) {
      if (window.confirm('You have unsaved changes. Are you sure you want to close?')) {
        resetForm();
        onClose();
      }
    } else {
      resetForm();
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal fade show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header bg-primary text-white">
            <h5 className="modal-title">
              <i className="bi bi-diagram-3 me-2"></i>
              {isEditMode ? 'Edit CDI Variable' : 'Create CDI Variable'}
            </h5>
            <button type="button" className="btn-close btn-close-white" onClick={handleClose}></button>
          </div>

          <div className="modal-body">
            <div className="row g-3">
              {/* Basic Information */}
              <div className="col-12">
                <h6 className="border-bottom pb-2">Basic Information</h6>
              </div>

              <div className="col-md-8">
                <label className="form-label">Name *</label>
                <input
                  type="text"
                  className="form-control"
                  value={form.name}
                  onChange={(e) => handleFormChange('name', e.target.value)}
                  placeholder="Enter a descriptive name for this CDI variable"
                  maxLength={100}
                />
              </div>

              <div className="col-md-4">
                <label className="form-label">Group Level *</label>
                <select
                  className="form-select"
                  value={form.group_level || 'tranche'}
                  onChange={(e) => handleFormChange('group_level', e.target.value as 'deal' | 'tranche')}
                >
                  {CDI_GROUP_LEVEL_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <small className="form-text text-muted">
                  {form.group_level === 'deal' 
                    ? 'Deal-level: One result per deal, no tranche breakdown' 
                    : 'Tranche-level: Results broken down by tranche within each deal'
                  }
                </small>
              </div>

              <div className="col-12">
                <label className="form-label">Description</label>
                <textarea
                  className="form-control"
                  rows={2}
                  value={form.description}
                  onChange={(e) => handleFormChange('description', e.target.value)}
                  placeholder="Optional description of what this variable represents"
                  maxLength={500}
                />
              </div>

              {/* Variable Pattern */}
              <div className="col-12 mt-4">
                <h6 className="border-bottom pb-2">Variable Pattern</h6>
              </div>

              <div className="col-12">
                <label className="form-label">Pattern *</label>
                <div className="input-group">
                  <input
                    type="text"
                    className="form-control"
                    value={form.variable_pattern}
                    onChange={(e) => handleFormChange('variable_pattern', e.target.value)}
                    placeholder={getVariablePatternPlaceholder(form.group_level)}
                  />
                </div>
                <small className="form-text text-muted">
                  {form.group_level === 'tranche' 
                    ? `Use {tranche_suffix} as a placeholder for tranche identifiers`
                    : 'For deal-level variables, enter the exact variable name (no placeholders needed)'
                  }
                </small>
              </div>

              {/* Result Column Name */}
              <div className="col-12">
                <label className="form-label">Result Column Name *</label>
                <input
                  type="text"
                  className="form-control"
                  value={form.result_column_name}
                  onChange={(e) => handleFormChange('result_column_name', e.target.value)}
                  placeholder="Column name in the result dataset"
                  pattern="^[a-zA-Z][a-zA-Z0-9_]*$"
                />
                <small className="form-text text-muted">
                  Must start with a letter and contain only letters, numbers, and underscores
                </small>
              </div>

              {/* Tranche Mappings - Only show for tranche-level calculations */}
              {requiresTrancheMapping(form.group_level) && (
                <>
                  <div className="col-12 mt-4">
                    <div className="d-flex align-items-center justify-content-between border-bottom pb-2">
                      <h6 className="mb-0">Tranche Mappings</h6>
                      {config && Object.keys(config.default_tranche_mappings).length > 0 && (
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-primary"
                          onClick={loadDefaultMappings}
                        >
                          Load Defaults
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Add New Mapping */}
                  <div className="col-md-4">
                    <label className="form-label">Suffix</label>
                    <input
                      type="text"
                      className="form-control"
                      value={newMappingKey}
                      onChange={(e) => setNewMappingKey(e.target.value)}
                      placeholder="e.g., M1, B1"
                    />
                  </div>

                  <div className="col-md-6">
                    <label className="form-label">Tranche IDs (comma-separated)</label>
                    <input
                      type="text"
                      className="form-control"
                      value={newMappingValues}
                      onChange={(e) => setNewMappingValues(e.target.value)}
                      placeholder="e.g., 1M1, 2M1, M1"
                    />
                  </div>

                  <div className="col-md-2">
                    <label className="form-label">&nbsp;</label>
                    <button
                      type="button"
                      className="btn btn-primary w-100"
                      onClick={addTrancheMapping}
                    >
                      Add
                    </button>
                  </div>

                  {/* Existing Mappings */}
                  {Object.keys(form.tranche_mappings).length > 0 && (
                    <div className="col-12">
                      <div className="table-responsive">
                        <table className="table table-sm">
                          <thead>
                            <tr>
                              <th>Suffix</th>
                              <th>Tranche IDs</th>
                              <th style={{ width: '80px' }}>Action</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.entries(form.tranche_mappings).map(([suffix, trancheIds]) => (
                              <tr key={suffix}>
                                <td><strong>{suffix}</strong></td>
                                <td>{trancheIds.join(', ')}</td>
                                <td>
                                  <button
                                    type="button"
                                    className="btn btn-sm btn-outline-danger"
                                    onClick={() => removeTrancheMapping(suffix)}
                                  >
                                    Remove
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* Deal-level information */}
              {form.group_level === 'deal' && (
                <div className="col-12 mt-4">
                  <div className="alert alert-info">
                    <i className="bi bi-info-circle me-2"></i>
                    <strong>Deal-Level Calculation:</strong> This variable will return one value per deal without tranche breakdown. 
                    The variable pattern should be the exact CDI variable name as it appears in the database.
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={handleClose}>
              <i className="bi bi-x-circle me-2"></i>
              Cancel
            </button>
            <button 
              type="button" 
              className="btn btn-primary"
              onClick={handleSave}
              disabled={isSaving}
            >
              {isSaving ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                  Saving...
                </>
              ) : (
                <>
                  <i className="bi bi-save me-2"></i>
                  Save Variable
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Helper functions
function formHasContent(form: CDIVariableForm): boolean {
  return !!(
    form.name?.trim() ||
    form.description?.trim() ||
    form.variable_pattern?.trim() ||
    form.result_column_name?.trim() ||
    form.group_level ||
    Object.keys(form.tranche_mappings).length > 0
  );
}

function formHasChanges(current: CDIVariableForm, original: CDIVariableResponse): boolean {
  return (
    current.name !== original.name ||
    current.description !== (original.description || '') ||
    current.variable_pattern !== original.variable_pattern ||
    current.result_column_name !== original.result_column_name ||
    current.group_level !== original.group_level ||
    JSON.stringify(current.tranche_mappings) !== JSON.stringify(original.tranche_mappings)
  );
}

export default CDIVariableModal;
