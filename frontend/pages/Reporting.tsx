import { useState, useEffect } from 'react';
import { reportsApi } from '@/services/api';
import { CycleProvider, useCycleContext } from '@/context/CycleContext';
import ReportingTable from '@/components/ReportingTable';
import CycleDropdown from '@/components/CycleDropdown';
import type { ReportRow, DynamicReportConfig, ReportConfigurationResponse } from '@/types';

const ReportingContent = () => {
  const { selectedCycle } = useCycleContext();

  // Run reports states
  const [activeReport, setActiveReport] = useState<string>('');
  const [reportData, setReportData] = useState<ReportRow[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [showResults, setShowResults] = useState<boolean>(false);
  const [isSkeletonMode, setIsSkeletonMode] = useState<boolean>(false);
  const [reportConfigurations, setReportConfigurations] = useState<ReportConfigurationResponse>({});
  const [configLoading, setConfigLoading] = useState<boolean>(true);
  // Configure reports states
  const [selectedReportToEdit, setSelectedReportToEdit] = useState<string>('');
  const [configureMode, setConfigureMode] = useState<'create' | 'edit' | null>(null);
  const [reportAggregationLevel, setReportAggregationLevel] = useState<'deal' | 'asset' | ''>('');  const [reportName, setReportName] = useState<string>('');
  const [selectedAttributes, setSelectedAttributes] = useState<string[]>([]);
  const [availableAttributes, _setAvailableAttributes] = useState<
    { name: string; label: string; aggregationLevel: 'deal' | 'asset' | 'both' }[]
  >([
    { name: 'deal_name', label: 'Deal Name', aggregationLevel: 'deal' },
    { name: 'deal_type', label: 'Deal Type', aggregationLevel: 'deal' },
    { name: 'deal_value', label: 'Deal Value', aggregationLevel: 'deal' },
    { name: 'deal_status', label: 'Deal Status', aggregationLevel: 'deal' },
    { name: 'deal_date', label: 'Deal Date', aggregationLevel: 'deal' },
    { name: 'asset_name', label: 'Asset Name', aggregationLevel: 'asset' },
    { name: 'asset_type', label: 'Asset Type', aggregationLevel: 'asset' },
    { name: 'asset_value', label: 'Asset Value', aggregationLevel: 'asset' },
    { name: 'asset_acquisition_date', label: 'Acquisition Date', aggregationLevel: 'asset' },
    { name: 'id', label: 'ID', aggregationLevel: 'both' },
    { name: 'created_date', label: 'Created Date', aggregationLevel: 'both' },
    { name: 'modified_date', label: 'Modified Date', aggregationLevel: 'both' },
  ]);

  const generateSkeletonData = (config: DynamicReportConfig, rowCount = 5): ReportRow[] => {
    const skeletonRows: ReportRow[] = [];

    for (let i = 0; i < rowCount; i++) {
      const row: ReportRow = {};
      config.columns.forEach(column => {
        switch (column.type) {
          case 'number':
          case 'percentage':
            row[column.field] = 0;
            break;
          case 'date':
            row[column.field] = new Date().toISOString();
            break;
          default:
            row[column.field] = '';
        }
      });
      skeletonRows.push(row);
    }

    return skeletonRows;
  };

  useEffect(() => {
    const fetchReportConfigurations = async () => {
      try {
        setConfigLoading(true);
        const response = await reportsApi.getReportConfigurations();
        setReportConfigurations(response.data);
      } catch (error) {
        console.error('Error fetching report configurations:', error);
        alert('Error loading report configurations. See console for details.');
      } finally {
        setConfigLoading(false);
      }
    };

    fetchReportConfigurations();
  }, []);

  const handleReportChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const reportType = e.target.value;
    setActiveReport(reportType);
    setShowResults(false);

    if (reportType && reportConfigurations[reportType]) {
      setIsSkeletonMode(true);
      setShowResults(true);

      const skeletonData = generateSkeletonData(reportConfigurations[reportType]);
      setReportData(skeletonData);
    } else {
      setIsSkeletonMode(false);
      setShowResults(false);
    }
  };
  // Handler for selecting a report to edit
  const handleReportEditChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const reportId = e.target.value;
    setSelectedReportToEdit(reportId);
    
    if (reportId) {
      // Fetch the current report configuration from API
      // For now, we'll just use the existing configurations
      const reportConfig = reportConfigurations[reportId];
      if (reportConfig) {
        setConfigureMode('edit');
        // You would set these values based on the fetched report
        setReportName(reportConfig.title);
        // This is a placeholder - in a real implementation, you'd get this from the database
        setReportAggregationLevel(reportId.includes('asset') ? 'asset' : 'deal');
        // For now, simulate that we're retrieving attributes
        setSelectedAttributes([]);
      }
    } else {
      setConfigureMode(null);
    }
  };

  // Handler for creating a new report
  const handleCreateNewReport = () => {
    setSelectedReportToEdit('');
    setReportName('');
    setSelectedAttributes([]);
    setConfigureMode('create');
  };

  // Handler for selecting/deselecting attributes
  const handleAttributeToggle = (attributeName: string) => {
    setSelectedAttributes(prev => {
      if (prev.includes(attributeName)) {
        return prev.filter(attr => attr !== attributeName);
      } else {
        return [...prev, attributeName];
      }
    });
  };

  // Handler for saving report configuration
  const handleSaveReportConfig = async () => {
    if (!reportName) {
      alert('Please enter a report name');
      return;
    }
    
    if (!reportAggregationLevel) {
      alert('Please select aggregation level');
      return;
    }
    
    if (selectedAttributes.length === 0) {
      alert('Please select at least one attribute');
      return;
    }
    
    try {
      // Here you would call your API to save the report configuration
      alert(`Report configuration saved! This would be stored in the database.
Name: ${reportName}
Type: ${reportAggregationLevel}-level
Attributes: ${selectedAttributes.join(', ')}`);
      
      // Reset form
      setConfigureMode(null);
      setReportName('');
      setSelectedAttributes([]);
      setReportAggregationLevel('');
      
      // In real implementation, you would refresh the list of reports here
    } catch (error) {
      console.error('Error saving report configuration:', error);
      alert('Error saving report configuration. See console for details.');
    }
  };

  const runReport = async () => {
    if (!activeReport) {
      alert('Please select a report to run');
      return;
    }

    if (!selectedCycle || selectedCycle.value === '') {
      alert('Please select a cycle');
      return;
    }

    setLoading(true);

    try {
      const config: DynamicReportConfig = reportConfigurations[activeReport];

      const response = await reportsApi.runReport(config.apiEndpoint, {
        cycle_code: selectedCycle.value,
      });

      setReportData(response.data)
      setIsSkeletonMode(false);
      setShowResults(true);
    } catch (error) {
      console.error('Error running report:', error);
      alert('Error running report. See console for details.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h3>Reporting Dashboard</h3>
      </div>      {/* Configure Reports Card */}      {/* Configure Reports Card */}
      <div className="card mb-4">
        <div className="card-header bg-success text-white d-flex justify-content-between align-items-center">
          <h5 className="card-title mb-0">Configure Reports</h5>
          {configureMode && (
            <button 
              type="button"
              className="btn btn-outline-light btn-sm"
              onClick={() => setConfigureMode(null)}
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
                  onChange={(e) => setReportName(e.target.value)}
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
                  onChange={(e) => setReportAggregationLevel(e.target.value as 'deal' | 'asset')}
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
                            onChange={() => handleAttributeToggle(attr.name)}
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
                  onClick={handleSaveReportConfig}
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
                  onChange={handleReportEditChange}
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
                  onClick={handleCreateNewReport}
                >
                  <i className="bi bi-plus-lg"></i> Create New Report
                </button>
                <button
                  type="button"
                  className="btn btn-outline-danger"
                  disabled={!selectedReportToEdit}
                  onClick={() => {
                    if (selectedReportToEdit && window.confirm('Are you sure you want to delete this report configuration?')) {
                      alert('This would delete the report in a real implementation');
                      setSelectedReportToEdit('');
                    }
                  }}
                >
                  <i className="bi bi-trash"></i> Delete
                </button>
              </div>
            </div>
          )}
        </div>
      </div>      {/* Report Parameters Card */}
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
                onChange={handleReportChange}
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
                onClick={runReport}
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

      {/* Report Results */}
      {showResults && (
        <ReportingTable
          reportType={activeReport}
          reportData={reportData}
          loading={loading}
          reportConfig={reportConfigurations[activeReport]}
          isSkeletonMode={isSkeletonMode}
        />
      )}

      {/* Loading Overlay */}
      {loading && (
        <div className="position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center"
          style={{ backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 9999 }}>
          <div className="bg-white p-4 rounded text-center">
            <div className="spinner-border text-primary" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
            <p className="mt-2 mb-0">Running report...</p>
          </div>
        </div>
      )}
    </div>
  );
};

const Reporting = () => (
  <CycleProvider>
    <ReportingContent />
  </CycleProvider>
);

export default Reporting;
