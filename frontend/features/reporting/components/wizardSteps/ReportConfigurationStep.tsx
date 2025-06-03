import React from 'react';
import type { ReportConfig } from '@/types/reporting';

interface ReportConfigurationStepProps {
  reportName: string;
  reportDescription: string;
  reportScope: 'DEAL' | 'TRANCHE' | '';
  onReportNameChange: (name: string) => void;
  onReportDescriptionChange: (description: string) => void;
  onReportScopeChange: (scope: 'DEAL' | 'TRANCHE' | '') => void;
  editingReport?: ReportConfig | null;
  isEditMode: boolean;
  // Optional validation props
  hasFieldError?: (fieldName: string) => boolean;
  getFieldErrorMessage?: (fieldName: string) => string | null;
}

const ReportConfigurationStep: React.FC<ReportConfigurationStepProps> = ({
  reportName,
  reportDescription,
  reportScope,
  onReportNameChange,
  onReportDescriptionChange,
  onReportScopeChange,
  editingReport,
  isEditMode,
  hasFieldError = () => false,
  getFieldErrorMessage = () => null
}) => {
  return (
    <div className="row g-3">
      <div className="col-12">
        <h5 className="mb-3">Step 1: Report Configuration</h5>
        {isEditMode && editingReport && (
          <div className="alert alert-info">
            <i className="bi bi-pencil me-2"></i>
            You are editing: <strong>{editingReport.name}</strong>
          </div>
        )}
      </div>
      
      <div className="col-md-6">
        <label htmlFor="reportName" className="form-label">Report Name</label>
        <input
          type="text"
          id="reportName"
          className={`form-control ${hasFieldError('reportName') ? 'is-invalid' : ''}`}
          value={reportName}
          onChange={(e) => onReportNameChange(e.target.value)}
          placeholder="Enter report name"
        />
        {hasFieldError('reportName') && (
          <div className="invalid-feedback">
            {getFieldErrorMessage('reportName')}
          </div>
        )}
      </div>
      
      <div className="col-md-6">
        <label htmlFor="reportScope" className="form-label">Report Scope</label>
        <select
          id="reportScope"
          className={`form-select ${hasFieldError('reportScope') ? 'is-invalid' : ''}`}
          value={reportScope}
          onChange={(e) => onReportScopeChange(e.target.value as 'DEAL' | 'TRANCHE' | '')}
        >
          <option value="">Select scope...</option>
          <option value="DEAL">Deal Level (One row per deal)</option>
          <option value="TRANCHE">Tranche Level (Multiple rows per deal)</option>
        </select>
        {hasFieldError('reportScope') && (
          <div className="invalid-feedback">
            {getFieldErrorMessage('reportScope')}
          </div>
        )}
      </div>
      
      <div className="col-12">
        <label htmlFor="reportDescription" className="form-label">Description (Optional)</label>
        <textarea
          id="reportDescription"
          className="form-control"
          rows={3}
          value={reportDescription}
          onChange={(e) => onReportDescriptionChange(e.target.value)}
          placeholder="Describe the purpose and use of this report..."
        />
        <div className="form-text">
          Provide a clear description of what this report contains and when it should be used.
        </div>
      </div>
      
      <div className="col-12">
        <div className="alert alert-info">
          <strong>Deal Level:</strong> Returns aggregated data with one row per deal.<br/>
          <strong>Tranche Level:</strong> Returns detailed data with one row per selected tranche.<br/>
          <small className="text-muted">
            <em>Note: Cycle selection happens when running the report, not during configuration.</em>
          </small>
        </div>
      </div>
    </div>
  );
};

export default ReportConfigurationStep;