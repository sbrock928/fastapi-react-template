import React, { useState } from 'react';
import type { PreviewData } from '@/types/calculations';
import { formatSQL, highlightSQL } from '@/utils/sqlFormatter';
import styles from '@/styles/components/SQLPreview.module.css';
import calculationsApi from '@/services/calculationsApi';
import { useToast } from '@/context/ToastContext';

interface SqlPreviewModalProps {
  isOpen: boolean;
  previewData: PreviewData | null;
  previewLoading: boolean;
  onClose: () => void;
  calculationId?: number | null;
  calculationType?: 'user_calculation' | 'system_calculation';
}

const SqlPreviewModal: React.FC<SqlPreviewModalProps> = ({
  isOpen,
  previewData,
  previewLoading,
  onClose,
  calculationId,
  calculationType = 'user_calculation'
}) => {
  const { showToast } = useToast();
  const [executing, setExecuting] = useState(false);
  const [executionResults, setExecutionResults] = useState<any>(null);
  const [executionError, setExecutionError] = useState<string | null>(null);
  const [showResults, setShowResults] = useState(false);

  if (!isOpen) return null;

  const handleCopySQL = () => {
    const sql = previewData?.sql || previewData?.generated_sql;
    if (sql) {
      navigator.clipboard.writeText(sql);
      showToast('SQL copied to clipboard!', 'success');
    }
  };

  const handleExecuteCalculation = async () => {
    if (!calculationId || !previewData) {
      showToast('Cannot execute: Missing calculation information', 'error');
      return;
    }

    setExecuting(true);
    setExecutionError(null);
    setExecutionResults(null);

    try {
      const executionParams = {
        deal_tranche_mapping: getDealMap() || { 101: ['A', 'B'], 102: [], 103: [] },
        cycle_code: getCycleCode() || 202404
      };

      const response = await calculationsApi.executeSeparateCalculation(
        calculationId,
        calculationType,
        executionParams
      );

      setExecutionResults(response.data);
      setShowResults(true);
      showToast(`Execution completed successfully! Retrieved ${response.data.row_count} rows in ${response.data.execution_time_ms}ms`, 'success');
    } catch (error: any) {
      console.error('Error executing calculation:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to execute calculation';
      setExecutionError(errorMessage);
      showToast(`Execution failed: ${errorMessage}`, 'error');
    } finally {
      setExecuting(false);
    }
  };

  // Handle both old and new API response formats
  const getCalculationName = () => {
    if (previewData?.calculation_name) return previewData.calculation_name;
    // Extract from columns - the last column is usually the calculation result
    if (previewData?.columns && previewData.columns.length > 0) {
      return previewData.columns[previewData.columns.length - 1];
    }
    return 'Unknown Calculation';
  };

  const getCalculationType = () => {
    return previewData?.calculation_type || 'Unknown';
  };

  const getGroupLevel = () => {
    return previewData?.group_level || previewData?.aggregation_level || 'Unknown';
  };

  const getSql = () => {
    return previewData?.sql || previewData?.generated_sql || '';
  };

  const getParameters = () => {
    return previewData?.parameters || previewData?.sample_parameters || {};
  };

  const getDealMap = () => {
    const params = getParameters();
    // Type-safe access to deal map properties
    if ('deal_tranche_map' in params) {
      return params.deal_tranche_map;
    }
    if ('deal_tranche_mapping' in params) {
      return params.deal_tranche_mapping;
    }
    return null;
  };

  const getCycleCode = () => {
    const params = getParameters();
    // Type-safe access to cycle properties
    if ('cycle_code' in params) {
      return params.cycle_code;
    }
    if ('cycle' in params) {
      return params.cycle;
    }
    return null;
  };

  const formatExecutionResults = () => {
    if (!executionResults?.data || executionResults.data.length === 0) {
      return <div className="text-muted">No results returned</div>;
    }

    const results = executionResults.data;
    const columns = Object.keys(results[0]);

    return (
      <div className="table-responsive" style={{ maxHeight: '400px', overflowY: 'auto' }}>
        <table className="table table-sm table-striped">
          <thead className="table-dark sticky-top">
            <tr>
              {columns.map(col => (
                <th key={col} scope="col">{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {results.slice(0, 100).map((row: any, index: number) => (
              <tr key={index}>
                {columns.map(col => (
                  <td key={col}>
                    {row[col] !== null && row[col] !== undefined ? 
                      (typeof row[col] === 'number' ? 
                        Number(row[col]).toLocaleString() : 
                        String(row[col])
                      ) : 
                      <span className="text-muted">NULL</span>
                    }
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {results.length > 100 && (
          <div className="text-muted text-center py-2">
            Showing first 100 rows of {results.length} total results
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="modal show d-block" tabIndex={-1} style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-xl modal-dialog-scrollable">
        <div className={`modal-content ${styles.sqlPreviewModalContent}`}>
          <div className={`modal-header ${styles.sqlPreviewModalHeader}`}>
            <h5 className="modal-title">
              <i className="bi bi-code-square me-2"></i>
              SQL Preview: {getCalculationName()}
            </h5>
            <button
              type="button"
              className="btn-close btn-close-white"
              onClick={onClose}
            ></button>
          </div>
          
          <div className={`modal-body ${styles.sqlPreviewModalBody}`}>
            {previewLoading ? (
              <div className={styles.previewLoadingContainer}>
                <div className={`spinner-border text-primary ${styles.previewLoadingSpinner}`} role="status">
                  <span className="visually-hidden">Loading...</span>
                </div>
                <span className={styles.previewLoadingText}>
                  Generating SQL preview...
                </span>
              </div>
            ) : previewData ? (
              <div>
                {/* Calculation Details */}
                <div className={styles.detailsGrid}>
                  <div className={styles.detailsCard}>
                    <h6 className={styles.detailsCardTitle}>
                      Calculation Details
                    </h6>
                    <div className={styles.detailsCardContent}>
                      <div className="mb-2">
                        <strong>Name:</strong> {getCalculationName()}
                      </div>
                      <div className="mb-2">
                        <strong>Type:</strong>{' '}
                        <span className={`${styles.badge} ${styles.badgePrimary}`}>
                          {getCalculationType()}
                        </span>
                      </div>
                      <div className="mb-2">
                        <strong>Level:</strong>{' '}
                        <span className={`${styles.badge} ${styles.badgeSecondary}`}>
                          {getGroupLevel()}
                        </span>
                      </div>
                      {previewData.columns && (
                        <div>
                          <strong>Returns:</strong> {previewData.columns.join(', ')}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className={styles.detailsCard}>
                    <h6 className={styles.detailsCardTitle}>
                      Sample Parameters
                    </h6>
                    <div className={styles.detailsCardContent}>
                      <div className="mb-1">
                        <strong>Deals:</strong> {(() => {
                          const dealMap = getDealMap();
                          return dealMap ? Object.keys(dealMap).join(', ') : 'N/A';
                        })()}
                      </div>
                      <div className="mb-1">
                        <strong>Tranches:</strong> {(() => {
                          const dealMap = getDealMap();
                          return dealMap ? Object.values(dealMap).flat().filter(t => t).join(', ') || 'All' : 'N/A';
                        })()}
                      </div>
                      <div>
                        <strong>Cycle:</strong> {getCycleCode() || 'N/A'}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="mb-3 d-flex justify-content-between align-items-center">
                  <div className="d-flex gap-2">
                    <button
                      className="btn btn-success"
                      onClick={handleExecuteCalculation}
                      disabled={executing || !calculationId}
                      title="Execute this calculation with sample data to see actual results"
                    >
                      {executing ? (
                        <>
                          <span className="spinner-border spinner-border-sm me-2" role="status"></span>
                          Executing...
                        </>
                      ) : (
                        <>
                          <i className="bi bi-play-fill me-2"></i>
                          Execute Calculation
                        </>
                      )}
                    </button>
                    {executionResults && (
                      <button
                        className={`btn ${showResults ? 'btn-outline-primary' : 'btn-primary'}`}
                        onClick={() => setShowResults(!showResults)}
                      >
                        <i className={`bi ${showResults ? 'bi-eye-slash' : 'bi-eye'} me-2`}></i>
                        {showResults ? 'Hide Results' : 'Show Results'}
                      </button>
                    )}
                  </div>
                  <div className="text-muted small">
                    <i className="bi bi-info-circle me-1"></i>
                    Execute to test with real data before adding to reports
                  </div>
                </div>

                {/* Execution Results */}
                {executionResults && showResults && (
                  <div className="mb-4">
                    <div className="card">
                      <div className="card-header bg-success text-white">
                        <div className="d-flex justify-content-between align-items-center">
                          <h6 className="mb-0">
                            <i className="bi bi-check-circle me-2"></i>
                            Execution Results
                          </h6>
                          <div className="d-flex gap-3">
                            <span className="badge bg-light text-dark">
                              {executionResults.row_count} rows
                            </span>
                            <span className="badge bg-light text-dark">
                              {executionResults.execution_time_ms}ms
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="card-body p-0">
                        {formatExecutionResults()}
                      </div>
                    </div>
                  </div>
                )}

                {/* Execution Error */}
                {executionError && (
                  <div className="mb-4">
                    <div className="alert alert-danger">
                      <h6 className="alert-heading">
                        <i className="bi bi-exclamation-triangle me-2"></i>
                        Execution Failed
                      </h6>
                      <p className="mb-0">{executionError}</p>
                    </div>
                  </div>
                )}
                
                {/* SQL Query */}
                <div className="mb-3">
                  <div className={styles.sqlSectionHeader}>
                    <h6 className={styles.sqlSectionTitle}>
                      Generated SQL Query
                    </h6>
                    <button
                      className={`btn btn-sm btn-outline-secondary ${styles.copyButton}`}
                      onClick={handleCopySQL}
                      title="Copy SQL to clipboard"
                    >
                      <i className="bi bi-clipboard me-1"></i>
                      Copy
                    </button>
                  </div>
                  <div 
                    className={styles['sql-code-enhanced']}
                    dangerouslySetInnerHTML={{
                      __html: highlightSQL(formatSQL(getSql()))
                    }}
                  />
                  <div className={styles.sqlNote}>
                    This is the exact SQL that executes when this calculation runs in a report.
                  </div>
                </div>
              </div>
            ) : (
              <div className={styles.previewEmptyState}>
                <i className={`bi bi-exclamation-circle ${styles.previewEmptyIcon}`}></i>
                <p>No preview data available</p>
              </div>
            )}
          </div>

          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SqlPreviewModal;