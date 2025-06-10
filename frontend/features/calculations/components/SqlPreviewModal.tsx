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
    if (previewData?.generated_sql) {
      navigator.clipboard.writeText(previewData.generated_sql);
    }
  };

  return (
    <div className="modal show d-block" tabIndex={-1} style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-xl modal-dialog-scrollable">
        <div className={`modal-content ${styles.sqlPreviewModalContent}`}>
          <div className={`modal-header ${styles.sqlPreviewModalHeader}`}>
            <h5 className="modal-title">
              <i className="bi bi-code-square me-2"></i>
              SQL Preview
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
                        <strong>Name:</strong> {previewData.calculation_name}
                      </div>
                      <div className="mb-2">
                        <strong>Type:</strong>{' '}
                        <span className={`${styles.badge} ${styles.badgePrimary}`}>
                          {previewData.calculation_type}
                        </span>
                      </div>
                      <div>
                        <strong>Level:</strong>{' '}
                        <span className={`${styles.badge} ${styles.badgeSecondary}`}>
                          {previewData.aggregation_level}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  <div className={styles.detailsCard}>
                    <h6 className={styles.detailsCardTitle}>
                      Sample Parameters
                    </h6>
                    <div className={styles.detailsCardContent}>
                      <div className="mb-1">
                        <strong>Deals:</strong> {previewData.sample_parameters?.deal_tranche_mapping ? 
                          Object.keys(previewData.sample_parameters.deal_tranche_mapping).join(', ') : 'N/A'}
                      </div>
                      <div className="mb-1">
                        <strong>Tranches:</strong> {previewData.sample_parameters?.deal_tranche_mapping ? 
                          Object.values(previewData.sample_parameters.deal_tranche_mapping).flat().join(', ') : 'N/A'}
                      </div>
                      <div>
                        <strong>Cycle:</strong> {previewData.sample_parameters?.cycle || 'N/A'}
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* SQL Query */}
                <div className="mb-3">
                  <div className={styles.sqlSectionHeader}>
                    <h6 className={styles.sqlSectionTitle}>
                      Raw Execution SQL
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
                      __html: highlightSQL(formatSQL(previewData.generated_sql))
                    }}
                  />
                  <div className={styles.sqlNote}>
                    This is the exact same SQL that executes when this calculation runs in a report.
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