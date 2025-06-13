import React, { useState } from 'react';
import { reportingApi } from '@/services/api';
import { useToast } from '@/context/ToastContext';
import { useReportContext } from '@/context/ReportContext';
import ExecutionLogsModal from './ExecutionLogsModal';
import type { ReportConfig } from '@/types';

interface SavedReportsManagerProps {
  selectedReportId: string;
  onReportSelect: (reportId: string) => void;
  onCreateNew: () => void;
  onReportsUpdated: () => void;
  onEditReport: (report: ReportConfig) => void;
}

const SavedReportsManager: React.FC<SavedReportsManagerProps> = ({
  selectedReportId,
  onReportSelect,
  onCreateNew,
  onReportsUpdated,
  onEditReport
}) => {
  const { showToast } = useToast();
  const { savedReports, loading, refreshReports } = useReportContext();
  const [deleteLoading, setDeleteLoading] = useState<string | null>(null);
  const [editLoading, setEditLoading] = useState<string | null>(null);
  const [showExecutionLogs, setShowExecutionLogs] = useState(false);

  // Handle edit report (fetch full details and trigger edit mode)
  const handleEditReport = async (reportId: number) => {
    setEditLoading(reportId.toString());
    try {
      const response = await reportingApi.getReport(reportId);
      const reportConfig = response.data;
      
      // Call the parent's edit handler with the full report configuration
      onEditReport(reportConfig);
      
    } catch (error: any) {
      console.error('Error fetching report for editing:', error);
      
      // Extract detailed error messages from the API response
      let errorMessage = 'Error loading report for editing';
      
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        
        if (detail.errors && Array.isArray(detail.errors)) {
          const errorMessages = detail.errors.join(', ');
          errorMessage = `${errorMessage}: ${errorMessages}`;
        } else if (typeof detail === 'string') {
          errorMessage = `${errorMessage}: ${detail}`;
        }
      } else if (error.response?.data?.message) {
        errorMessage = `${errorMessage}: ${error.response.data.message}`;
      } else if (error.message) {
        errorMessage = `${errorMessage}: ${error.message}`;
      }
      
      showToast(errorMessage, 'error');
    } finally {
      setEditLoading(null);
    }
  };

  // Handle report deletion
  const handleDeleteReport = async (reportId: number, reportName: string) => {
    if (!window.confirm(`Are you sure you want to delete "${reportName}"? This action cannot be undone.`)) {
      return;
    }

    setDeleteLoading(reportId.toString());
    try {
      await reportingApi.deleteReport(reportId);
      showToast(`Successfully deleted report "${reportName}"`, 'success');
      
      // Refresh reports using context with force flag
      await refreshReports(true);
      
      // Clear selection if the deleted report was selected
      if (selectedReportId === reportId.toString()) {
        onReportSelect('');
      }
      
      // Notify parent that reports were updated
      onReportsUpdated();
      
    } catch (error: any) {
      console.error('Error deleting report:', error);
      
      // Extract detailed error messages from the API response
      let errorMessage = `Error deleting report "${reportName}"`;
      
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        
        if (detail.errors && Array.isArray(detail.errors)) {
          // Handle the backend's errors array format
          const errorMessages = detail.errors.join(', ');
          errorMessage = `${errorMessage}: ${errorMessages}`;
        } else if (typeof detail === 'string') {
          // Handle simple string error messages
          errorMessage = `${errorMessage}: ${detail}`;
        } else if (typeof detail === 'object' && detail.message) {
          // Handle other object formats with a message property
          errorMessage = `${errorMessage}: ${detail.message}`;
        }
      } else if (error.response?.data?.message) {
        // Handle other API error formats
        errorMessage = `${errorMessage}: ${error.response.data.message}`;
      } else if (error.message) {
        // Handle network or other errors
        errorMessage = `${errorMessage}: ${error.message}`;
      }
      
      showToast(errorMessage, 'error');
    } finally {
      setDeleteLoading(null);
    }
  };

  // Format date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="text-center py-4">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
        <p className="mt-2">Loading saved reports...</p>
      </div>
    );
  }

  return (
    <div className="row g-3">
      <div className="col-md-8">
        <label htmlFor="existingReportSelect" className="form-label">Saved Report Configurations</label>
        <select
          id="existingReportSelect"
          className="form-select"
          value={selectedReportId}
          onChange={(e) => onReportSelect(e.target.value)}
        >
          <option value="">Select a saved report...</option>
          {savedReports.map(report => (
            <option key={report.id} value={report.id.toString()}>
              {report.name} ({report.scope} Level • {report.deal_count} deals • {report.calculation_count} calculations
              {report.scope === 'TRANCHE' && ` • ${report.tranche_count} tranches`}
              {report.last_executed && ` • Last run: ${formatDate(report.last_executed)}`})
            </option>
          ))}
        </select>
        
        {/* Show additional info for selected report */}
        {selectedReportId && (
          <div className="mt-2">
            {(() => {
              const selectedReport = savedReports.find(r => r.id.toString() === selectedReportId);
              if (!selectedReport) return null;
              
              return (
                <div className="card border-primary">
                  <div className="card-body p-3">
                    <div className="row text-sm">
                      <div className="col-sm-6">
                        <strong>Report Type:</strong> {selectedReport.scope} Level
                      </div>
                      <div className="col-sm-6">
                        <strong>Created:</strong> {formatDate(selectedReport.created_date)}
                      </div>
                      <div className="col-sm-6">
                        <strong>Deals:</strong> {selectedReport.deal_count}
                      </div>
                      <div className="col-sm-6">
                        <strong>Calculations:</strong> {selectedReport.calculation_count}
                      </div>
                      <div className="col-sm-6">
                        <strong>Total Executions:</strong> {selectedReport.total_executions}
                      </div>
                      {selectedReport.scope === 'TRANCHE' && (
                        <div className="col-sm-6">
                          <strong>Tranches:</strong> {selectedReport.tranche_count}
                        </div>
                      )}
                      {selectedReport.last_executed && (
                        <div className="col-sm-6">
                          <strong>Last Executed:</strong> {formatDate(selectedReport.last_executed)}
                          {selectedReport.last_execution_success !== undefined && (
                            <span className={`ms-2 badge ${selectedReport.last_execution_success ? 'bg-success' : 'bg-danger'}`}>
                              {selectedReport.last_execution_success ? 'Success' : 'Failed'}
                            </span>
                          )}
                        </div>
                      )}
                      {selectedReport.description && (
                        <div className="col-12 mt-2">
                          <strong>Description:</strong>
                          <div className="mt-1 p-2 bg-light rounded small">
                            {selectedReport.description}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })()}
          </div>
        )}
        
        {/* Empty state */}
        {savedReports.length === 0 && (
          <div className="alert alert-info mt-3">
            <i className="bi bi-info-circle me-2"></i>
            No saved reports found. Create your first report configuration to get started.
          </div>
        )}      
      </div>      
      <div className="col-md-4">
        <div className="d-flex flex-column gap-2" style={{ paddingTop: '2rem' }}>
          <button
            type="button"
            className="btn btn-primary w-100"
            onClick={onCreateNew}
          >
            <i className="bi bi-plus-lg"></i> Create New Report
          </button>
          
          <button
            type="button"
            className="btn btn-outline-primary w-100"
            disabled={!selectedReportId || editLoading !== null}
            onClick={() => selectedReportId && handleEditReport(parseInt(selectedReportId))}
          >
            {editLoading === selectedReportId ? (
              <>
                <span className="spinner-border spinner-border-sm me-1"></span>
                Loading...
              </>
            ) : (
              <>
                <i className="bi bi-pencil"></i> Edit
              </>
            )}
          </button>
          
          <button
            type="button"
            className="btn btn-outline-danger w-100"
            disabled={!selectedReportId || deleteLoading !== null}
            onClick={() => {
              if (selectedReportId) {
                const report = savedReports.find(r => r.id.toString() === selectedReportId);
                if (report) {
                  handleDeleteReport(report.id, report.name);
                }
              }
            }}
          >
            {deleteLoading === selectedReportId ? (
              <>
                <span className="spinner-border spinner-border-sm me-1"></span>
                Deleting...
              </>
            ) : (
              <>
                <i className="bi bi-trash"></i> Delete
              </>
            )}
          </button>
          
          <button
            type="button"
            className="btn btn-outline-info w-100"
            disabled={!selectedReportId}
            onClick={() => setShowExecutionLogs(true)}
          >
            <i className="bi bi-clock-history"></i> View Execution Logs
          </button>
        </div>
      </div>
      
      {/* Execution Logs Modal */}
      {showExecutionLogs && selectedReportId && (
        <ExecutionLogsModal
          reportId={parseInt(selectedReportId)}
          reportName={savedReports.find(r => r.id.toString() === selectedReportId)?.name || 'Unknown Report'}
          isOpen={showExecutionLogs}
          onClose={() => setShowExecutionLogs(false)}
        />
      )}
    </div>
  );
};

export default SavedReportsManager;