import { useState, useEffect } from 'react';
import { reportsApi } from '@/services/api';
import { CycleProvider, useCycleContext } from '@/context/CycleContext';
import ReportingTable from '@/components/ReportingTable';
import CycleDropdown from '@/components/CycleDropdown';
import { 
  ReportBuilderWizard, 
  SavedReportsManager 
} from '@/components/reporting';
import type { 
  ReportRow, 
  DynamicReportConfig, 
  ReportConfigurationResponse,
  ReportSummary,
  DealReportRow,
  TrancheReportRow
} from '@/types';

const ReportingContent = () => {
  const { selectedCycle } = useCycleContext();

  // ===== EXISTING LEGACY REPORTS STATE (preserved for backward compatibility) =====
  const [activeReport, setActiveReport] = useState<string>('');
  const [reportData, setReportData] = useState<ReportRow[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [showResults, setShowResults] = useState<boolean>(false);
  const [isSkeletonMode, setIsSkeletonMode] = useState<boolean>(false);
  const [reportConfigurations, setReportConfigurations] = useState<ReportConfigurationResponse>({});
  const [configLoading, setConfigLoading] = useState<boolean>(true);

  // ===== NEW REPORT BUILDER STATE =====
  const [reportBuilderMode, setReportBuilderMode] = useState<boolean>(false);
  const [selectedSavedReport, setSelectedSavedReport] = useState<string>('');
  const [savedReports, setSavedReports] = useState<ReportSummary[]>([]);
  const [savedReportsLoading, setSavedReportsLoading] = useState<boolean>(false);
  
  // Edit mode state
  const [editingReport, setEditingReport] = useState<ReportConfig | null>(null);
  const [wizardMode, setWizardMode] = useState<'create' | 'edit'>('create');

  // ===== UTILITY FUNCTIONS (preserved) =====
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

  // ===== INITIALIZATION =====
  useEffect(() => {
    // Load both legacy and new report configurations
    const fetchReportConfigurations = async () => {
      try {
        setConfigLoading(true);
        
        // Load legacy report configurations for backward compatibility
        const legacyResponse = await reportsApi.getReportConfigurations();
        setReportConfigurations(legacyResponse.data);
        
      } catch (error) {
        console.error('Error fetching report configurations:', error);
        alert('Error loading report configurations. See console for details.');
      } finally {
        setConfigLoading(false);
      }
    };

    fetchReportConfigurations();
    loadSavedReports();
  }, []);

  // ===== NEW REPORT MANAGEMENT =====
  const loadSavedReports = async () => {
    setSavedReportsLoading(true);
    try {
      // TODO: Get actual user ID from auth context
      const response = await reportsApi.getUserReports('current_user');
      setSavedReports(response.data);
    } catch (error) {
      console.error('Error loading saved reports:', error);
      // Don't show alert here as this is background loading
    } finally {
      setSavedReportsLoading(false);
    }
  };

  const handleReportSaved = () => {
    setReportBuilderMode(false);
    setEditingReport(null);
    setWizardMode('create');
    loadSavedReports(); // Refresh the saved reports list
  };

  const handleCreateNewReport = () => {
    setSelectedSavedReport('');
    setEditingReport(null);
    setWizardMode('create');
    setReportBuilderMode(true);
  };

  const handleEditReport = (report: ReportConfig) => {
    setEditingReport(report);
    setWizardMode('edit');
    setReportBuilderMode(true);
  };

  const handleCancelWizard = () => {
    setReportBuilderMode(false);
    setEditingReport(null);
    setWizardMode('create');
  };

  const handleSavedReportSelect = (reportId: string) => {
    setSelectedSavedReport(reportId);
    // Clear any existing results when changing selection
    setShowResults(false);
    setReportData([]);
  };

  // ===== LEGACY REPORT HANDLERS (preserved for backward compatibility) =====
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

  const runLegacyReport = async () => {
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

      setReportData(response.data);
      setIsSkeletonMode(false);
      setShowResults(true);
    } catch (error) {
      console.error('Error running report:', error);
      alert('Error running report. See console for details.');
    } finally {
      setLoading(false);
    }
  };

  // ===== NEW SAVED REPORT EXECUTION =====
  const runSavedReport = async () => {
    if (!selectedSavedReport) {
      alert('Please select a saved report to run');
      return;
    }

    if (!selectedCycle || selectedCycle.value === '') {
      alert('Please select a cycle');
      return;
    }

    setLoading(true);

    try {
      const reportId = parseInt(selectedSavedReport);
      const response = await reportsApi.runReportById(reportId, selectedCycle.value);
      
      // Convert the response data to the format expected by ReportingTable
      setReportData(response.data as ReportRow[]);
      setIsSkeletonMode(false);
      setShowResults(true);
      
      // Clear legacy selection to avoid confusion
      setActiveReport('');
      
    } catch (error) {
      console.error('Error running saved report:', error);
      alert('Error running saved report. See console for details.');
    } finally {
      setLoading(false);
    }
  };

  // ===== RENDER HELPERS =====
  const getCurrentReportConfig = (): DynamicReportConfig | null => {
    if (activeReport && reportConfigurations[activeReport]) {
      return reportConfigurations[activeReport];
    }
    
    // For saved reports, we'd need to create a dynamic config
    // This is a simplified version - in practice, you'd want to 
    // fetch the report structure from the API
    if (selectedSavedReport && reportData.length > 0) {
      const firstRow = reportData[0];
      const columns = Object.keys(firstRow).map(key => ({
        field: key,
        header: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        type: typeof firstRow[key] === 'number' ? 'number' : 'string'
      }));
      
      const selectedReport = savedReports.find(r => r.id.toString() === selectedSavedReport);
      
      return {
        apiEndpoint: `/reports/run/${selectedSavedReport}`,
        title: selectedReport?.name || 'Saved Report',
        columns
      };
    }
    
    return null;
  };

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h3>Reporting Dashboard</h3>
      </div>

      {/* ===== NEW ENHANCED CONFIGURE REPORTS CARD ===== */}
      <div className="card mb-4">
        <div className="card-header bg-success text-white d-flex justify-content-between align-items-center">
          <h5 className="card-title mb-0">
            {reportBuilderMode 
              ? (wizardMode === 'edit' ? 'Edit Report Configuration' : 'Create New Report') 
              : 'Configure Reports'
            }
          </h5>
          {reportBuilderMode && (
            <button 
              type="button"
              className="btn btn-outline-light btn-sm"
              onClick={handleCancelWizard}
            >
              <i className="bi bi-x-lg"></i> Cancel
            </button>
          )}
        </div>
        <div className="card-body">
          {reportBuilderMode ? (
            <ReportBuilderWizard
              onReportSaved={handleReportSaved}
              onCancel={handleCancelWizard}
              editingReport={editingReport}
              mode={wizardMode}
            />
          ) : (
            <SavedReportsManager
              selectedReportId={selectedSavedReport}
              onReportSelect={handleSavedReportSelect}
              onCreateNew={handleCreateNewReport}
              onReportsUpdated={loadSavedReports}
              onEditReport={handleEditReport}
            />
          )}
        </div>
      </div>

      {/* ===== ENHANCED RUN REPORTS CARD ===== */}
      <div className="card mb-4">
        <div className="card-header bg-primary text-white">
          <h5 className="card-title mb-0">Run Reports</h5>
        </div>
        <div className="card-body">
          <div className="row g-3">
            {/* New Saved Reports Section */}
            <div className="col-md-6">
              <label htmlFor="savedReportSelect" className="form-label">Saved Report Configurations</label>
              <select
                id="savedReportSelect"
                className="form-select"
                value={selectedSavedReport}
                onChange={(e) => handleSavedReportSelect(e.target.value)}
                disabled={savedReportsLoading}
              >
                <option value="">Choose a saved report...</option>
                {savedReports.map(report => (
                  <option key={report.id} value={report.id.toString()}>
                    {report.name} ({report.scope} Level)
                  </option>
                ))}
              </select>
              {savedReportsLoading && <div className="text-muted mt-1">Loading saved reports...</div>}
            </div>

            {/* Legacy Reports Section */}
            <div className="col-md-6">
              <label htmlFor="legacyReportSelect" className="form-label">Legacy Report Templates</label>
              <select
                id="legacyReportSelect"
                className="form-select"
                value={activeReport}
                onChange={handleReportChange}
                disabled={configLoading}
              >
                <option value="">Choose a legacy report...</option>
                {Object.entries(reportConfigurations).map(([key, config]) => (
                  <option key={key} value={key}>
                    {config.title}
                  </option>
                ))}
              </select>
              {configLoading && <div className="text-muted mt-1">Loading legacy reports...</div>}
            </div>

            {/* Cycle Selection */}
            <div className="col-md-6">
              <CycleDropdown />
            </div>
            
            {/* Action Buttons */}
            <div className="col-12 mt-3 d-flex gap-2">
              <button
                type="button"
                className="btn"
                style={{ backgroundColor: '#93186C', color: 'white' }}
                onClick={selectedSavedReport ? runSavedReport : runLegacyReport}
                disabled={loading || (!selectedSavedReport && !activeReport)}
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

          {/* Report Selection Info */}
          {(selectedSavedReport || activeReport) && (
            <div className="alert alert-info mt-3">
              <i className="bi bi-info-circle me-2"></i>
              {selectedSavedReport 
                ? `Selected saved report: ${savedReports.find(r => r.id.toString() === selectedSavedReport)?.name}`
                : `Selected legacy report: ${reportConfigurations[activeReport]?.title}`
              }
            </div>
          )}
        </div>
      </div>

      {/* ===== REPORT RESULTS (preserved) ===== */}
      {showResults && (
        <ReportingTable
          reportType={selectedSavedReport || activeReport}
          reportData={reportData}
          loading={loading}
          reportConfig={getCurrentReportConfig()!}
          isSkeletonMode={isSkeletonMode}
        />
      )}

      {/* ===== LOADING OVERLAY (preserved) ===== */}
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