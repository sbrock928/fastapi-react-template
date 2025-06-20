import { useRef, useEffect, useCallback } from 'react';
import useModal from '@/hooks/useModal';
import { formatJsonString } from '@/utils/formatters';
import type { Log } from '@/types';
import styles from '@/styles/components/LogDetailsModal.module.css';

interface LogDetailsModalProps {
  log: Log;
  show: boolean;
  onHide: () => void;
}

const LogDetailsModal = ({ log, show, onHide }: LogDetailsModalProps) => {
  const modalMounted = useRef(false);
  const { modalRef, closeModal } = useModal(show, onHide);
  
  // Mark when modal is mounted
  useEffect(() => {
    modalMounted.current = true;
    return () => {
      modalMounted.current = false;
    };
  }, []);
  
  // Handle modal container click to isolate its event bubble
  const handleModalClick = useCallback((e: React.MouseEvent) => {
    // Prevent event propagation from modal dialog clicks
    e.stopPropagation();
  }, []);
  
  // Handle manual close of the modal
  const handleClose = useCallback((e: React.MouseEvent) => {
    // Prevent default behavior
    e.preventDefault();
    // Stop event propagation
    e.stopPropagation();
    // Use our direct closeModal function to ensure the modal closes
    closeModal();
  }, [closeModal]);
  
  // Copy to clipboard function
  const copyToClipboard = useCallback((content: string, type: string) => {
    navigator.clipboard.writeText(content).then(() => {
      // You could add a toast notification here if available
      console.log(`${type} copied to clipboard`);
    }).catch(err => {
      console.error('Failed to copy to clipboard:', err);
    });
  }, []);
  
  if (!log) return null;

  return (
    <div 
      className={`modal fade ${styles.modal}`}
      tabIndex={-1}
      aria-labelledby="logDetailsModalLabel"
      aria-hidden="true"
      ref={modalRef}
      onClick={handleModalClick}
      data-bs-backdrop="static"
      data-bs-keyboard="false"
    >
      <div className={`modal-dialog modal-lg ${styles.modalDialog}`}>
        <div className={`modal-content ${styles.modalContent}`}>
          <div className={`modal-header ${styles.modalHeader}`}>
            <h5 className="modal-title" id="logDetailsModalLabel">
              Request Details - {log.method} {log.path}
            </h5>
            <button 
              type="button" 
              className={`btn-close ${styles.closeButton}`}
              onClick={handleClose}
              aria-label="Close"
            ></button>
          </div>
          <div className={`modal-body ${styles.modalBody}`}>
            <div className="row mb-3">
              <div className="col-md-6">
                <div className="mb-3">
                  <label className="form-label fw-bold">Timestamp:</label>
                  <div id="detailTimestamp">{new Date(log.timestamp).toLocaleString()}</div>
                </div>
                <div className="mb-3">
                  <label className="form-label fw-bold">Method:</label>
                  <div><span className="badge bg-primary" id="detailMethod">{log.method}</span></div>
                </div>
                <div className="mb-3">
                  <label className="form-label fw-bold">Path:</label>
                  <div id="detailPath">{log.path}</div>
                </div>
                <div className="mb-3">
                  <label className="form-label fw-bold">Application ID:</label>
                  <div id="detailAppId">{log.application_id || 'N/A'}</div>
                </div>
              </div>
              <div className="col-md-6">
                <div className="mb-3">
                  <label className="form-label fw-bold">Status Code:</label>
                  <div>
                    <span 
                      className={`badge ${
                        log.status_code >= 400 ? 'bg-danger' : 
                        log.status_code >= 300 ? 'bg-warning' : 
                        'bg-success'
                      }`}
                      id="detailStatus"
                    >
                      {log.status_code}
                    </span>
                  </div>
                </div>
                <div className="mb-3">
                  <label className="form-label fw-bold">Client IP:</label>
                  <div id="detailIp">
                    {log.client_ip || 'Unknown'}
                  </div>
                </div>
                <div className="mb-3">
                  <label className="form-label fw-bold">User:</label>
                  <div id="detailUser">
                    {log.username ? (
                      <span>
                        <i className="bi bi-person-circle me-1"></i>
                        {log.username}
                      </span>
                    ) : 'Not logged in'}
                  </div>
                </div>
                <div className="mb-3">
                  <label className="form-label fw-bold">Processing Time:</label>
                  <div id="detailTime">{log.processing_time ? `${log.processing_time.toFixed(2)} ms` : 'N/A'}</div>
                </div>
                <div className="mb-3">
                  <label className="form-label fw-bold">Server:</label>
                  <div id="detailServer">{log.hostname || 'Not available'}</div>
                </div>
              </div>
            </div>
            
            <ul className="nav nav-tabs" id="logDetailsTabs" role="tablist">
              <li className="nav-item" role="presentation">
                <button className="nav-link active" id="headers-tab" data-bs-toggle="tab" data-bs-target="#headers-tab-pane" type="button" role="tab">
                  Request Headers
                </button>
              </li>
              <li className="nav-item" role="presentation">
                <button className="nav-link" id="body-tab" data-bs-toggle="tab" data-bs-target="#body-tab-pane" type="button" role="tab">
                  Request Body
                </button>
              </li>
              <li className="nav-item" role="presentation">
                <button className="nav-link" id="response-tab" data-bs-toggle="tab" data-bs-target="#response-tab-pane" type="button" role="tab">
                  Response Body
                </button>
              </li>
            </ul>
            
            <div className={`tab-content ${styles.tabContent}`} id="requestTabsContent">
              <div className="tab-pane fade show active" id="headers-tab-pane" role="tabpanel" aria-labelledby="headers-tab" tabIndex={0}>
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <h6 className="mb-0 text-muted">Request Headers</h6>
                  <button
                    className="btn btn-sm btn-outline-secondary"
                    onClick={() => copyToClipboard(formatJsonString(log.request_headers), 'Request Headers')}
                    title="Copy request headers to clipboard"
                  >
                    <i className="bi bi-clipboard me-1"></i>
                    Copy
                  </button>
                </div>
                <pre className={styles.preBlock} id="detailHeaders">{formatJsonString(log.request_headers)}</pre>
              </div>
              <div className="tab-pane fade" id="body-tab-pane" role="tabpanel" aria-labelledby="body-tab" tabIndex={0}>
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <h6 className="mb-0 text-muted">Request Body</h6>
                  <button
                    className="btn btn-sm btn-outline-secondary"
                    onClick={() => copyToClipboard(formatJsonString(log.request_body), 'Request Body')}
                    title="Copy request body to clipboard"
                  >
                    <i className="bi bi-clipboard me-1"></i>
                    Copy
                  </button>
                </div>
                <pre className={styles.preBlock} id="detailBody">{formatJsonString(log.request_body)}</pre>
              </div>
              <div className="tab-pane fade" id="response-tab-pane" role="tabpanel" aria-labelledby="response-tab" tabIndex={0}>
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <h6 className="mb-0 text-muted">Response Body</h6>
                  <button
                    className="btn btn-sm btn-outline-secondary"
                    onClick={() => copyToClipboard(formatJsonString(log.response_body), 'Response Body')}
                    title="Copy response body to clipboard"
                  >
                    <i className="bi bi-clipboard me-1"></i>
                    Copy
                  </button>
                </div>
                <pre className={styles.preBlock} id="detailResponseBody">{formatJsonString(log.response_body)}</pre>
              </div>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={handleClose}>Close</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LogDetailsModal;
