import React, { useState } from 'react';
import useModal from '@/hooks/useModal';
import styles from '@/styles/components/SQLPreview.module.css';
import { formatSQL, highlightSQL } from '@/utils/sqlFormatter';

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
  const [activeTab, setActiveTab] = useState<'unified' | 'cdi'>('unified');

  const handleClose = () => {
    closeModal();
  };

  const hasCDICalculations = previewData?.cdi_sql_previews && previewData.cdi_sql_previews.length > 0;
  const hasUnifiedSQL = previewData?.unified_sql || previewData?.complete_runtime_sql;

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
                      <div>
                        <strong>Calculations:</strong>{' '}
                        <span className={`${styles.badge} ${styles.badgeSecondary}`}>
                          {previewData.summary?.total_calculations || 0} selected
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
                    <h6 className={styles.detailsCardTitle}>Parameters</h6>
                    <div className={styles.detailsCardContent}>
                      <div className="mb-1">
                        <strong>Cycle Code:</strong> {previewData.parameters?.cycle_code}
                      </div>
                      <div className="mb-1">
                        <strong>Deals:</strong> {Object.keys(previewData.parameters?.deal_tranche_map || {}).length} selected
                      </div>
                      <div>
                        <strong>Breakdown:</strong> {previewData.summary?.static_fields || 0} static fields, {previewData.summary?.user_calculations || 0} user calculations, {previewData.summary?.system_calculations || 0} system calculations
                      </div>
                    </div>
                  </div>
                </div>

                {/* Tabbed Interface */}
                {(hasUnifiedSQL || hasCDICalculations) && (
                  <div className="mt-4">
                    {/* Tab Navigation */}
                    <ul className="nav nav-tabs" role="tablist">
                      {hasUnifiedSQL && (
                        <li className="nav-item" role="presentation">
                          <button
                            className={`nav-link ${activeTab === 'unified' ? 'active' : ''}`}
                            onClick={() => setActiveTab('unified')}
                            type="button"
                            role="tab"
                          >
                            <i className="bi bi-code me-2"></i>
                            Unified SQL
                            <span className={`ms-2 ${styles.badge} ${styles.badgeSecondary}`}>
                              {(previewData.summary?.total_calculations || 0) - (previewData.summary?.cdi_calculations || 0)}
                            </span>
                          </button>
                        </li>
                      )}
                      {hasCDICalculations && (
                        <li className="nav-item" role="presentation">
                          <button
                            className={`nav-link ${activeTab === 'cdi' ? 'active' : ''}`}
                            onClick={() => setActiveTab('cdi')}
                            type="button"
                            role="tab"
                          >
                            <i className="bi bi-database me-2"></i>
                            CDI Calculations
                            <span className={`ms-2 ${styles.badge} ${styles.badgePrimary}`}>
                              {previewData.summary?.cdi_calculations || 0}
                            </span>
                          </button>
                        </li>
                      )}
                    </ul>

                    {/* Tab Content */}
                    <div className="tab-content mt-3">
                      {/* Unified SQL Tab */}
                      {hasUnifiedSQL && activeTab === 'unified' && (
                        <div className="tab-pane fade show active">
                          {previewData.complete_runtime_sql ? (
                            // Complete runtime SQL - shows exactly what gets executed
                            <div className="mb-3">
                              <div className="d-flex justify-content-between align-items-center mb-2">
                                <h6 className={styles.sqlSectionTitle}>
                                  <i className="bi bi-play-circle me-2"></i>
                                  Complete Runtime SQL
                                </h6>
                                <button
                                  className={`btn btn-sm btn-outline-secondary ${styles.copyButton}`}
                                  onClick={() => navigator.clipboard.writeText(previewData.complete_runtime_sql)}
                                  title="Copy complete runtime SQL to clipboard"
                                >
                                  <i className="bi bi-clipboard me-1"></i>
                                  Copy
                                </button>
                              </div>
                              
                              <div 
                                className={styles['sql-code-enhanced']}
                                dangerouslySetInnerHTML={{
                                  __html: highlightSQL(formatSQL(previewData.complete_runtime_sql))
                                }}
                              />
                              
                              <div className={`alert ${styles.previewInfoAlert} mt-3`}>
                                <i className={`bi bi-info-circle ${styles.previewInfoIcon}`}></i>
                                <strong>Runtime SQL:</strong> This is the exact SQL query that will be executed for regular calculations, 
                                including all CTEs, joins, filters, and aggregations with your specific parameters applied.
                              </div>
                            </div>
                          ) : previewData.unified_sql ? (
                            // Unified SQL format (fallback)
                            <div className="mb-3">
                              <div className="d-flex justify-content-between align-items-center mb-2">
                                <h6 className={styles.sqlSectionTitle}>
                                  <i className="bi bi-code me-2"></i>
                                  Unified SQL Query
                                </h6>
                                <button
                                  className={`btn btn-sm btn-outline-secondary ${styles.copyButton}`}
                                  onClick={() => navigator.clipboard.writeText(previewData.unified_sql)}
                                  title="Copy SQL to clipboard"
                                >
                                  <i className="bi bi-clipboard me-1"></i>
                                  Copy
                                </button>
                              </div>
                              
                              <div 
                                className={styles['sql-code-enhanced']}
                                dangerouslySetInnerHTML={{
                                  __html: highlightSQL(formatSQL(previewData.unified_sql))
                                }}
                              />
                              
                              <div className={`alert ${styles.previewInfoAlert} mt-3`}>
                                <i className={`bi bi-info-circle ${styles.previewInfoIcon}`}></i>
                                <strong>Preview Note:</strong> This is the optimized unified SQL query with CTEs for regular calculations. 
                                All non-CDI calculations are combined into a single, efficient query.
                              </div>
                            </div>
                          ) : (
                            <div className={styles.previewEmptyState}>
                              <i className={`bi bi-exclamation-circle ${styles.previewEmptyIcon}`}></i>
                              <p>No unified SQL available</p>
                              <small className="text-muted">This report may only contain CDI calculations.</small>
                            </div>
                          )}
                        </div>
                      )}

                      {/* CDI Calculations Tab */}
                      {hasCDICalculations && activeTab === 'cdi' && (
                        <div className="tab-pane fade show active">
                          <div className="mb-3">
                            <h6 className={styles.sqlSectionTitle}>
                              <i className="bi bi-database me-2"></i>
                              CDI Variable Calculations
                            </h6>
                            <p className="text-muted mb-3">
                              CDI calculations are executed separately against the <code>deal_cdi_var_rpt</code> table and merged with the main results.
                            </p>
                            
                            {previewData.cdi_sql_previews.map((cdiCalc: any, index: number) => (
                              <div key={index} className="mb-4">
                                <div className="d-flex justify-content-between align-items-center mb-2">
                                  <h6 className="mb-0">
                                    <i className="bi bi-code me-2"></i>
                                    {cdiCalc.alias || `CDI Calculation ${index + 1}`}
                                    <span className={`ms-2 ${styles.badge} ${styles.badgePrimary}`}>
                                      {cdiCalc.calculation_type?.replace('_', ' ') || 'CDI'}
                                    </span>
                                    {cdiCalc.variable_pattern && (
                                      <span className={`ms-1 ${styles.badge} ${styles.badgeSecondary}`}>
                                        {cdiCalc.variable_pattern}
                                      </span>
                                    )}
                                  </h6>
                                  <button
                                    className={`btn btn-sm btn-outline-secondary ${styles.copyButton}`}
                                    onClick={() => navigator.clipboard.writeText(cdiCalc.sql)}
                                    title="Copy CDI SQL to clipboard"
                                  >
                                    <i className="bi bi-clipboard me-1"></i>
                                    Copy
                                  </button>
                                </div>
                                
                                {cdiCalc.error ? (
                                  <div className="alert alert-danger">
                                    <i className="bi bi-exclamation-triangle me-2"></i>
                                    <strong>Error:</strong> {cdiCalc.error}
                                  </div>
                                ) : (
                                  <>
                                    <div 
                                      className={styles['sql-code-enhanced']}
                                      dangerouslySetInnerHTML={{
                                        __html: highlightSQL(formatSQL(cdiCalc.sql))
                                      }}
                                    />
                                    
                                    <div className="mt-2">
                                      <small className="text-muted">
                                        {cdiCalc.variable_names && (
                                          <>
                                            <strong>Variables:</strong> {cdiCalc.variable_names.join(', ')} | {' '}
                                          </>
                                        )}
                                        <strong>Estimated rows:</strong> {cdiCalc.estimated_rows || 'Unknown'}
                                        {cdiCalc.tranche_mappings && Object.keys(cdiCalc.tranche_mappings).length > 0 && (
                                          <>
                                            {' '} | <strong>Tranche mappings:</strong> {Object.keys(cdiCalc.tranche_mappings).length} suffix mappings
                                          </>
                                        )}
                                      </small>
                                    </div>
                                  </>
                                )}
                              </div>
                            ))}
                            
                            <div className={`alert ${styles.previewInfoAlert}`}>
                              <i className={`bi bi-info-circle ${styles.previewInfoIcon}`}></i>
                              <strong>CDI Execution:</strong> These queries are executed separately from the main unified query and their results 
                              are merged based on deal number and tranche ID. Each CDI calculation maps variable patterns to specific tranche suffixes.
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Fallback for legacy format */}
                {!hasUnifiedSQL && !hasCDICalculations && previewData.sql_previews && Object.keys(previewData.sql_previews).length > 0 && (
                  <div className="mb-3">
                    <h6 className={styles.sqlSectionTitle}>Generated SQL Queries (Legacy Format)</h6>
                    <p className="text-muted mb-3">
                      Each calculation generates its own optimized SQL query. These are executed individually and then merged.
                    </p>
                    
                    {Object.entries(previewData.sql_previews).map(([alias, sqlData]: [string, any]) => (
                      <div key={alias} className="mb-4">
                        <div className="d-flex justify-content-between align-items-center mb-2">
                          <h6 className="mb-0">
                            <i className="bi bi-code me-2"></i>
                            {alias.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                            <span className={`ms-2 ${styles.badge} ${styles.badgePrimary}`}>
                              {sqlData.calculation_type}
                            </span>
                            {sqlData.group_level && (
                              <span className={`ms-1 ${styles.badge} ${styles.badgeSecondary}`}>
                                {sqlData.group_level} level
                              </span>
                            )}
                          </h6>
                          <button
                            className={`btn btn-sm btn-outline-secondary ${styles.copyButton}`}
                            onClick={() => navigator.clipboard.writeText(sqlData.sql)}
                            title="Copy SQL to clipboard"
                          >
                            <i className="bi bi-clipboard me-1"></i>
                            Copy
                          </button>
                        </div>
                        
                        <div 
                          className={styles['sql-code-enhanced']}
                          dangerouslySetInnerHTML={{
                            __html: highlightSQL(formatSQL(sqlData.sql))
                          }}
                        />
                        
                        <div className="mt-2">
                          <small className="text-muted">
                            <strong>Returns columns:</strong> {sqlData.columns?.join(', ') || 'Unknown'}
                          </small>
                        </div>
                      </div>
                    ))}
                    
                    <div className={`alert ${styles.previewInfoAlert}`}>
                      <i className={`bi bi-info-circle ${styles.previewInfoIcon}`}></i>
                      <strong>Preview Note:</strong> These are the individual SQL queries that will be executed and merged when the report runs. 
                      Each calculation is optimized separately for performance.
                    </div>
                  </div>
                )}

                {/* Empty state if no SQL at all */}
                {!hasUnifiedSQL && !hasCDICalculations && (!previewData.sql_previews || Object.keys(previewData.sql_previews).length === 0) && (
                  <div className={styles.previewEmptyState}>
                    <i className={`bi bi-exclamation-circle ${styles.previewEmptyIcon}`}></i>
                    <p>No SQL queries generated</p>
                    <small className="text-muted">This may indicate an error in the report configuration.</small>
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