import React, { useState } from 'react';
import { reportsApi } from '@/services/api';
import { useToast } from '@/context/ToastContext';
import { useReportContext } from '@/context/ReportContext';
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

  // Handle edit report (fetch full details and trigger edit mode)
  const handleEditReport = async (reportId: number) => {
    setEditLoading(reportId.toString());
    try {
      const response = await reportsApi.getReport(reportId);
      const reportConfig = response.data;
      
      // Call the parent's edit handler with the full report configuration
      onEditReport(reportConfig);
      
    } catch (error) {
      console.error('Error fetching report for editing:', error);
      showToast('Error loading report for editing', 'error');
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
      await reportsApi.deleteReport(reportId);
      showToast(`Successfully deleted report "${reportName}"`, 'success');
      
      // Refresh reports using context
      await refreshReports();
      
      // Clear selection if the deleted report was selected
      if (selectedReportId === reportId.toString()) {
        onReportSelect('');
      }
      
      // Notify parent that reports were updated
      onReportsUpdated();
      
    } catch (error) {
      console.error('Error deleting report:', error);
      showToast(`Error deleting report "${reportName}"`, 'error');
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
              {report.name} ({report.scope} Level • {report.deal_count} deals
              {report.scope === 'TRANCHE' && ` • ${report.tranche_count} tranches`})
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
                      {selectedReport.scope === 'TRANCHE' && (
                        <div className="col-sm-6">
                          <strong>Tranches:</strong> {selectedReport.tranche_count}
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
      
      <div className="col-md-4 d-flex align-items-end gap-2">
        <button
          type="button"
          className="btn btn-success"
          onClick={onCreateNew}
        >
          <i className="bi bi-plus-lg"></i> Create New Report
        </button>
        
        <button
          type="button"
          className="btn btn-outline-primary"
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
          className="btn btn-outline-danger"
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
      </div>
    </div>
  );
};

export default SavedReportsManager;