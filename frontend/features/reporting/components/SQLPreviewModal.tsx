import React from 'react';
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

  const handleClose = () => {
    closeModal();
  };

  const handleCopySQL = () => {
    if (previewData?.sql_query) {
      navigator.clipboard.writeText(previewData.sql_query);
      // You could integrate with the toast context here if needed
    }
  };

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
                {/* Template Details */}
                <div className={styles.detailsGrid}>
                  <div className={styles.detailsCard}>
                    <h6 className={styles.detailsCardTitle}>Report Details</h6>
                    <div className={styles.detailsCardContent}>
                      <div className="mb-2">
                        <strong>Name:</strong> {previewData.template_name || reportName}
                      </div>
                      <div>
                        <strong>Aggregation Level:</strong>{' '}
                        <span className={`${styles.badge} ${styles.badgeSecondary}`}>
                          {previewData.aggregation_level}
                        </span>
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
                        <strong>Deals:</strong> {previewData.parameters?.deal_numbers?.length || 0} selected
                      </div>
                      <div>
                        <strong>Tranches:</strong> {previewData.parameters?.tranche_ids?.length || 0} selected
                      </div>
                    </div>
                  </div>
                </div>

                {/* SQL Query */}
                <div className="mb-3">
                  <div className={styles.sqlSectionHeader}>
                    <h6 className={styles.sqlSectionTitle}>Generated SQL Query</h6>
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
                      __html: highlightSQL(formatSQL(previewData.sql_query))
                    }}
                  />
                  <div className={styles.sqlNote}>
                    This is the exact SQL that will execute when the report runs.
                  </div>
                </div>

                {/* Additional Info */}
                {previewData.parameters?.deal_numbers && (
                  <div className={`alert ${styles.previewInfoAlert}`}>
                    <i className={`bi bi-info-circle ${styles.previewInfoIcon}`}></i>
                    <strong>Preview Note:</strong> This preview shows the SQL structure with the actual report configuration. 
                    The execution will use the specific deals, tranches, and cycle selected for this report.
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