import React from 'react';
import { useReportContext } from '@/context/ReportContext';
import { useCycleContext } from '@/context/CycleContext';
import { ReportDropdown, CycleDropdown } from './';
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

  // Check if both report and cycle are selected
  const canRunReport = selectedSavedReport && selectedCycle && selectedCycle.value !== 0;

  return (
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
  );
};

export default RunReportsCard;