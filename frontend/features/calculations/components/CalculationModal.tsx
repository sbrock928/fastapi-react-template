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
  getAvailableFields,
  parseAndValidateComplexSQLWithPlaceholders
} from '../utils/calculationUtils';
import { getFullSQLPreview } from '../utils/sqlPreviewUtils';
import SqlEditor from './SqlEditor';
import { calculationsApi } from '@/services/calculationsApi';
import { useToast } from '@/context/ToastContext';

interface CalculationModalProps {
  isOpen: boolean;
  modalType: 'user-defined' | 'system-field' | 'system-sql';
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
  const [clientValidationResult, setClientValidationResult] = useState<any>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  if (!isOpen) return null;

  const getModalTitle = () => {
    switch (modalType) {
      case 'user-defined':
        return editingCalculation ? 'Edit User Calculation' : 'Create New User Calculation';
      case 'system-sql':
        return editingCalculation ? 'Edit System SQL Calculation' : 'Create System SQL Calculation';
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

  // Enhanced SQL validation for System SQL calculations
  const handleValidateSQL = async () => {
    if (!calculation.source_field || !calculation.weight_field || !calculation.level) {
      showToast('Please provide SQL query, result column name, and group level before validating', 'warning');
      return;
    }

    setSqlValidating(true);
    setSaveError(null); // Clear any previous save errors
    try {
      const response = await calculationsApi.validateSystemSql({
        sql_text: calculation.source_field,
        group_level: calculation.level as "deal" | "tranche",
        result_column_name: calculation.weight_field
      });

      setSqlValidationResult(response.data.validation_result);
      
      if (response.data.validation_result.is_valid) {
        showToast('SQL validation passed! All placeholder usage and structure checks succeeded.', 'success');
      } else {
        showToast('SQL validation failed. Please check the errors below.', 'error');
      }
    } catch (error: any) {
      console.error('Error validating SQL:', error);
      let errorMessage = 'Error validating SQL';
      let detailedErrors: string[] = [];
      
      // Extract detailed error information
      if (error.response?.data?.detail) {
        if (typeof error.response.data.detail === 'string') {
          errorMessage = error.response.data.detail;
          detailedErrors = [error.response.data.detail];
        } else if (Array.isArray(error.response.data.detail)) {
          detailedErrors = error.response.data.detail.map((err: any) => 
            typeof err === 'string' ? err : err.msg || err.message || JSON.stringify(err)
          );
          errorMessage = detailedErrors[0] || 'Validation failed';
        } else if (error.response.data.detail.msg) {
          errorMessage = error.response.data.detail.msg;
          detailedErrors = [error.response.data.detail.msg];
        }
      } else if (error.message) {
        errorMessage = error.message;
        detailedErrors = [error.message];
      }
      
      showToast(errorMessage, 'error');
      setSqlValidationResult({
        is_valid: false,
        errors: detailedErrors,
        warnings: [],
        placeholders_used: []
      });
    } finally {
      setSqlValidating(false);
    }
  };

  // Enhanced save handler with better error handling
  const handleSave = async () => {
    setSaveError(null); // Clear any previous save errors
    try {
      await onSave();
    } catch (error: any) {
      console.error('Error saving calculation:', error);
      let errorMessage = 'Error saving calculation';
      
      // Extract detailed error information
      if (error.response?.data?.detail) {
        if (typeof error.response.data.detail === 'string') {
          errorMessage = error.response.data.detail;
        } else if (Array.isArray(error.response.data.detail)) {
          const detailedErrors = error.response.data.detail.map((err: any) => 
            typeof err === 'string' ? err : err.msg || err.message || JSON.stringify(err)
          );
          errorMessage = detailedErrors.join(', ');
        } else if (error.response.data.detail.msg) {
          errorMessage = error.response.data.detail.msg;
        }
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      setSaveError(errorMessage);
      showToast(errorMessage, 'error');
    }
  };

  // Enhanced client-side validation for real-time feedback
  const handleSqlChange = (sql: string) => {
    onUpdateCalculation({ source_field: sql });
    
    // Clear previous server validation when SQL changes
    if (sqlValidationResult) {
      setSqlValidationResult(null);
    }
    
    // Perform enhanced client-side validation with placeholder support
    if (sql && calculation.level && calculation.weight_field) {
      const clientValidation = parseAndValidateComplexSQLWithPlaceholders(
        sql,
        calculation.level,
        calculation.weight_field
      );
      setClientValidationResult(clientValidation);
    } else {
      setClientValidationResult(null);
    }
  };

  const renderUserDefinedForm = () => {
    const scopeWarning = getScopeCompatibilityWarning(calculation);
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
    return (
      <>
        <div className="row g-3">
          <div className="col-md-6">
            <label className="form-label">Calculation Name *</label>
            <input
              type="text"
              value={calculation.name}
              onChange={(e) => onUpdateCalculation({ name: e.target.value })}
              className="form-control"
              placeholder="e.g., Deal Growth Trend Analysis"
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
                  {level.label} - {level.value === 'deal' ? 'One result per deal' : 'One result per tranche'}
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
              placeholder="Describe what this calculation analyzes (e.g., 'Classifies deals by growth trend using current vs previous cycle balances')"
            />
          </div>

          <div className="col-md-6">
            <label className="form-label">Result Column Name *</label>
            <input
              type="text"
              value={calculation.weight_field || ''}
              onChange={(e) => onUpdateCalculation({ weight_field: e.target.value })}
              className="form-control"
              placeholder="e.g., growth_trend"
              pattern="^[a-zA-Z][a-zA-Z0-9_]*$"
            />
            <div className="form-text">
              Must be a valid SQL identifier. This will be the column name in your reports.
            </div>
          </div>

          {/* Enhanced placeholder information */}
          <div className="col-md-6">
            <label className="form-label">Available Placeholders</label>
            <div className="form-control" style={{ height: 'auto', minHeight: '38px' }}>
              <small className="text-muted">
                Click "Placeholders" in SQL editor to see all options. 
                Examples: <code className="text-primary">{`{current_cycle}`}</code>, <code className="text-primary">{`{previous_cycle}`}</code>
              </small>
            </div>
          </div>

          <div className="col-12">
            <label className="form-label">SQL Query with Enhanced Placeholder Support *</label>
            
            <SqlEditor
              value={calculation.source_field || ''}
              onChange={handleSqlChange}
              groupLevel={calculation.level}
              disabled={isSaving}
              resultColumnName={calculation.weight_field || 'result_column'}
              onValidate={handleValidateSQL}
              validationResult={sqlValidationResult}
              placeholder={`-- Enhanced SQL with Placeholders
-- Example: Deal growth analysis with previous cycle comparison
WITH current_balances AS (
    SELECT 
        deal.dl_nbr,
        SUM(tranchebal.tr_end_bal_amt) as current_balance,
        COUNT(tranche.tr_id) as tranche_count
    FROM deal
    JOIN tranche ON deal.dl_nbr = tranche.dl_nbr
    JOIN tranchebal ON tranche.dl_nbr = tranchebal.dl_nbr 
        AND tranche.tr_id = tranchebal.tr_id
    WHERE tranchebal.cycle_cde = {current_cycle}
        AND {deal_tranche_filter}
    GROUP BY deal.dl_nbr
),
previous_balances AS (
    SELECT 
        deal.dl_nbr,
        SUM(tranchebal.tr_end_bal_amt) as previous_balance
    FROM deal
    JOIN tranche ON deal.dl_nbr = tranche.dl_nbr
    JOIN tranchebal ON tranche.dl_nbr = tranchebal.dl_nbr 
        AND tranche.tr_id = tranchebal.tr_id
    WHERE tranchebal.cycle_cde = {previous_cycle}
        AND {deal_tranche_filter}
    GROUP BY deal.dl_nbr
)
SELECT 
    c.dl_nbr,
    CASE 
        WHEN p.previous_balance IS NULL THEN 'New Deal'
        WHEN c.current_balance > p.previous_balance * 1.1 THEN 'Growing'
        WHEN c.current_balance < p.previous_balance * 0.9 THEN 'Declining'
        ELSE 'Stable'
    END AS ${calculation.weight_field || 'result_column'}
FROM current_balances c
LEFT JOIN previous_balances p ON c.dl_nbr = p.dl_nbr`}
            />
          </div>

          {/* Enhanced Examples Section */}
          <div className="col-12">
            <div className="card bg-light border-info">
              <div className="card-header bg-info text-white">
                <h6 className="mb-0">
                  <i className="bi bi-lightbulb me-2"></i>
                  Enhanced SQL Examples with Placeholders
                </h6>
              </div>
              <div className="card-body">
                <div className="row">
                  <div className="col-md-4">
                    <h6 className="text-info">Period-over-Period Analysis</h6>
                    <div className="bg-dark text-light p-2 rounded small" style={{ fontFamily: 'monospace' }}>
{`-- Compare current vs previous
WHERE cycle_cde = {current_cycle}
-- Previous cycle data  
WHERE cycle_cde = {previous_cycle}
-- Two cycles back
WHERE cycle_cde = {cycle_minus_2}`}
                    </div>
                  </div>
                  <div className="col-md-4">
                    <h6 className="text-info">Dynamic Filtering</h6>
                    <div className="bg-dark text-light p-2 rounded small" style={{ fontFamily: 'monospace' }}>
{`-- Combined deal/tranche filter
WHERE {deal_tranche_filter}
-- Just deal filter
WHERE {deal_filter}
-- Direct deal list
IN ({deal_numbers})`}
                    </div>
                  </div>
                  <div className="col-md-4">
                    <h6 className="text-info">Window Functions</h6>
                    <div className="bg-dark text-light p-2 rounded small" style={{ fontFamily: 'monospace' }}>
{`-- Ranking within cycle
ROW_NUMBER() OVER (
  ORDER BY balance DESC
) as rank
-- Running totals
SUM(balance) OVER (
  ORDER BY dl_nbr
) as running_total`}
                    </div>
                  </div>
                </div>
                
                <div className="alert alert-success mt-3 mb-0">
                  <small>
                    <strong>💡 Pro Tip:</strong> Use <code>{`{deal_tranche_filter}`}</code> for comprehensive filtering that adapts to user selections.
                    Previous cycle placeholders enable powerful trend analysis and period comparisons.
                  </small>
                </div>
              </div>
            </div>
          </div>

          {/* Enhanced client-side validation feedback */}
          {clientValidationResult && !clientValidationResult.isValid && (
            <div className="col-12">
              <div className="alert alert-warning">
                <h6 className="alert-heading">
                  <i className="bi bi-exclamation-triangle me-2"></i>
                  Client-side Validation Issues
                </h6>
                <ul className="mb-0">
                  {clientValidationResult.errors.map((error: string, index: number) => (
                    <li key={index}>{error}</li>
                  ))}
                </ul>
                {clientValidationResult.warnings && clientValidationResult.warnings.length > 0 && (
                  <div className="mt-2">
                    <strong>Warnings:</strong>
                    <ul className="mb-0">
                      {clientValidationResult.warnings.map((warning: string, index: number) => (
                        <li key={index} className="text-warning">{warning}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <small className="text-muted mt-2 d-block">
                  Fix these issues before server validation. Some validation happens only on the server.
                </small>
              </div>
            </div>
          )}

          {/* Enhanced server validation results */}
          {sqlValidationResult && (
            <div className="col-12">
              <div className={`alert ${sqlValidationResult.is_valid ? 'alert-success' : 'alert-danger'} mt-3`}>
                <div className="d-flex align-items-center mb-2">
                  <i className={`bi ${sqlValidationResult.is_valid ? 'bi-check-circle' : 'bi-exclamation-triangle'} me-2`}></i>
                  <strong>
                    {sqlValidationResult.is_valid ? 'Enhanced SQL Validation Passed' : 'SQL Validation Failed'}
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
                  <div className="mb-2">
                    <strong className="text-warning">Warnings:</strong>
                    <ul className="mb-0 mt-1">
                      {sqlValidationResult.warnings.map((warning: string, index: number) => (
                        <li key={index} className="text-warning">{warning}</li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {sqlValidationResult.placeholders_used && sqlValidationResult.placeholders_used.length > 0 && (
                  <div className="mb-2">
                    <strong className="text-info">Placeholders Detected:</strong>
                    <div className="mt-1">
                      {sqlValidationResult.placeholders_used.map((placeholder: string, index: number) => (
                        <span key={index} className="badge bg-info me-1">
                          {`{${placeholder}}`}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                
                {sqlValidationResult.is_valid && (
                  <div className="mt-2">
                    <div className="row">
                      <div className="col-md-6">
                        <small className="text-success d-block">
                          <strong>✅ Validation Passed:</strong>
                          <ul className="mb-0 mt-1">
                            <li>SQL structure is valid</li>
                            <li>Required columns included</li>
                            <li>Placeholders are valid</li>
                            <li>Security checks passed</li>
                          </ul>
                        </small>
                      </div>
                      {sqlValidationResult.has_ctes && (
                        <div className="col-md-6">
                          <small className="text-info d-block">
                            <strong>📊 Advanced Features Detected:</strong>
                            <ul className="mb-0 mt-1">
                              {sqlValidationResult.has_ctes && <li>Common Table Expressions (CTEs)</li>}
                              {sqlValidationResult.has_subqueries && <li>Subqueries</li>}
                              {sqlValidationResult.used_tables && sqlValidationResult.used_tables.length > 2 && <li>Complex multi-table joins</li>}
                            </ul>
                          </small>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Enhanced Requirements */}
          <div className="col-12">
            <div className="card bg-light border-primary">
              <div className="card-body">
                <h6 className="card-title text-primary">
                  <i className="bi bi-list-check me-2"></i>
                  Enhanced SQL Requirements for {calculation.level} Level:
                </h6>
                <div className="row">
                  <div className="col-md-6">
                    <h6 className="text-success">✅ Required (You Must Include):</h6>
                    <ul className="mb-2">
                      <li>SELECT <code>deal.dl_nbr</code> (or <code>dl_nbr</code>)</li>
                      {calculation.level === 'tranche' && (
                        <li>SELECT <code>tranche.tr_id</code> (or <code>tr_id</code>)</li>
                      )}
                      <li>Return result column: <code>{calculation.weight_field || 'result_column'}</code></li>
                      <li>Proper FROM/JOIN structure</li>
                      <li>Use placeholders for dynamic filtering</li>
                    </ul>
                  </div>
                  <div className="col-md-6">
                    <h6 className="text-info">✨ Enhanced Features Available:</h6>
                    <ul className="mb-2">
                      <li>Period comparisons with <code>{`{previous_cycle}`}</code></li>
                      <li>Dynamic filtering with <code>{`{deal_tranche_filter}`}</code></li>
                      <li>CTEs and window functions</li>
                      <li>Complex analytical calculations</li>
                    </ul>
                  </div>
                </div>
                <div className="alert alert-info mb-0 mt-2">
                  <small>
                    <strong>🚀 New in Enhanced Mode:</strong> Use placeholders to create calculations that adapt to different 
                    reporting cycles and selections automatically. Perfect for trend analysis and period comparisons!
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
              {modalType === 'system-sql' && (
                <span className="badge bg-light text-dark ms-2">Enhanced</span>
              )}
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
                {/* Enhanced error display - show both generic error and save error */}
                {(error || saveError) && (
                  <div className="alert alert-danger" role="alert">
                    <div className="d-flex align-items-start">
                      <i className="bi bi-exclamation-triangle-fill me-2 flex-shrink-0" style={{ marginTop: '2px' }}></i>
                      <div className="flex-grow-1">
                        <strong>Error:</strong>
                        <div className="mt-1">
                          {saveError && (
                            <div className="mb-2">
                              <strong>Save Error:</strong> {saveError}
                            </div>
                          )}
                          {error && error !== saveError && (
                            <div>
                              <strong>General Error:</strong> {error}
                            </div>
                          )}
                        </div>
                        
                        {/* Common solutions for SQL errors */}
                        {(saveError || error) && (
                          <div className="mt-3 p-2 bg-light rounded border-start border-3 border-warning">
                            <small className="text-muted">
                              <strong>💡 Common Solutions:</strong>
                              <ul className="mb-0 mt-1 small">
                                <li>Make sure your SQL starts with <code>SELECT</code> or <code>WITH</code> for CTEs</li>
                                <li>Include required columns: <code>deal.dl_nbr</code> and <code>tranche.tr_id</code> (for tranche level)</li>
                                <li>Use valid SQL syntax and proper JOIN conditions</li>
                                <li>Check that all placeholders are valid (use the Placeholders button)</li>
                                <li>Ensure your result column name matches a column in your SELECT statement</li>
                              </ul>
                            </small>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {renderModalContent()}
              </>
            )}
          </div>

          {/* Enhanced Modal Footer */}
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
                    <i className="bi bi-shield-check me-2"></i>
                    Validate Enhanced SQL
                  </>
                )}
              </button>
            )}
            <button
              type="button"
              onClick={handleSave}
              disabled={
                isSaving || 
                fieldsLoading || 
                (modalType === 'system-sql' && !editingCalculation && (!sqlValidationResult || !sqlValidationResult.is_valid)) ||
                (modalType === 'system-sql' && clientValidationResult && !clientValidationResult.isValid)
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
                  {editingCalculation ? 'Update Enhanced Calculation' : 'Save Enhanced Calculation'}
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