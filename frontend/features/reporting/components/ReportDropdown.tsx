import React from 'react';
import { useReportContext } from '@/context/ReportContext';
import type { ReportSummary } from '@/types';

interface ReportDropdownProps {
  selectedReportId: string;
  onReportSelect: (reportId: string) => void;
}

const ReportDropdown: React.FC<ReportDropdownProps> = ({ 
  selectedReportId, 
  onReportSelect 
}) => {
  const { savedReports, loading, error } = useReportContext();

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onReportSelect(e.target.value);
  };

  if (error) {
    return (
      <div className="form-group">
        <label htmlFor="savedReportSelect" className="form-label">Saved Report Configurations</label>
        <div className="text-danger">Error loading saved reports</div>
      </div>
    );
  }

  return (
    <div className="form-group">
      <label htmlFor="savedReportSelect" className="form-label">Saved Report Configurations</label>
      <select
        id="savedReportSelect"
        name="saved_report"
        className="form-select"
        value={selectedReportId}
        onChange={handleChange}
        disabled={loading}
      >
        {loading ? (
          <option value="">Loading saved reports...</option>
        ) : (
          <>
            <option value="">Choose a saved report...</option>
            {savedReports.map((report: ReportSummary) => (
              <option key={report.id} value={report.id.toString()}>
                {report.name} ({report.scope} Level)
              </option>
            ))}
          </>
        )}
      </select>
    </div>
  );
};

export default ReportDropdown;