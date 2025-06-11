import React from 'react';
import type { PreviewData } from '@/types/calculations';
import { formatSQL, highlightSQL } from '@/utils/sqlFormatter';
import styles from '@/styles/components/SQLPreview.module.css';

interface SqlPreviewModalProps {
  isOpen: boolean;
  previewData: PreviewData | null;
  previewLoading: boolean;
  onClose: () => void;
}

const SqlPreviewModal: React.FC<SqlPreviewModalProps> = ({
  isOpen,
  previewData,
  previewLoading,
  onClose
}) => {
  if (!isOpen) return null;

  const handleCopySQL = () => {
    const sql = previewData?.sql || previewData?.generated_sql;
    if (sql) {
      navigator.clipboard.writeText(sql);
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