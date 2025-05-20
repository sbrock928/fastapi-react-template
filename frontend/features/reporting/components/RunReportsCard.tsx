import React from 'react';
import CycleDropdown from '@/components/CycleDropdown';
import type { ReportConfigurationResponse } from '@/types';

interface RunReportsCardProps {
  activeReport: string;
  reportConfigurations: ReportConfigurationResponse;
  configLoading: boolean;
  loading: boolean;
  onReportChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  onRunReport: () => void;
}

const RunReportsCard: React.FC<RunReportsCardProps> = ({
  activeReport,
  reportConfigurations,
  configLoading,
  loading,
  onReportChange,
  onRunReport
}) => {
  return (
    <div className="card mb-4">
      <div className="card-header bg-primary text-white">
        <h5 className="card-title mb-0">Run Reports</h5>
      </div>
      <div className="card-body">
        <form id="reportForm" className="row g-3">
          <div className="col-md-6">
            <label htmlFor="reportSelect" className="form-label">Select Report</label>
            <select
              id="reportSelect"
              className="form-select"
              required
              value={activeReport}
              onChange={onReportChange}
              disabled={configLoading}
            >
              <option value="" disabled>Choose a report...</option>
              {Object.entries(reportConfigurations).map(([key, config]) => (
                <option key={key} value={key}>
                  {config.title}
                </option>
              ))}
            </select>
            {configLoading && <div className="text-muted mt-1">Loading report types...</div>}
          </div>

          <div className="col-md-6">
            <CycleDropdown />
          </div>
          
          <div className="col-12 mt-3 d-flex gap-2">
            <button
              type="button"
              id="runReportBtn"
              className="btn"
              style={{ backgroundColor: '#93186C', color: 'white' }}
              onClick={onRunReport}
              disabled={loading || !activeReport}
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
              id="scheduleReportBtn"
              className="btn btn-outline-secondary"
              disabled={true}
              title="Coming soon: Schedule reports to run automatically"
            >
              <i className="bi bi-calendar-event"></i> Schedule Report
              <span className="badge bg-info ms-2" style={{ fontSize: '0.7rem' }}>Coming Soon</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default RunReportsCard;
