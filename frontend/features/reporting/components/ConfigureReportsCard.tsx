import type { ReportConfigurationResponse } from '@/types';

interface ConfigureReportsCardProps {
  reportConfigurations: ReportConfigurationResponse;
  configLoading: boolean;
  selectedReportToEdit: string;
  configureMode: 'create' | 'edit' | null;
  reportName: string;
  reportAggregationLevel: 'deal' | 'asset' | '';
  selectedAttributes: string[];
  availableAttributes: { name: string; label: string; aggregationLevel: 'deal' | 'asset' | 'both' }[];
  
  // Handlers
  onReportEditChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  onCreateNewReport: () => void;
  onReportNameChange: (value: string) => void;
  onAggregationLevelChange: (value: 'deal' | 'asset' | '') => void;
  onAttributeToggle: (attributeName: string) => void;
  onSaveReportConfig: () => void;
  onCancelConfig: () => void;
  onDeleteReport: (reportId: string) => void;
}

const ConfigureReportsCard: React.FC<ConfigureReportsCardProps> = ({
  reportConfigurations,
  configLoading,
  selectedReportToEdit,
  configureMode,
  reportName,
  reportAggregationLevel,
  selectedAttributes,
  availableAttributes,
  onReportEditChange,
  onCreateNewReport,
  onReportNameChange,
  onAggregationLevelChange,
  onAttributeToggle,
  onSaveReportConfig,
  onCancelConfig,
  onDeleteReport
}) => {
  return (
    <div className="card mb-4">
      <div className="card-header bg-success text-white d-flex justify-content-between align-items-center">
        <h5 className="card-title mb-0">Configure Reports</h5>
        {configureMode && (
          <button 
            type="button"
            className="btn btn-outline-light btn-sm"
            onClick={onCancelConfig}
          >
            <i className="bi bi-x-lg"></i> Cancel
          </button>
        )}
      </div>
      <div className="card-body">
        {configureMode ? (
          <form id="reportConfigForm" className="row g-3">
            <div className="col-md-6">
              <label htmlFor="reportNameInput" className="form-label">Report Name</label>
              <input 
                type="text" 
                id="reportNameInput" 
                className="form-control"
                value={reportName}
                onChange={(e) => onReportNameChange(e.target.value)}
                placeholder="Enter report name"
                required
              />
            </div>
            <div className="col-md-6">
              <label htmlFor="aggregationLevelSelect" className="form-label">Aggregation Level</label>
              <select
                id="aggregationLevelSelect"
                className="form-select"
                value={reportAggregationLevel}
                onChange={(e) => onAggregationLevelChange(e.target.value as 'deal' | 'asset')}
                required
              >
                <option value="" disabled>Select level...</option>
                <option value="deal">Deal Level</option>
                <option value="asset">Asset Level</option>
              </select>
            </div>
            <div className="col-12">
              <label className="form-label">Select Attributes</label>
              <div className="row">
                {availableAttributes
                  .filter(attr => 
                    reportAggregationLevel === '' || 
                    attr.aggregationLevel === 'both' || 
                    attr.aggregationLevel === reportAggregationLevel
                  )
                  .map(attr => (
                    <div key={attr.name} className="col-md-4 mb-2">
                      <div className="form-check">
                        <input
                          type="checkbox"
                          id={`attribute-${attr.name}`}
                          className="form-check-input"
                          checked={selectedAttributes.includes(attr.name)}
                          onChange={() => onAttributeToggle(attr.name)}
                        />
                        <label className="form-check-label" htmlFor={`attribute-${attr.name}`}>
                          {attr.label}
                        </label>
                      </div>
                    </div>
                  ))
                }
              </div>
            </div>
            <div className="col-12 mt-3">
              <button
                type="button"
                className="btn btn-success"
                onClick={onSaveReportConfig}
              >
                <i className="bi bi-save"></i> Save Report Configuration
              </button>
            </div>
          </form>
        ) : (
          <div className="row g-3">
            <div className="col-md-6">
              <label htmlFor="existingReportSelect" className="form-label">Existing Report Configurations</label>
              <select
                id="existingReportSelect"
                className="form-select"
                value={selectedReportToEdit}
                onChange={onReportEditChange}
                disabled={configLoading}
              >
                <option value="">Select a report to edit...</option>
                {Object.entries(reportConfigurations).map(([key, config]) => (
                  <option key={key} value={key}>
                    {config.title}
                  </option>
                ))}
              </select>
            </div>
            <div className="col-md-6 d-flex align-items-end">
              <button
                type="button"
                className="btn btn-success me-2"
                onClick={onCreateNewReport}
              >
                <i className="bi bi-plus-lg"></i> Create New Report
              </button>
              <button
                type="button"
                className="btn btn-outline-danger"
                disabled={!selectedReportToEdit}
                onClick={() => {
                  if (selectedReportToEdit && window.confirm('Are you sure you want to delete this report configuration?')) {
                    onDeleteReport(selectedReportToEdit);
                  }
                }}
              >
                <i className="bi bi-trash"></i> Delete
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ConfigureReportsCard;
