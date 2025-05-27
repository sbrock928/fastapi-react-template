import { useRef, useEffect, useCallback } from 'react';
import useModal from '@/hooks/useModal';
import { formatJsonString } from '@/utils/formatters';
import type { Log } from '@/types';

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
  
  return (
    <div 
      className="modal fade" 
      id="logDetailsModal" 
      tabIndex={-1} 
      ref={modalRef}
      data-bs-backdrop="static"
      data-bs-keyboard="false"
      onClick={handleModalClick}
    >
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header text-white" style={{ backgroundColor: '#28a745' }}>
            <h5 className="modal-title">Log Details</h5>
            <button type="button" className="btn-close btn-close-white" onClick={handleClose} aria-label="Close"></button>
          </div>
          <div className="modal-body">
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
            
            <div className="tab-content p-3 border border-top-0 rounded-bottom" id="logDetailsTabContent">
              <div className="tab-pane fade show active" id="headers-tab-pane" role="tabpanel" aria-labelledby="headers-tab" tabIndex={0}>
                <pre className="bg-light p-3 rounded" id="detailHeaders">{formatJsonString(log.request_headers)}</pre>
              </div>
              <div className="tab-pane fade" id="body-tab-pane" role="tabpanel" aria-labelledby="body-tab" tabIndex={0}>
                <pre className="bg-light p-3 rounded" id="detailBody">{formatJsonString(log.request_body)}</pre>
              </div>
              <div className="tab-pane fade" id="response-tab-pane" role="tabpanel" aria-labelledby="response-tab" tabIndex={0}>
                <pre className="bg-light p-3 rounded" id="detailResponseBody">{formatJsonString(log.response_body)}</pre>
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
