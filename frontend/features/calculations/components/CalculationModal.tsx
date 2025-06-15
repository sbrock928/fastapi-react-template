// frontend/features/calculations/components/CalculationModal.tsx
import React, { useState } from 'react';
import type { 
  Calculation, 
  CalculationField, 
  AggregationFunctionInfo, 
  SourceModelInfo, 
  GroupLevelInfo, 
  CalculationForm 
} from '@/types/calculations';
import { 
  getPreviewFormula, 
  getScopeCompatibilityWarning, 
  getRecommendedLevel, 
  getAvailableFields,
  validateSqlSyntax
} from '../utils/calculationUtils';
import { getFullSQLPreview } from '../utils/sqlPreviewUtils';
import SqlEditor from './SqlEditor';
import { calculationsApi } from '@/services/calculationsApi';
import { useToast } from '@/context/ToastContext';

interface CalculationModalProps {
  isOpen: boolean;
  modalType: 'user-defined' | 'system-sql';
  editingCalculation: Calculation | null;
  calculation: CalculationForm;
  error: string | null;
  isSaving: boolean;
  fieldsLoading: boolean;
  allAvailableFields: Record<string, CalculationField[]>;
  aggregationFunctions: AggregationFunctionInfo[];
  sourceModels: SourceModelInfo[];
  groupLevels: GroupLevelInfo[];
  onClose: () => void;
  onSave: () => void;
  onUpdateCalculation: (updates: Partial<CalculationForm>) => void;
  hasUnsavedChanges: boolean;
}

const CalculationModal: React.FC<CalculationModalProps> = ({
  isOpen,
  modalType,
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
  const { showToast } = useToast();
  const [sqlValidationResult, setSqlValidationResult] = useState<any>(null);
  const [sqlValidating, setSqlValidating] = useState<boolean>(false);

  if (!isOpen) return null;

  const getModalTitle = () => {
    switch (modalType) {
      case 'user-defined':
        return editingCalculation ? 'Edit User Calculation' : 'Create New User Calculation';
      case 'system-sql':
        return 'Create System SQL Calculation';
      default:
        return 'Calculation';
    }
  };

  const getModalHeaderColor = () => {
    switch (modalType) {
      case 'user-defined':
        return 'bg-primary';
      case 'system-sql':
        return 'bg-primary text-white';
      default:
        return 'bg-primary';
    }
  };

  // Handle SQL validation for System SQL calculations
  const handleValidateSQL = async () => {
    if (!calculation.source_field || !calculation.weight_field || !calculation.level) {
      showToast('Please provide SQL query, result column name, and group level before validating', 'warning');
      return;
    }

    setSqlValidating(true);
    try {
      const response = await calculationsApi.validateSystemSql({
        sql_text: calculation.source_field,
        group_level: calculation.level as "deal" | "tranche",
        result_column_name: calculation.weight_field
      });

      setSqlValidationResult(response.data.validation_result);
      
      if (response.data.validation_result.is_valid) {
        showToast('SQL validation passed!', 'success');
      } else {
        showToast('SQL validation failed. Please check the errors below.', 'error');
      }
    } catch (error: any) {
      console.error('Error validating SQL:', error);
      const errorMessage = error.response?.data?.detail || 'Error validating SQL';
      showToast(errorMessage, 'error');
      setSqlValidationResult({
        is_valid: false,
        errors: [errorMessage],
        warnings: []
      });
    } finally {
      setSqlValidating(false);
    }
  };

  const renderUserDefinedForm = () => {
    const scopeWarning = getScopeCompatibilityWarning(calculation);
    const recommendedLevel = getRecommendedLevel(calculation);
    const availableFields = getAvailableFields(calculation.source, allAvailableFields);

    return (
      <>
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
              disabled={groupLevels.length === 0}
            >
              <option value="">
                {groupLevels.length === 0 ? 'Loading group levels...' : 'Select group level...'}
              </option>
              {groupLevels.map((level: GroupLevelInfo) => (
                <option key={level.value} value={level.value}>
                  {level.label}
                </option>
              ))}
            </select>
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
              disabled={sourceModels.length === 0}
            >
              <option value="">
                {sourceModels.length === 0 ? 'Loading source models...' : 'Select a source model...'}
              </option>
              {sourceModels.map((model: SourceModelInfo) => (
                <option key={model.value} value={model.value}>
                  {model.label}
                </option>
              ))}
            </select>
          </div>

          <div className="col-md-6">
            <label className="form-label">Aggregation Function *</label>
            <select
              value={calculation.function_type}
              onChange={(e) => onUpdateCalculation({ function_type: e.target.value })}
              className="form-select"
              disabled={aggregationFunctions.length === 0}
            >
              <option value="">
                {aggregationFunctions.length === 0 ? 'Loading aggregation functions...' : 'Select aggregation function...'}
              </option>
              {aggregationFunctions.map((func: AggregationFunctionInfo) => (
                <option key={func.value} value={func.value}>
                  {func.label}
                </option>
              ))}
            </select>
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
              {availableFields.map((field: CalculationField) => (
                <option key={field.value} value={field.value}>
                  {field.label} ({field.type})
                </option>
              ))}
            </select>
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
                {availableFields.filter((f: CalculationField) => f.type === 'currency' || f.type === 'number').map((field: CalculationField) => (
                  <option key={field.value} value={field.value}>
                    {field.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Formula Preview */}
          <div className="col-12">
            <label className="form-label">Generated Formula Preview</label>
            <div className="bg-light rounded p-3 border">
              <code className="text-dark">{getPreviewFormula(calculation)}</code>
            </div>
          </div>

          {/* Scope Warning */}
          {scopeWarning && (
            <div className="col-12">
              <div className="alert alert-warning">
                <i className="bi bi-exclamation-triangle me-2"></i>
                <strong>Compatibility Notice:</strong> {scopeWarning}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {recommendedLevel && recommendedLevel !== calculation.level && (
            <div className="col-12">
              <div className="alert alert-info">
                <i className="bi bi-lightbulb me-2"></i>
                <strong>Recommendation:</strong> Consider setting the group level to <strong>{recommendedLevel}</strong> for optimal compatibility.
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

          {/* SQL Preview */}
          <div className="col-12">
            <label className="form-label">Complete SQL Query Preview</label>
            <div className="bg-dark text-light rounded p-3 border" style={{ fontFamily: 'monospace' }}>
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: '0.85rem' }}>
                {getFullSQLPreview(calculation)}
              </pre>
            </div>
          </div>
        </div>
      </>
    );
  };

  const renderSystemSqlForm = () => {
    // Perform basic client-side SQL validation
    const clientValidation = calculation.source_field ? validateSqlSyntax(calculation.source_field) : null;

    return (
      <>
        <div className="alert alert-info">
          <i className="bi bi-info-circle me-2"></i>
          <strong>System SQL Calculation:</strong> Advanced custom calculation using validated SQL queries.
          <div className="mt-2">
            <strong>Important:</strong> 
            <ul className="mb-0 mt-1">
              <li><strong>WHERE clauses are automatically injected</strong> - Don't include deal/tranche filters or cycle filters</li>
              <li><strong>GROUP BY clauses are required</strong> - You must include appropriate grouping for your calculation level</li>
              <li>Must include proper join fields and return exactly one new column</li>
            </ul>
          </div>
        </div>

        <div className="row g-3">
          <div className="col-md-6">
            <label className="form-label">Calculation Name *</label>
            <input
              type="text"
              value={calculation.name}
              onChange={(e) => onUpdateCalculation({ name: e.target.value })}
              className="form-control"
              placeholder="e.g., Issuer Type Classification"
            />
          </div>

          <div className="col-md-6">
            <label className="form-label">Group Level *</label>
            <select
              value={calculation.level}
              onChange={(e) => onUpdateCalculation({ level: e.target.value })}
              className="form-select"
            >
              <option value="">
                {groupLevels.length === 0 ? 'Loading group levels...' : 'Select group level...'}
              </option>
              {groupLevels.map((level: GroupLevelInfo) => (
                <option key={level.value} value={level.value}>
                  {level.label}
                </option>
              ))}
            </select>
          </div>

          <div className="col-12">
            <label className="form-label">Description</label>
            <textarea
              value={calculation.description}
              onChange={(e) => onUpdateCalculation({ description: e.target.value })}
              className="form-control"
              rows={2}
              placeholder="Describe what this SQL calculation does..."
            />
          </div>

          <div className="col-md-6">
            <label className="form-label">Result Column Name *</label>
            <input
              type="text"
              value={calculation.weight_field || ''} // Using weight_field to store result column name
              onChange={(e) => onUpdateCalculation({ weight_field: e.target.value })}
              className="form-control"
              placeholder="e.g., issuer_type"
              pattern="^[a-zA-Z][a-zA-Z0-9_]*$"
            />
            <div className="form-text">Must be a valid SQL identifier (letters, numbers, underscores)</div>
          </div>

          <div className="col-12">
            <label className="form-label">SQL Query *</label>
            <div className="alert alert-warning mb-2">
              <i className="bi bi-exclamation-triangle me-2"></i>
              <strong>Filter Injection Notice:</strong> 
              <div className="mt-1">
                The system will automatically add WHERE clauses for:
                <ul className="mb-0 mt-1">
                  <li><code>deal.dl_nbr IN (selected_deals)</code></li>
                  <li><code>tranche.tr_id IN (selected_tranches)</code> (if applicable)</li>
                  <li><code>tranchebal.cycle_cde = selected_cycle</code> (if tranchebal table is used)</li>
                </ul>
                <strong>Don't include these filters in your SQL - they'll be added automatically!</strong>
              </div>
            </div>
            <SqlEditor
              value={calculation.source_field || ''} // Using source_field to store SQL
              onChange={(sql) => {
                onUpdateCalculation({ source_field: sql });
                // Clear previous validation when SQL changes
                if (sqlValidationResult) {
                  setSqlValidationResult(null);
                }
              }}
              groupLevel={calculation.level}
              disabled={isSaving}
              placeholder={calculation.level === 'deal' 
                ? `-- Deal-level example (GROUP BY required for aggregations):
SELECT 
    deal.dl_nbr,
    CASE 
        WHEN deal.issr_cde LIKE '%FHLMC%' THEN 'GSE'
        WHEN deal.issr_cde LIKE '%GNMA%' THEN 'Government'
        ELSE 'Private'
    END AS ${calculation.weight_field || 'result_column'}
FROM deal
-- WHERE clauses will be injected automatically

-- For aggregations, include GROUP BY:
-- GROUP BY deal.dl_nbr`
                : `-- Tranche-level example (GROUP BY required for aggregations):
SELECT 
    deal.dl_nbr,
    tranche.tr_id,
    CASE 
        WHEN tranchebal.tr_end_bal_amt >= 25000000 THEN 'Large'
        WHEN tranchebal.tr_end_bal_amt >= 10000000 THEN 'Medium'
        ELSE 'Small'
    END AS ${calculation.weight_field || 'result_column'}
FROM deal
JOIN tranche ON deal.dl_nbr = tranche.dl_nbr
JOIN tranchebal ON tranche.dl_nbr = tranchebal.dl_nbr 
    AND tranche.tr_id = tranchebal.tr_id
-- WHERE clauses will be injected automatically

-- For aggregations, include GROUP BY:
-- GROUP BY deal.dl_nbr, tranche.tr_id`}
            />
          </div>

          {/* Preview of what the final SQL will look like */}
          {calculation.source_field && calculation.source_field.trim() && (
            <div className="col-12">
              <label className="form-label">Final SQL Preview (with injected filters)</label>
              <div className="alert alert-secondary">
                <small className="text-muted">
                  This shows how your SQL will look after the system automatically injects WHERE clauses:
                </small>
                <pre className="bg-dark text-light p-3 mt-2 rounded" style={{ fontSize: '0.8rem', whiteSpace: 'pre-wrap' }}>
{calculation.source_field.trim()}
{/* Show where the WHERE clause would be injected */}
{!calculation.source_field.toLowerCase().includes('where') && !calculation.source_field.toLowerCase().includes('group by') 
  ? '\nWHERE [filters will be injected here]'
  : calculation.source_field.toLowerCase().includes('group by') && !calculation.source_field.toLowerCase().includes('where')
  ? '\nWHERE [filters will be injected before GROUP BY]'
  : '\nAND [additional filters will be injected]'}
                </pre>
              </div>
            </div>
          )}

          {/* Client-side SQL validation feedback */}
          {clientValidation && !clientValidation.isValid && (
            <div className="col-12">
              <div className="alert alert-warning">
                <h6 className="alert-heading">
                  <i className="bi bi-exclamation-triangle me-2"></i>
                  Basic SQL Issues Detected
                </h6>
                <ul className="mb-0">
                  {clientValidation.errors.map((error: string, index: number) => (
                    <li key={index}>{error}</li>
                  ))}
                </ul>
                <small className="text-muted mt-2 d-block">
                  Fix these issues before server validation.
                </small>
              </div>
            </div>
          )}

          {/* Server validation results */}
          {sqlValidationResult && (
            <div className="col-12">
              <div className={`alert ${sqlValidationResult.is_valid ? 'alert-success' : 'alert-danger'} mt-3`}>
                <div className="d-flex align-items-center mb-2">
                  <i className={`bi ${sqlValidationResult.is_valid ? 'bi-check-circle' : 'bi-exclamation-triangle'} me-2`}></i>
                  <strong>
                    {sqlValidationResult.is_valid ? 'SQL Validation Passed' : 'SQL Validation Failed'}
                  </strong>
                </div>
                
                {sqlValidationResult.errors && sqlValidationResult.errors.length > 0 && (
                  <div className="mb-2">
                    <strong className="text-danger">Errors:</strong>
                    <ul className="mb-0 mt-1">
                      {sqlValidationResult.errors.map((error: string, index: number) => (
                        <li key={index} className="text-danger">{error}</li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {sqlValidationResult.warnings && sqlValidationResult.warnings.length > 0 && (
                  <div>
                    <strong className="text-warning">Warnings:</strong>
                    <ul className="mb-0 mt-1">
                      {sqlValidationResult.warnings.map((warning: string, index: number) => (
                        <li key={index} className="text-warning">{warning}</li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {sqlValidationResult.is_valid && (
                  <small className="text-muted d-block mt-2">
                    Your SQL passed all validation checks and is ready to save.
                  </small>
                )}
              </div>
            </div>
          )}

          {/* Updated Requirements */}
          <div className="col-12">
            <div className="card bg-light border-primary">
              <div className="card-body">
                <h6 className="card-title text-primary">
                  <i className="bi bi-list-check me-2"></i>
                  SQL Requirements for {calculation.level} Level:
                </h6>
                <div className="row">
                  <div className="col-md-6">
                    <h6 className="text-success">✅ Required (You Must Include):</h6>
                    <ul className="mb-2">
                      <li>SELECT <code>deal.dl_nbr</code></li>
                      {calculation.level === 'tranche' && (
                        <li>SELECT <code>tranche.tr_id</code></li>
                      )}
                      <li>Return exactly one result column: <code>{calculation.weight_field || 'result_column'}</code></li>
                      <li>Proper FROM and JOIN statements</li>
                      <li><strong>GROUP BY clause</strong> (for aggregations)</li>
                    </ul>
                  </div>
                  <div className="col-md-6">
                    <h6 className="text-danger">❌ Forbidden (System Handles):</h6>
                    <ul className="mb-2">
                      <li>WHERE <code>deal.dl_nbr = ...</code></li>
                      <li>WHERE <code>tranche.tr_id IN ...</code></li>
                      <li>WHERE <code>tranchebal.cycle_cde = ...</code></li>
                      <li>Dangerous operations (DROP, DELETE, etc.)</li>
                    </ul>
                  </div>
                </div>
                <div className="alert alert-info mb-0 mt-2">
                  <small>
                    <strong>💡 Tip:</strong> Focus on your business logic and grouping. The system will automatically add filters 
                    for the selected deals, tranches, and cycle when the calculation runs.
                  </small>
                </div>
              </div>
            </div>
          </div>
        </div>
      </>
    );
  };

  const renderModalContent = () => {
    switch (modalType) {
      case 'user-defined':
        return renderUserDefinedForm();
      case 'system-sql':
        return renderSystemSqlForm();
      default:
        return null;
    }
  };

  return (
    <div className="modal show d-block" tabIndex={-1} style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-xl modal-dialog-scrollable">
        <div className="modal-content">
          <div className={`modal-header ${getModalHeaderColor()}`}>
            <h5 className="modal-title">
              {getModalTitle()}
            </h5>
            <button
              type="button"
              className={`btn-close ${modalType === 'system-sql' ? '' : 'btn-close-white'}`}
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

                {renderModalContent()}
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
            {modalType === 'system-sql' && (
              <button
                type="button"
                className="btn btn-outline-info"
                disabled={!calculation.source_field || sqlValidating}
                onClick={handleValidateSQL}
              >
                {sqlValidating ? (
                  <>
                    <span className="spinner-border spinner-border-sm me-2"></span>
                    Validating...
                  </>
                ) : (
                  <>
                    <i className="bi bi-check-circle me-2"></i>
                    Validate SQL
                  </>
                )}
              </button>
            )}
            <button
              type="button"
              onClick={onSave}
              disabled={
                isSaving || 
                fieldsLoading || 
                (modalType === 'system-sql' && (!sqlValidationResult || !sqlValidationResult.is_valid))
              }
              className="btn btn-primary"
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