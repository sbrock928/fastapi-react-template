import React from 'react';
import type { 
  Calculation, 
  CalculationField, 
  AggregationFunction, 
  SourceModel, 
  GroupLevel, 
  CalculationForm 
} from '@/types/calculations';
import { 
  getPreviewFormula, 
  getScopeCompatibilityWarning, 
  getRecommendedLevel, 
  getAvailableFields 
} from '../utils/calculationUtils';
import { getFullSQLPreview } from '../utils/sqlPreviewUtils';

interface CalculationModalProps {
  isOpen: boolean;
  editingCalculation: Calculation | null;
  calculation: CalculationForm;
  error: string | null;
  isSaving: boolean;
  fieldsLoading: boolean;
  allAvailableFields: Record<string, CalculationField[]>;
  aggregationFunctions: AggregationFunction[];
  sourceModels: SourceModel[];
  groupLevels: GroupLevel[];
  onClose: () => void;
  onSave: () => void;
  onUpdateCalculation: (updates: Partial<CalculationForm>) => void;
}

const CalculationModal: React.FC<CalculationModalProps> = ({
  isOpen,
  editingCalculation,
  calculation,
  error,
  isSaving,
  fieldsLoading,
  allAvailableFields,
  aggregationFunctions,
  sourceModels,
  groupLevels,
  onClose,
  onSave,
  onUpdateCalculation
}) => {
  if (!isOpen) return null;

  const scopeWarning = getScopeCompatibilityWarning(calculation);
  const recommendedLevel = getRecommendedLevel(calculation);
  const availableFields = getAvailableFields(calculation.source, allAvailableFields);

  return (
    <div className="modal show d-block" tabIndex={-1} style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-xl modal-dialog-scrollable">
        <div className="modal-content">
          <div className="modal-header bg-primary">
            <h5 className="modal-title">
              {editingCalculation ? 'Edit Calculation' : 'Create New Calculation'}
            </h5>
            <button
              type="button"
              className="btn-close btn-close-white"
              onClick={onClose}
            ></button>
          </div>
          
          <div className="modal-body">
            {fieldsLoading ? (
              <div className="text-center py-4">
                <div className="spinner-border text-primary" role="status">
                  <span className="visually-hidden">Loading...</span>
                </div>
                <p className="mt-2 mb-0">Loading calculation configuration...</p>
              </div>
            ) : (
              <>
                {error && (
                  <div className="alert alert-danger" role="alert">
                    {error}
                  </div>
                )}

                <div className="row g-3">
                  {/* Basic Information */}
                  <div className="col-md-6">
                    <label className="form-label">Calculation Name *</label>
                    <input
                      type="text"
                      value={calculation.name}
                      onChange={(e) => onUpdateCalculation({ name: e.target.value })}
                      className="form-control"
                      placeholder="e.g., Total Ending Balance"
                    />
                  </div>

                  <div className="col-md-6">
                    <label className="form-label">Group Level *</label>
                    <select
                      value={calculation.level}
                      onChange={(e) => onUpdateCalculation({ level: e.target.value })}
                      className="form-select"
                    >
                      {groupLevels.map(level => (
                        <option key={level.value} value={level.value}>
                          {level.label}
                        </option>
                      ))}
                    </select>
                    <div className="form-text">
                      {groupLevels.find(l => l.value === calculation.level)?.description}
                    </div>
                  </div>

                  {/* Description */}
                  <div className="col-12">
                    <label className="form-label">Description</label>
                    <textarea
                      value={calculation.description}
                      onChange={(e) => onUpdateCalculation({ description: e.target.value })}
                      className="form-control"
                      rows={3}
                      placeholder="Describe what this calculation measures..."
                    />
                  </div>

                  {/* Source Configuration */}
                  <div className="col-md-6">
                    <label className="form-label">Source Model *</label>
                    <select
                      value={calculation.source}
                      onChange={(e) => onUpdateCalculation({ source: e.target.value, source_field: '' })}
                      className="form-select"
                    >
                      <option value="">Select a source model...</option>
                      {sourceModels.map(model => (
                        <option key={model.value} value={model.value}>
                          {model.label}
                        </option>
                      ))}
                    </select>
                    <div className="form-text">
                      {sourceModels.find(m => m.value === calculation.source)?.description}
                    </div>
                  </div>

                  <div className="col-md-6">
                    <label className="form-label">Aggregation Function *</label>
                    <select
                      value={calculation.function_type}
                      onChange={(e) => onUpdateCalculation({ function_type: e.target.value })}
                      className="form-select"
                    >
                      {aggregationFunctions.map(func => (
                        <option key={func.value} value={func.value}>
                          {func.label}
                        </option>
                      ))}
                    </select>
                    <div className="form-text">
                      {aggregationFunctions.find(f => f.value === calculation.function_type)?.description}
                    </div>
                  </div>

                  {/* Field Selection */}
                  <div className="col-md-6">
                    <label className="form-label">Source Field *</label>
                    <select
                      value={calculation.source_field}
                      onChange={(e) => onUpdateCalculation({ source_field: e.target.value })}
                      className="form-select"
                      disabled={!calculation.source || availableFields.length === 0}
                    >
                      <option value="">Select a field...</option>
                      {availableFields.map(field => (
                        <option key={field.value} value={field.value}>
                          {field.label} ({field.type})
                        </option>
                      ))}
                    </select>
                    <div className="form-text">
                      {calculation.source ? `Available fields from ${calculation.source} model` : 'Select a source model first'}
                    </div>
                    {/* Show field description if available */}
                    {calculation.source_field && availableFields.find(f => f.value === calculation.source_field)?.description && (
                      <div className="form-text text-info">
                        {availableFields.find(f => f.value === calculation.source_field)?.description}
                      </div>
                    )}
                  </div>

                  {/* Weight Field for Weighted Average */}
                  {calculation.function_type === 'WEIGHTED_AVG' && (
                    <div className="col-md-6">
                      <label className="form-label">Weight Field *</label>
                      <select
                        value={calculation.weight_field}
                        onChange={(e) => onUpdateCalculation({ weight_field: e.target.value })}
                        className="form-select"
                        disabled={!calculation.source || availableFields.length === 0}
                      >
                        <option value="">Select weight field...</option>
                        {availableFields.filter(f => f.type === 'currency' || f.type === 'number').map(field => (
                          <option key={field.value} value={field.value}>
                            {field.label}
                          </option>
                        ))}
                      </select>
                      <div className="form-text">
                        Field to use as weight for the weighted average calculation
                      </div>
                      {/* Show weight field description if available */}
                      {calculation.weight_field && availableFields.find(f => f.value === calculation.weight_field)?.description && (
                        <div className="form-text text-info">
                          {availableFields.find(f => f.value === calculation.weight_field)?.description}
                        </div>
                      )}
                    </div>
                  )}

                  {/* ORM Formula Preview */}
                  <div className="col-12">
                    <label className="form-label">Generated ORM Formula Preview</label>
                    <div className="bg-light rounded p-3 border">
                      <code className="text-dark">{getPreviewFormula(calculation)}</code>
                    </div>
                    <div className="form-text">
                      <strong>Model:</strong> {calculation.source} | 
                      <strong> Function:</strong> {calculation.function_type} | 
                      <strong> Level:</strong> {calculation.level}
                    </div>
                  </div>

                  {/* Scope Compatibility Warning */}
                  {scopeWarning && (
                    <div className="col-12">
                      <div className="alert alert-warning">
                        <i className="bi bi-exclamation-triangle me-2"></i>
                        <strong>Compatibility Notice:</strong> {scopeWarning}
                      </div>
                    </div>
                  )}

                  {/* Intelligent Recommendations */}
                  {recommendedLevel && recommendedLevel !== calculation.level && (
                    <div className="col-12">
                      <div className="alert alert-info">
                        <i className="bi bi-lightbulb me-2"></i>
                        <strong>Recommendation:</strong> Based on your source model and function type, 
                        consider setting the group level to <strong>{recommendedLevel}</strong> for optimal compatibility.
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-info ms-2"
                          onClick={() => onUpdateCalculation({ level: recommendedLevel })}
                        >
                          Apply Recommendation
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Full SQL Preview */}
                  <div className="col-12">
                    <label className="form-label">Complete SQL Query Preview</label>
                    <div className="bg-dark text-light rounded p-3 border" style={{ fontFamily: 'monospace' }}>
                      <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: '0.85rem' }}>
                        {getFullSQLPreview(calculation)}
                      </pre>
                    </div>
                    <div className="form-text text-muted">
                      This shows the complete SQL query that will be executed when this calculation runs in a report, 
                      including all result fields and proper JOIN relationships.
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Modal Footer */}
          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              disabled={isSaving || fieldsLoading}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={onSave}
              disabled={isSaving || fieldsLoading}
              className="btn btn-success"
            >
              {isSaving ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2" role="status"></span>
                  Saving...
                </>
              ) : (
                <>
                  <i className="bi bi-save me-2"></i>
                  {editingCalculation ? 'Update Calculation' : 'Save Calculation'}
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CalculationModal;