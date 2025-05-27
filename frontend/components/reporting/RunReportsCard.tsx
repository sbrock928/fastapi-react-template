import React from 'react';
import { useReportContext } from '@/context/ReportContext';
import { useCycleContext } from '@/context/CycleContext';
import { ReportDropdown, CycleDropdown } from '@/components/reporting';

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
  const canRunReport = selectedSavedReport && selectedCycle && selectedCycle.value !== '';

  return (
    <div className="card mb-4">
      <div className="card-header bg-primary text-white">
        <h5 className="card-title mb-0">Run Reports</h5>
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
              className="btn"
              style={{ backgroundColor: '#28a745', color: 'white' }}
              onClick={onRunReport}
              disabled={loading || !canRunReport}
            >
              {loading ? (
                <>
                  <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                  <span className="ms-2">Running...</span>
                </>
              ) : (
                <>
                  <i className="bi bi-play-fill"></i> Run Report
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
        {!selectedSavedReport && (
          <div className="alert alert-warning mt-3">
            <i className="bi bi-exclamation-triangle me-2"></i>
            Please select a saved report to run.
          </div>
        )}
        
        {selectedSavedReport && (!selectedCycle || selectedCycle.value === '') && (
          <div className="alert alert-warning mt-3">
            <i className="bi bi-exclamation-triangle me-2"></i>
            Please select a cycle to run the report.
          </div>
        )}

        {selectedSavedReport && selectedCycle && selectedCycle.value !== '' && (
          <div className="alert alert-info mt-3">
            <i className="bi bi-info-circle me-2"></i>
            Ready to run: <strong>{savedReports.find(r => r.id.toString() === selectedSavedReport)?.name}</strong> for cycle <strong>{selectedCycle.label}</strong>
          </div>
        )}
      </div>
    </div>
  );
};

export default RunReportsCard;