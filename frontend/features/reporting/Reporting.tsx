import { useState } from 'react';
import { reportingApi } from '@/services/api';
import { useCycleContext, useReportContext } from '@/context';
import { useToast } from '@/context/ToastContext';
import { 
  ReportManagementCard,
  RunReportsCard,
  ReportingTable
} from './components';
import type { 
  ReportRow, 
  DynamicReportConfig,
  ReportConfig
} from '@/types';

const ReportingContent = () => {
  const { selectedCycle } = useCycleContext();
  const { savedReports, refreshReports } = useReportContext();
  const { showToast } = useToast();

  // ===== REPORT STATE =====
  const [reportData, setReportData] = useState<ReportRow[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [showResults, setShowResults] = useState<boolean>(false);
  const [isSkeletonMode, setIsSkeletonMode] = useState<boolean>(false);
  const [reportSchema, setReportSchema] = useState<any>(null);

  // ===== REPORT BUILDER STATE =====
  const [reportBuilderMode, setReportBuilderMode] = useState<boolean>(false);
  const [selectedSavedReport, setSelectedSavedReport] = useState<string>('');
  
  // Edit mode state
  const [editingReport, setEditingReport] = useState<ReportConfig | null>(null);
  const [wizardMode, setWizardMode] = useState<'create' | 'edit'>('create');

  // ===== REPORT MANAGEMENT HANDLERS =====
  const handleReportSaved = () => {
    setReportBuilderMode(false);
    setEditingReport(null);
    setWizardMode('create');
    refreshReports();
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
    
    // Load skeleton data when a report is selected
    if (reportId) {
      loadReportSkeleton(reportId);
    }
  };

  // ===== SKELETON DATA LOADING =====
  const loadReportSkeleton = async (reportId: string) => {
    try {
      const response = await reportingApi.getReportSchema(parseInt(reportId));
      const skeletonData = response.data;
      
      // Store the schema for better column information
      setReportSchema(skeletonData);
      
      // Set skeleton data and show results
      setReportData(skeletonData.skeleton_data as ReportRow[]);
      setIsSkeletonMode(true);
      setShowResults(true);
      
      showToast(`Loaded preview for ${skeletonData.title}`, 'info');
    } catch (error: any) {
      console.error('Error loading report skeleton:', error);
      
      // Don't show error toast for skeleton loading failures - just silently fail
      // The user can still run the report normally
    }
  };

  // ===== REPORT EXECUTION =====
  const runSavedReport = async () => {
    if (!selectedSavedReport) {
      showToast('Please select a saved report to run', 'warning');
      return;
    }

    if (!selectedCycle || selectedCycle.value === 0) {
      showToast('Please select a cycle', 'warning');
      return;
    }

    setLoading(true);

    try {
      const reportId = parseInt(selectedSavedReport);
      const response = await reportingApi.runReportById(reportId, selectedCycle.value);
      
      setReportData(response.data as ReportRow[]);
      setIsSkeletonMode(false);
      setShowResults(true);
      
    } catch (error: any) {
      console.error('Error running saved report:', error);
      
      // Extract detailed error messages from the API response
      let errorMessage = 'Error running saved report';
      
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        
        if (detail.errors && Array.isArray(detail.errors)) {
          // Handle the backend's errors array format
          const errorMessages = detail.errors.join(', ');
          errorMessage = `${errorMessage}: ${errorMessages}`;
        } else if (typeof detail === 'string') {
          // Handle simple string error messages
          errorMessage = `${errorMessage}: ${detail}`;
        } else if (typeof detail === 'object' && detail.message) {
          // Handle other object formats with a message property
          errorMessage = `${errorMessage}: ${detail.message}`;
        }
      } else if (error.response?.data?.message) {
        // Handle other API error formats
        errorMessage = `${errorMessage}: ${error.response.data.message}`;
      } else if (error.message) {
        // Handle network or other errors
        errorMessage = `${errorMessage}: ${error.message}`;
      }
      
      // Use toast instead of alert for better UX
      showToast(errorMessage, 'error');
    } finally {
      setLoading(false);
    }
  };

  // ===== RENDER HELPERS =====
  const getCurrentReportConfig = (): DynamicReportConfig | null => {
    if (selectedSavedReport && reportData.length > 0) {
      // Use schema data if in skeleton mode for better column information
      if (isSkeletonMode && reportSchema) {
        return {
          apiEndpoint: `/reports/run/${selectedSavedReport}`,
          title: reportSchema.title,
          columns: reportSchema.columns.map((col: any) => ({
            field: col.field,
            header: col.header,
            type: col.type
          }))
        };
      }
      
      // Fallback to dynamic generation from data
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

      {/* ===== REPORT MANAGEMENT SECTION ===== */}
      <ReportManagementCard
        reportBuilderMode={reportBuilderMode}
        wizardMode={wizardMode}
        editingReport={editingReport}
        selectedSavedReport={selectedSavedReport}
        onReportSaved={handleReportSaved}
        onCreateNewReport={handleCreateNewReport}
        onEditReport={handleEditReport}
        onCancelWizard={handleCancelWizard}
        onSavedReportSelect={handleSavedReportSelect}
        onReportsUpdated={refreshReports}
      />

      {/* ===== RUN REPORTS SECTION ===== */}
      <RunReportsCard
        selectedSavedReport={selectedSavedReport}
        loading={loading}
        onSavedReportSelect={handleSavedReportSelect}
        onRunReport={runSavedReport}
      />

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