import { useState } from 'react';
import { reportsApi } from '@/services/api';
import { useCycleContext, useReportContext } from '@/context';
import { 
  ReportBuilderWizard, 
  SavedReportsManager,
  CycleDropdown,
  ReportDropdown,
  ReportingTable
} from '@/components/reporting';
import type { 
  ReportRow, 
  DynamicReportConfig,
  ReportConfig
} from '@/types';

const ReportingContent = () => {
  const { selectedCycle } = useCycleContext();
  const { savedReports, refreshReports } = useReportContext();

  // ===== REPORT STATE =====
  const [reportData, setReportData] = useState<ReportRow[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [showResults, setShowResults] = useState<boolean>(false);
  const [isSkeletonMode, setIsSkeletonMode] = useState<boolean>(false);

  // ===== NEW REPORT BUILDER STATE =====
  const [reportBuilderMode, setReportBuilderMode] = useState<boolean>(false);
  const [selectedSavedReport, setSelectedSavedReport] = useState<string>('');
  
  // Edit mode state
  const [editingReport, setEditingReport] = useState<ReportConfig | null>(null);
  const [wizardMode, setWizardMode] = useState<'create' | 'edit'>('create');

  // ===== NEW REPORT MANAGEMENT =====
  const handleReportSaved = () => {
    setReportBuilderMode(false);
    setEditingReport(null);
    setWizardMode('create');
    refreshReports(); // Use context method instead of local function
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
    setSelectedSavedReport('');
  };

  const handleSavedReportSelect = (reportId: string) => {
    setSelectedSavedReport(reportId);
    setShowResults(false);
    setReportData([]);
  };

  // ===== SAVED REPORT EXECUTION =====
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
      
      setReportData(response.data as ReportRow[]);
      setIsSkeletonMode(false);
      setShowResults(true);
      
    } catch (error) {
      console.error('Error running saved report:', error);
      alert('Error running saved report. See console for details.');
    } finally {
      setLoading(false);
    }
  };

  // ===== RENDER HELPERS =====
  const getCurrentReportConfig = (): DynamicReportConfig | null => {
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

      {/* ===== REPORT MANAGEMENT CARD ===== */}
      <div className="card mb-4">
        <div className="card-header bg-success text-white d-flex justify-content-between align-items-center">
          <h5 className="card-title mb-0">
            {reportBuilderMode 
              ? (wizardMode === 'edit' ? 'Edit Report Configuration' : 'Create New Report') 
              : 'Manage Reports'
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
              editingReport={editingReport}
              mode={wizardMode}
            />
          ) : (
            <SavedReportsManager
              selectedReportId={selectedSavedReport}
              onReportSelect={handleSavedReportSelect}
              onCreateNew={handleCreateNewReport}
              onReportsUpdated={refreshReports}
              onEditReport={handleEditReport}
            />
          )}
        </div>
      </div>

      {/* ===== RUN REPORTS CARD ===== */}
      <div className="card mb-4">
        <div className="card-header bg-primary text-white">
          <h5 className="card-title mb-0">Run Reports</h5>
        </div>
        <div className="card-body">
          <div className="row g-3">
            <div className="col-md-6">
              <ReportDropdown
                selectedReportId={selectedSavedReport}
                onReportSelect={handleSavedReportSelect}
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
                onClick={runSavedReport}
                disabled={loading || !selectedSavedReport || !selectedCycle || selectedCycle.value === ''}
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

          {selectedSavedReport && (
            <div className="alert alert-info mt-3">
              <i className="bi bi-info-circle me-2"></i>
              Selected saved report: {savedReports.find(r => r.id.toString() === selectedSavedReport)?.name}
            </div>
          )}
        </div>
      </div>

      {/* ===== REPORT RESULTS ===== */}
      {showResults && (
        <ReportingTable
          reportType={selectedSavedReport}
          reportData={reportData}
          loading={loading}
          reportConfig={getCurrentReportConfig()!}
          isSkeletonMode={isSkeletonMode}
        />
      )}

      {/* ===== LOADING OVERLAY ===== */}
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
  <ReportingContent />
);

export default Reporting;