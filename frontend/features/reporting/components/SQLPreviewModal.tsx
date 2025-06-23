import React, { useState } from 'react';
import useModal from '@/hooks/useModal';
import styles from '@/styles/components/SQLPreview.module.css';
import { useToast } from '@/context/ToastContext';
import apiClient from '@/services/apiClient';

interface SQLPreviewModalProps {
  show: boolean;
  onHide: () => void;
  previewData: any;
  loading: boolean;
  reportName: string;
}

const SQLPreviewModal: React.FC<SQLPreviewModalProps> = ({
  show,
  onHide,
  previewData,
  loading,
  reportName
}) => {
  const { modalRef, closeModal } = useModal(show, onHide);
  const { showToast } = useToast();
  
  // Execution state for individual calculations
  const [executingCalcs, setExecutingCalcs] = useState<Set<string>>(new Set());
  const [executionResults, setExecutionResults] = useState<{[key: string]: any}>({});
  const [executionErrors, setExecutionErrors] = useState<{[key: string]: string}>({});
  const [showResults, setShowResults] = useState<{[key: string]: boolean}>({});

  const handleClose = () => {
    closeModal();
  };

  // Function to extract calculation ID from preview data
  const extractCalculationId = async (calcData: any): Promise<number | null> => {
    try {
      // Handle different calculation ID formats
      if (typeof calcData.calculation_id === 'number') {
        return calcData.calculation_id;
      }
      
      if (typeof calcData.calc_id === 'number') {
        return calcData.calc_id;
      }
      
      // Handle string-based calculation IDs (like "user.balance_amount" or "system.total_loan_amount")
      if (typeof calcData.calculation_id === 'string') {
        const calcId = calcData.calculation_id;
        
        if (calcId.startsWith('user.')) {
          // Extract source field from user calculation ID
          const sourceField = calcId.replace('user.', '');
          try {
            const response = await fetch(`/api/calculations/user/by-source-field/${encodeURIComponent(sourceField)}`);
            if (response.ok) {
              const data = await response.json();
              return data.calculation_id;
            }
          } catch (error) {
            console.error('Error looking up user calculation:', error);
          }
        } else if (calcId.startsWith('system.')) {
          // Extract result column from system calculation ID
          const resultColumn = calcId.replace('system.', '');
          try {
            const response = await fetch(`/api/calculations/system/by-result-column/${encodeURIComponent(resultColumn)}`);
            if (response.ok) {
              const data = await response.json();
              return data.calculation_id;
            }
          } catch (error) {
            console.error('Error looking up system calculation:', error);
          }
        }
      }
      
      // Handle legacy numeric string IDs
      if (typeof calcData.calculation_id === 'string' && /^\d+$/.test(calcData.calculation_id)) {
        return parseInt(calcData.calculation_id, 10);
      }
      
      console.warn('Could not extract numeric calculation ID from:', calcData);
      return null;
    } catch (error) {
      console.error('Error extracting calculation ID:', error);
      return null;
    }
  };

  const handleExecuteCalculation = async (calcData: any) => {
    try {
      setExecutingCalcs(prev => new Set([...prev, calcData.alias || calcData]));
      setExecutionErrors(prev => ({ ...prev, [calcData.alias || calcData]: '' }));
      setExecutionResults(prev => ({ ...prev, [calcData.alias || calcData]: null }));

      const executionParams = {
        deal_tranche_map: previewData?.parameters?.deal_tranche_map || { 101: ['A', 'B'], 102: [], 103: [] },
        cycle_code: previewData?.parameters?.cycle_code || 202404
      };

      // Check if this is raw SQL from preview data (has sql property but no calculation_id)
      if (calcData.sql && !calcData.calculation_id && !calcData.calc_id) {
        // This is raw SQL from field introspection - execute it using the new execute-raw-sql endpoint
        const requestData = {
          sql_text: calcData.sql,
          deal_tranche_map: executionParams.deal_tranche_map,
          cycle_code: executionParams.cycle_code,
          alias: calcData.alias || 'field_introspection'
        };

        // Use the new execute-raw-sql endpoint for field introspection
        const response = await apiClient.post('/calculations/execute-raw-sql', requestData);
        
        // FIXED: Check the response success status before showing toast
        if (response.data.success) {
          setExecutionResults(prev => ({ ...prev, [calcData.alias || calcData]: response.data }));
          setShowResults(prev => ({ ...prev, [calcData.alias || calcData]: true }));
          showToast('Field introspection executed successfully!', 'success');
        } else {
          // Handle SQL execution failure
          const errorMsg = response.data.error || 'SQL execution failed';
          setExecutionErrors(prev => ({ ...prev, [calcData.alias || calcData]: errorMsg }));
          showToast(`Field introspection failed: ${errorMsg}`, 'error');
        }
        
      } else {
        // This has a calculation ID - use the existing approach
        const calculationId = await extractCalculationId(calcData);
        
        if (calculationId === null) {
          throw new Error(`Could not determine calculation ID for: ${calcData.alias || JSON.stringify(calcData)}`);
        }

        const requestData = {
          calculation_requests: [
            {
              calc_id: calculationId,
              alias: calcData.alias || calcData
            }
          ],
          deal_tranche_map: executionParams.deal_tranche_map,
          cycle_code: executionParams.cycle_code,
          report_scope: "TRANCHE"
        };

        const response = await apiClient.post('/calculations/execute-separate', requestData);
        const result = response.data;
        
        setExecutionResults(prev => ({ ...prev, [calcData.alias || calcData]: result }));
        setShowResults(prev => ({ ...prev, [calcData.alias || calcData]: true }));
        showToast('Calculation executed successfully!', 'success');
      }
      
    } catch (error: any) {
      console.error('Error executing calculation:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to execute calculation';
      setExecutionErrors(prev => ({ ...prev, [calcData.alias || calcData]: errorMessage }));
      showToast(`Error executing calculation: ${errorMessage}`, 'error');
    } finally {
      setExecutingCalcs(prev => {
        const newSet = new Set(prev);
        newSet.delete(calcData.alias || calcData);
        return newSet;
      });
    }
  };

  const formatExecutionResults = (calcId: string) => {
    const results = executionResults[calcId];
    
    if (!results) {
      return <div className="text-muted">No results available</div>;
    }
    
    // Handle different response formats
    let data = null;
    if (results.data && Array.isArray(results.data)) {
      // New format: { data: [...], row_count: 17, columns: [...] }
      data = results.data;
    } else if (results.results && Array.isArray(results.results)) {
      // Old format: { results: [...] }
      data = results.results;
    } else if (Array.isArray(results)) {
      // Direct array format
      data = results;
    }
    
    if (!data || data.length === 0) {
      return <div className="text-muted">No results returned</div>;
    }

    const columns = Object.keys(data[0]);

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
            {data.slice(0, 100).map((row: any, index: number) => (
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
        {data.length > 100 && (
          <div className="text-muted text-center py-2">
            Showing first 100 rows of {data.length} total results
          </div>
        )}
      </div>
    );
  };

  const hasCDICalculations = previewData?.cdi_sql_previews && previewData.cdi_sql_previews.length > 0;

  return (
    <div
      className={`modal fade ${show ? 'show' : ''} ${styles.sqlPreviewModal}`}
      style={{ display: show ? 'block' : 'none' }}
      tabIndex={-1}
      ref={modalRef}
      aria-labelledby="sqlPreviewModalLabel"
      aria-hidden={!show}
    >
      <div className="modal-dialog modal-xl">
        <div className={`modal-content ${styles.sqlPreviewModalContent}`}>
          <div className={`modal-header ${styles.sqlPreviewModalHeader}`}>
            <h5 className="modal-title" id="sqlPreviewModalLabel">
              <i className="bi bi-code-square me-2"></i>
              SQL Preview: {reportName}
            </h5>
            <button
              type="button"
              className="btn-close btn-close-white"
              onClick={handleClose}
              aria-label="Close"
            ></button>
          </div>

          <div className={`modal-body ${styles.sqlPreviewModalBody}`}>
            {loading ? (
              <div className={styles.previewLoadingContainer}>
                <div className={`spinner-border text-primary ${styles.previewLoadingSpinner}`} role="status">
                  <span className="visually-hidden">Loading...</span>
                </div>
                <span className={styles.previewLoadingText}>Generating SQL preview...</span>
              </div>
            ) : previewData ? (
              <div>
                {/* Report Summary */}
                <div className={styles.detailsGrid}>
                  <div className={styles.detailsCard}>
                    <h6 className={styles.detailsCardTitle}>Report Details</h6>
                    <div className={styles.detailsCardContent}>
                      <div className="mb-2">
                        <strong>Name:</strong> {reportName}
                      </div>
                      <div className="mb-2">
                        <strong>Execution Method:</strong>{' '}
                        <span className={`${styles.badge} ${styles.badgeInfo}`}>
                          Individual Calculation Execution
                        </span>
                      </div>
                      <div>
                        <strong>Calculations:</strong>{' '}
                        <span className={`${styles.badge} ${styles.badgeSecondary}`}>
                          {previewData.summary?.total_calculations || 0} calculations
                        </span>
                        {hasCDICalculations && (
                          <span className={`ms-2 ${styles.badge} ${styles.badgePrimary}`}>
                            {previewData.summary?.cdi_calculations || 0} CDI
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className={styles.detailsCard}>
                    <h6 className={styles.detailsCardTitle}>Execution Strategy</h6>
                    <div className={styles.detailsCardContent}>
                      <div className="mb-2">
                        <strong>Base Query:</strong> Retrieves deal/tranche data and static fields
                      </div>
                      <div>
                        <strong>Calculations:</strong> Executed individually and merged with base data
                      </div>
                    </div>
                  </div>
                </div>

                {/* Base Query Section */}
                {previewData.base_query && (
                  <div className="mb-4">
                    <div className="d-flex align-items-center mb-3">
                      <h6 className="mb-0 me-3">
                        <i className="bi bi-database me-2"></i>
                        Base Query (Static Fields)
                      </h6>
                      <span className={`${styles.badge} ${styles.badgeSuccess}`}>
                        Always executed first
                      </span>
                    </div>
                    
                    <div className={styles.sqlContainer}>
                      <div className={styles.sqlHeader}>
                        <span className={styles.sqlTitle}>Base Data Query</span>
                        <button
                          className={`btn btn-sm btn-outline-secondary ${styles.copyButton}`}
                          onClick={() => navigator.clipboard.writeText(previewData.base_query)}
                          title="Copy SQL to clipboard"
                        >
                          <i className="bi bi-clipboard"></i>
                        </button>
                      </div>
                      <pre className={styles.sqlContent}>
                        <code>{previewData.base_query}</code>
                      </pre>
                    </div>
                  </div>
                )}

                {/* Individual Calculations Section */}
                {previewData.calculation_queries && previewData.calculation_queries.length > 0 && (
                  <div className="mb-4">
                    <div className="d-flex align-items-center mb-3">
                      <h6 className="mb-0 me-3">
                        <i className="bi bi-calculator me-2"></i>
                        Individual Calculations
                      </h6>
                      <span className={`${styles.badge} ${styles.badgeInfo}`}>
                        {previewData.calculation_queries.length} calculations
                      </span>
                    </div>
                    
                    <div className="accordion" id="calculationAccordion">
                      {previewData.calculation_queries.map((query: any, index: number) => (
                        <div key={query.alias || index} className="accordion-item">
                          <h2 className="accordion-header" id={`heading${index}`}>
                            <button
                              className="accordion-button collapsed"
                              type="button"
                              data-bs-toggle="collapse"
                              data-bs-target={`#collapse${index}`}
                              aria-expanded="false"
                              aria-controls={`collapse${index}`}
                            >
                              <div className="d-flex align-items-center w-100">
                                <i className="bi bi-gear me-2"></i>
                                <span className="fw-bold me-2">{query.alias || `Calculation ${index + 1}`}</span>
                                <span className={`${styles.badge} ${styles.badgeSecondary} ms-auto me-2`}>
                                  {query.type || 'Individual Query'}
                                </span>
                              </div>
                            </button>
                          </h2>
                          <div
                            id={`collapse${index}`}
                            className="accordion-collapse collapse"
                            aria-labelledby={`heading${index}`}
                            data-bs-parent="#calculationAccordion"
                          >
                            <div className="accordion-body">
                              {/* Display calculation description if available */}
                              {query.description && (
                                <div className="mb-3">
                                  <div className="alert alert-light">
                                    <i className="bi bi-info-circle me-2"></i>
                                    {query.description}
                                  </div>
                                </div>
                              )}

                              {/* Execution Controls */}
                              <div className="mb-3 d-flex justify-content-between align-items-center">
                                <div className="d-flex gap-2">
                                  <button
                                    className="btn btn-success btn-sm"
                                    onClick={() => handleExecuteCalculation(query)}
                                    disabled={executingCalcs.has(query.alias || index.toString())}
                                    title="Execute this calculation with sample data to see actual results"
                                  >
                                    {executingCalcs.has(query.alias || index.toString()) ? (
                                      <>
                                        <span className="spinner-border spinner-border-sm me-2" role="status"></span>
                                        Executing...
                                      </>
                                    ) : (
                                      <>
                                        <i className="bi bi-play-fill me-2"></i>
                                        Execute
                                      </>
                                    )}
                                  </button>
                                  {executionResults[query.alias || index.toString()] && (
                                    <button
                                      className={`btn btn-sm ${showResults[query.alias || index.toString()] ? 'btn-outline-primary' : 'btn-primary'}`}
                                      onClick={() => setShowResults(prev => ({ ...prev, [query.alias || index.toString()]: !prev[query.alias || index.toString()] }))}
                                    >
                                      <i className={`bi ${showResults[query.alias || index.toString()] ? 'bi-eye-slash' : 'bi-eye'} me-2`}></i>
                                      {showResults[query.alias || index.toString()] ? 'Hide Results' : 'Show Results'}
                                    </button>
                                  )}
                                </div>
                                <div className="text-muted small">
                                  <i className="bi bi-info-circle me-1"></i>
                                  Test with real data
                                </div>
                              </div>

                              {/* Execution Results */}
                              {executionResults[query.alias || index.toString()] && showResults[query.alias || index.toString()] && (
                                <div className="mb-4">
                                  <div className="card">
                                    <div className="card-header bg-success text-white">
                                      <div className="d-flex justify-content-between align-items-center">
                                        <h6 className="mb-0">
                                          <i className="bi bi-check-circle me-2"></i>
                                          Execution Results: {query.alias || `Calculation ${index + 1}`}
                                        </h6>
                                        <div className="d-flex gap-3">
                                          <span className="badge bg-light text-dark">
                                            {executionResults[query.alias || index.toString()].row_count} rows
                                          </span>
                                          <span className="badge bg-light text-dark">
                                            {executionResults[query.alias || index.toString()].execution_time_ms}ms
                                          </span>
                                        </div>
                                      </div>
                                    </div>
                                    <div className="card-body p-0">
                                      {formatExecutionResults(query.alias || index.toString())}
                                    </div>
                                  </div>
                                </div>
                              )}

                              {/* Execution Error */}
                              {executionErrors[query.alias || index.toString()] && (
                                <div className="mb-4">
                                  <div className="alert alert-danger">
                                    <h6 className="alert-heading">
                                      <i className="bi bi-exclamation-triangle me-2"></i>
                                      Execution Failed: {query.alias || `Calculation ${index + 1}`}
                                    </h6>
                                    <p className="mb-0">{executionErrors[query.alias || index.toString()]}</p>
                                  </div>
                                </div>
                              )}

                              <div className={styles.sqlContainer}>
                                <div className={styles.sqlHeader}>
                                  <span className={styles.sqlTitle}>Calculation: {query.alias || `Calculation ${index + 1}`}</span>
                                  <button
                                    className={`btn btn-sm btn-outline-secondary ${styles.copyButton}`}
                                    onClick={() => {
                                      // Extract SQL properly from query object or string
                                      const sqlText = typeof query === 'string' ? query :
                                                     query?.sql || query?.generated_sql || 
                                                     JSON.stringify(query, null, 2);
                                      navigator.clipboard.writeText(sqlText);
                                    }}
                                    title="Copy SQL to clipboard"
                                  >
                                    <i className="bi bi-clipboard"></i>
                                  </button>
                                </div>
                                <pre className={styles.sqlContent}>
                                  <code>{(() => {
                                    // Handle different response formats for individual calculations
                                    if (typeof query === 'string') {
                                      return query;
                                    }
                                    
                                    // If it's an object, try to extract SQL from common properties
                                    if (query && typeof query === 'object') {
                                      if (query.sql) return query.sql;
                                      if (query.generated_sql) return query.generated_sql;
                                      if (query.query) return query.query;
                                      if (query.raw_sql) return query.raw_sql;
                                      
                                      // If none of the expected properties exist, show formatted JSON
                                      return JSON.stringify(query, null, 2);
                                    }
                                    
                                    return 'No SQL data available';
                                  })()}</code>
                                </pre>
                              </div>
                              <div className="mt-2">
                                <small className="text-muted">
                                  <i className="bi bi-info-circle me-1"></i>
                                  This calculation will be executed separately and merged with the base query results.
                                </small>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* CDI Calculations Section */}
                {previewData.cdi_calculations && Object.keys(previewData.cdi_calculations).length > 0 && (
                  <div className="mb-4">
                    <div className="d-flex align-items-center mb-3">
                      <h6 className="mb-0 me-3">
                        <i className="bi bi-file-earmark-code me-2"></i>
                        CDI Calculations
                      </h6>
                      <span className={`${styles.badge} ${styles.badgePrimary}`}>
                        {Object.keys(previewData.cdi_calculations).length} CDI calculations
                      </span>
                    </div>
                    
                    <div className="accordion" id="cdiCalculationAccordion">
                      {Object.entries(previewData.cdi_calculations).map(([calcId, details], index) => (
                        <div key={calcId} className="accordion-item">
                          <h2 className="accordion-header" id={`cdi-heading${index}`}>
                            <button
                              className="accordion-button collapsed"
                              type="button"
                              data-bs-toggle="collapse"
                              data-bs-target={`#cdi-collapse${index}`}
                              aria-expanded="false"
                              aria-controls={`cdi-collapse${index}`}
                            >
                              <div className="d-flex align-items-center w-100">
                                <i className="bi bi-file-earmark-code me-2"></i>
                                <span className="fw-bold me-2">{calcId}</span>
                                <span className={`${styles.badge} ${styles.badgePrimary} ms-auto me-2`}>
                                  CDI Field
                                </span>
                              </div>
                            </button>
                          </h2>
                          <div
                            id={`cdi-collapse${index}`}
                            className="accordion-collapse collapse"
                            aria-labelledby={`cdi-heading${index}`}
                            data-bs-parent="#cdiCalculationAccordion"
                          >
                            <div className="accordion-body">
                              <div className="mb-3">
                                <strong>CDI Field:</strong> {(details as any).field_name || calcId}
                              </div>
                              <div className="alert alert-info">
                                <i className="bi bi-info-circle me-2"></i>
                                CDI calculations are extracted directly from uploaded CDI files and do not require SQL queries.
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Execution Flow Information */}
                <div className="mb-4">
                  <div className="alert alert-light border">
                    <h6 className="alert-heading">
                      <i className="bi bi-arrow-repeat me-2"></i>
                      Execution Flow
                    </h6>
                    <ol className="mb-0">
                      <li><strong>Base Query:</strong> Retrieves static fields (Deal Number, Tranche ID, Cycle Code, etc.)</li>
                      <li><strong>Individual Calculations:</strong> Each calculation executes separately with its own optimized query</li>
                      <li><strong>CDI Calculations:</strong> Values extracted from uploaded CDI files</li>
                      <li><strong>Data Merging:</strong> All results combined into final report structure</li>
                      <li><strong>Error Handling:</strong> Failed calculations show as null values; report continues with successful data</li>
                    </ol>
                  </div>
                </div>

                {/* Legacy unified SQL notice */}
                {!previewData.base_query && !previewData.calculation_queries && previewData.sql_previews && Object.keys(previewData.sql_previews).length > 0 && (
                  <div className="alert alert-warning">
                    <i className="bi bi-exclamation-triangle me-2"></i>
                    <strong>Legacy Format:</strong> This preview is showing the old unified SQL format. The actual execution will use individual calculation queries for better performance and error handling.
                  </div>
                )}

                {/* No preview data */}
                {!previewData.base_query && !previewData.calculation_queries && (!previewData.sql_previews || Object.keys(previewData.sql_previews).length === 0) && (
                  <div className="alert alert-warning">
                    <i className="bi bi-exclamation-triangle me-2"></i>
                    No SQL preview data available for this report configuration.
                  </div>
                )}
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
              onClick={handleClose}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SQLPreviewModal;