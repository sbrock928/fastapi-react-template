import React, { useState } from 'react';
import { useReportContext } from '@/context/ReportContext';
import { useCycleContext } from '@/context/CycleContext';
import { useToast } from '@/context/ToastContext';
import { reportingApi } from '@/services/api';
import { ReportDropdown, CycleDropdown } from './';
import SQLPreviewModal from './SQLPreviewModal';
import styles from '@/styles/components/RunReportsCard.module.css';

interface RunReportsCardProps {
  selectedSavedReport: string;
  loading: boolean;
  onSavedReportSelect: (reportId: string) => void;
  onRunReport: () => void;
}

const RunReportsCard: React.FC<RunReportsCardProps> = ({
  selectedSavedReport,
  loading,
  onSavedReportSelect,
  onRunReport
}) => {
  const { savedReports } = useReportContext();
  const { selectedCycle } = useCycleContext();
  const { showToast } = useToast();

  // Preview SQL state
  const [showPreviewModal, setShowPreviewModal] = useState<boolean>(false);
  const [previewData, setPreviewData] = useState<any>(null);
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);

  // Check if both report and cycle are selected
  const canRunReport = selectedSavedReport && selectedCycle && selectedCycle.value !== 0;
  const canPreviewSQL = selectedSavedReport && selectedCycle && selectedCycle.value !== 0;

  // Handle SQL Preview
  const handlePreviewSQL = async () => {
    if (!selectedSavedReport || !selectedCycle?.value) {
      showToast('Please select both a report and cycle to preview SQL', 'warning');
      return;
    }

    setPreviewLoading(true);
    setPreviewData(null);
    setShowPreviewModal(true);

    try {
      const response = await reportingApi.previewReportSQL(
        parseInt(selectedSavedReport), 
        selectedCycle.value as number
      );
      setPreviewData(response.data);
    } catch (error: any) {
      console.error('Error previewing SQL:', error);
      
      // Extract detailed error messages from the API response
      let errorMessage = 'Error generating SQL preview';
      
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        
        if (detail.errors && Array.isArray(detail.errors)) {
          const errorMessages = detail.errors.join(', ');
          errorMessage = `${errorMessage}: ${errorMessages}`;
        } else if (typeof detail === 'string') {
          errorMessage = `${errorMessage}: ${detail}`;
        } else if (typeof detail === 'object' && detail.message) {
          errorMessage = `${errorMessage}: ${detail.message}`;
        }
      } else if (error.response?.data?.message) {
        errorMessage = `${errorMessage}: ${error.response.data.message}`;
      } else if (error.message) {
        errorMessage = `${errorMessage}: ${error.message}`;
      }
      
      showToast(errorMessage, 'error');
      setShowPreviewModal(false);
    } finally {
      setPreviewLoading(false);
    }
  };

  // Get selected report name for modal
  const getSelectedReportName = (): string => {
    const selectedReport = savedReports.find(r => r.id.toString() === selectedSavedReport);
    return selectedReport?.name || 'Unknown Report';
  };

  return (
    <>
      <div className={`card ${styles.runReportsCard}`}>
        <div className={`card-header text-white ${styles.cardHeader}`}>
          <h5 className="card-title mb-0">
            <i className="bi bi-play-circle me-2"></i>
            Run Report
          </h5>
        </div>
        <div className="card-body">
          <div className="row g-3">
            <div className="col-md-6">
              <ReportDropdown
                selectedReportId={selectedSavedReport}
                onReportSelect={onSavedReportSelect}
              />
            </div>

            <div className="col-md-6">
              <CycleDropdown />
            </div>
            
            <div className="col-12 mt-3 d-flex gap-2">
              <button
                type="button"
                className={`btn btn-primary ${styles.runButton}`}
                onClick={onRunReport}
                disabled={loading || !canRunReport}
              >
                {loading ? (
                  <>
                    <span className={`spinner-border spinner-border-sm ${styles.loadingSpinner}`} role="status" aria-hidden="true"></span>
                    <span className={styles.loadingText}>Running Report...</span>
                  </>
                ) : (
                  <>
                    <i className="bi bi-play-fill me-2"></i>
                    Run Report
                  </>
                )}
              </button>

              {/* Preview SQL Button */}
              <button
                type="button"
                className="btn btn-outline-primary"
                onClick={handlePreviewSQL}
                disabled={previewLoading || !canPreviewSQL}
                title="Preview the SQL that will be executed"
              >
                {previewLoading ? (
                  <>
                    <span className="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
                    Previewing...
                  </>
                ) : (
                  <>
                    <i className="bi bi-code-square me-2"></i>
                    Preview SQL
                  </>
                )}
              </button>
              
              <button
                type="button"
                className="btn btn-outline-secondary"
                disabled={true}
                title="Coming soon: Schedule reports to run automatically"
              >
                <i className="bi bi-calendar-event"></i> Schedule Report
                <span className="badge bg-info ms-2" style={{ fontSize: '0.7rem' }}>Coming Soon</span>
              </button>
            </div>
          </div>

          {/* Validation messages */}
          <div className="mt-3">
            {!selectedSavedReport && (
              <div className={`alert alert-warning ${styles.warningAlert}`}>
                <i className={`bi bi-exclamation-triangle ${styles.warningIcon}`}></i>
                Please select a saved report to run.
              </div>
            )}
            
            {selectedSavedReport && (!selectedCycle || selectedCycle.value === 0) && (
              <div className={`alert alert-warning ${styles.warningAlert}`}>
                <i className={`bi bi-exclamation-triangle ${styles.warningIcon}`}></i>
                Please select a cycle to run the report.
              </div>
            )}

            {selectedSavedReport && selectedCycle && selectedCycle.value !== 0 && (
              <div className={`alert alert-info ${styles.infoAlert}`}>
                <i className={`bi bi-info-circle ${styles.infoIcon}`}></i>
                Ready to run: <strong>{savedReports.find(r => r.id.toString() === selectedSavedReport)?.name}</strong> for cycle <strong>{selectedCycle.label}</strong>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* SQL Preview Modal */}
      <SQLPreviewModal
        show={showPreviewModal}
        onHide={() => setShowPreviewModal(false)}
        previewData={previewData}
        loading={previewLoading}
        reportName={getSelectedReportName()}
      />
    </>
  );
};

export default RunReportsCard;