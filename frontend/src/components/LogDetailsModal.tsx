import { useEffect, useRef } from 'react'

// Remove the global declaration since it's now in main.tsx

interface Log {
  id: number;
  timestamp: string;
  method: string;
  path: string;
  status_code: number;
  client_ip: string;
  processing_time: number;
  request_headers?: string;
  request_body?: string;
  response_body?: string;
  status_category?: string; // Add this property to match the interface in Logs.tsx
  username?: string;  // Changed from server_username
  hostname?: string;  // Added hostname field
}

interface LogDetailsModalProps {
  log: Log;
  show: boolean;
  onHide: () => void;
}

const LogDetailsModal = ({ log, show, onHide }: LogDetailsModalProps) => {
  const modalRef = useRef<HTMLDivElement>(null)
  const bootstrapModalRef = useRef<any>(null)
  
  useEffect(() => {
    // Bootstrap is loaded globally via script tag
    if (modalRef.current && window.bootstrap) {
      bootstrapModalRef.current = new window.bootstrap.Modal(modalRef.current)
      
      if (show) {
        bootstrapModalRef.current.show()
      } else {
        bootstrapModalRef.current.hide()
      }
      
      // Event listener for when modal is hidden
      modalRef.current.addEventListener('hidden.bs.modal', onHide)
    }
    
    return () => {
      if (bootstrapModalRef.current) {
        bootstrapModalRef.current.dispose()
      }
      if (modalRef.current) {
        modalRef.current.removeEventListener('hidden.bs.modal', onHide)
      }
    }
  }, [show, onHide])
  
  const formatJsonDisplay = (jsonString: string | undefined): string => {
    if (!jsonString) return ''
    
    try {
      const parsed = JSON.parse(jsonString)
      return JSON.stringify(parsed, null, 2)
    } catch {
      return jsonString
    }
  }
  
  return (
    <div className="modal fade" id="logDetailsModal" tabIndex={-1} ref={modalRef}>
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">Log Details</h5>
            <button type="button" className="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
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
                  <label className="form-label fw-bold">Client IP / User:</label>
                  <div id="detailIp">
                    {log.client_ip || 'Unknown'}
                    {log.username && (
                      <div className="small">
                        <i className="bi bi-person-circle me-1"></i>
                        {log.username}
                      </div>
                    )}
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
                <pre className="bg-light p-3 rounded" id="detailHeaders">{formatJsonDisplay(log.request_headers)}</pre>
              </div>
              <div className="tab-pane fade" id="body-tab-pane" role="tabpanel" aria-labelledby="body-tab" tabIndex={0}>
                <pre className="bg-light p-3 rounded" id="detailBody">{formatJsonDisplay(log.request_body)}</pre>
              </div>
              <div className="tab-pane fade" id="response-tab-pane" role="tabpanel" aria-labelledby="response-tab" tabIndex={0}>
                <pre className="bg-light p-3 rounded" id="detailResponseBody">{formatJsonDisplay(log.response_body)}</pre>
              </div>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" data-bs-dismiss="modal">Close</button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LogDetailsModal
