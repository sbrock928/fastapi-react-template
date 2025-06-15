import React from 'react';

interface UsageModalProps {
  isOpen: boolean;
  selectedUsageData: any;
  usageLoading: boolean;
  onClose: () => void;
}

const UsageModal: React.FC<UsageModalProps> = ({
  isOpen,
  selectedUsageData,
  usageLoading,
  onClose
}) => {
  if (!isOpen) return null;

  return (
    <div className="modal show d-block" tabIndex={-1} style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-lg modal-dialog-scrollable">
        <div className="modal-content">
          <div className="modal-header bg-primary">
            <h5 className="modal-title text-white">
              <i className="bi bi-bar-chart me-2"></i>
              Calculation Usage Information
            </h5>
            <button
              type="button"
              className="btn-close btn-close-white"
              onClick={onClose}
            ></button>
          </div>
          
          <div className="modal-body">
            {usageLoading ? (
              <div className="text-center py-4">
                <div className="spinner-border text-primary" role="status">
                  <span className="visually-hidden">Loading...</span>
                </div>
                <p className="mt-2 mb-0">Loading usage information...</p>
              </div>
            ) : !selectedUsageData ? (
              <div className="text-center py-4">
                <p className="mt-2 mb-0">No usage information available.</p>
              </div>
            ) : (
              <div>
                <div className="mb-4">
                  <h6 className="text-muted mb-3">Usage Details for:</h6>
                  <h5 className="mb-3">"{selectedUsageData.calculation_name}"</h5>
                  
                  {/* Scope Filter Information */}
                  {selectedUsageData.scope_filter && selectedUsageData.scope_filter !== 'ALL' && (
                    <div className="alert alert-info mb-3">
                      <i className="bi bi-filter me-2"></i>
                      <strong>Scope Filter:</strong> Showing usage only for <strong>{selectedUsageData.scope_filter}</strong> reports.
                      {selectedUsageData.scope_specific_usage && (
                        <span> This is scope-specific usage data.</span>
                      )}
                    </div>
                  )}
                  
                  <div className="row mb-3">
                    <div className="col-md-6">
                      <div className="card">
                        <div className="card-body text-center">
                          <h6 className="card-title">Status</h6>
                          <span className={`badge fs-6 ${selectedUsageData.is_in_use ? 'bg-warning text-dark' : 'bg-primary'}`}>
                            {selectedUsageData.is_in_use ? 'In Use' : 'Available for Deletion'}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="col-md-6">
                      <div className="card">
                        <div className="card-body text-center">
                          <h6 className="card-title">Report Count</h6>
                          <span className="fs-4 fw-bold text-primary">{selectedUsageData.report_count}</span>
                          {selectedUsageData.scope_filter && selectedUsageData.scope_filter !== 'ALL' && (
                            <small className="d-block text-muted">in {selectedUsageData.scope_filter} reports</small>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {selectedUsageData.is_in_use && selectedUsageData.reports.length > 0 && (
                    <div>
                      <h6 className="mb-3">Used in the following report templates:</h6>
                      <div className="list-group">
                        {selectedUsageData.reports.map((report: any) => (
                          <div key={report.report_id} className="list-group-item">
                            <div className="d-flex w-100 justify-content-between">
                              <div>
                                <h6 className="mb-1">{report.report_name}</h6>
                                {report.report_description && (
                                  <p className="mb-1 text-muted">{report.report_description}</p>
                                )}
                                <small className="text-muted">
                                  Scope: {report.scope} | Created by: {report.created_by}
                                  {report.display_name && ` | Display Name: ${report.display_name}`}
                                </small>
                              </div>
                              <div className="text-end">
                                <span className="badge bg-secondary">ID: {report.report_id}</span>
                                {report.created_date && (
                                  <small className="d-block text-muted mt-1">
                                    {new Date(report.created_date).toLocaleDateString()}
                                  </small>
                                )}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                      
                      <div className="alert alert-warning mt-3">
                        <i className="bi bi-exclamation-triangle me-2"></i>
                        <strong>Note:</strong> To delete this calculation, you must first remove it from all the report templates listed above.
                      </div>
                    </div>
                  )}
                  
                  {!selectedUsageData.is_in_use && (
                    <div className="alert alert-success">
                      <i className="bi bi-check-circle me-2"></i>
                      <strong>Good news!</strong> This calculation is not currently being used in any report templates and can be safely deleted if needed.
                    </div>
                  )}
                </div>
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

export default UsageModal;