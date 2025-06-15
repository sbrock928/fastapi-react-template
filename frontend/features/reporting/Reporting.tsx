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
  const [backendColumns, setBackendColumns] = useState<Array<{
    field: string;
    header: string;
    format_type: string;
    display_order: number;
  }> | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [showResults, setShowResults] = useState<boolean>(false);
  const [isSkeletonMode, setIsSkeletonMode] = useState<boolean>(false);
  // New state for skeleton data
  const [skeletonColumns, setSkeletonColumns] = useState<Array<{
    field: string;
    header: string;
    format_type: string;
    display_order: number;
  }> | null>(null);

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
    refreshReports(true); // Force refresh when a report is saved
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

  const handleSavedReportSelect = async (reportId: string) => {
    setSelectedSavedReport(reportId);
    setShowResults(false);
    setReportData([]);
    setBackendColumns(null);
    
    // If a report is selected, show skeleton mode with report structure
    if (reportId) {
      await showReportStructure(reportId);
    } else {
      // Clear skeleton mode if no report selected
      setIsSkeletonMode(false);
      setSkeletonColumns(null);
    }
  };

  // New function to fetch and display report structure
  const showReportStructure = async (reportId: string) => {
    try {
      setIsSkeletonMode(true);
      setShowResults(true);
      
      // Fetch report structure from the API
      const response = await reportingApi.getReportStructure(parseInt(reportId));
      const reportStructure = response.data;
      
      if (reportStructure.columns && reportStructure.columns.length > 0) {
        // Use API response to build skeleton structure
        const columns = reportStructure.columns.map(col => ({
          field: col.field,
          header: col.header,
          format_type: col.format_type,
          display_order: col.display_order
        }));
        
        setSkeletonColumns(columns);
        // Generate skeleton data (5 rows for preview)
        const skeletonData = generateSkeletonData(columns, 5);
        setReportData(skeletonData);
      } else {
        // Fallback: create basic structure if no columns from API
        const basicColumns = [
          { field: 'deal_number', header: 'Deal Number', format_type: 'number', display_order: 0 },
          { field: 'cycle_code', header: 'Cycle Code', format_type: 'number', display_order: 1 },
          { field: 'calculation_result', header: 'Calculation Result', format_type: 'currency', display_order: 2 }
        ];
        
        setSkeletonColumns(basicColumns);
        const skeletonData = generateSkeletonData(basicColumns, 5);
        setReportData(skeletonData);
      }
    } catch (error) {
      console.error('Error loading report structure:', error);
      // Don't show error toast for skeleton mode, just disable it
      setIsSkeletonMode(false);
      setSkeletonColumns(null);
      setShowResults(false);
    }
  };

  // Helper function to generate skeleton data
  const generateSkeletonData = (columns: Array<{field: string, header: string, format_type: string, display_order: number}>, rowCount: number): ReportRow[] => {
    const skeletonRows: ReportRow[] = [];
    
    for (let i = 0; i < rowCount; i++) {
      const row: ReportRow = {};
      
      columns.forEach(col => {
        // Generate appropriate placeholder data based on format type
        switch (col.format_type) {
          case 'number':
            row[col.field] = 12345 + i;
            break;
          case 'currency':
            row[col.field] = `$${(100000 + i * 1000).toLocaleString()}.00`;
            break;
          case 'percentage':
            row[col.field] = `${(25 + i * 5)}%`;
            break;
          case 'date_mdy':
            row[col.field] = new Date(2025, 0, 15 + i).toLocaleDateString('en-US');
            break;
          case 'date_dmy':
            row[col.field] = new Date(2025, 0, 15 + i).toLocaleDateString('en-GB');
            break;
          default: // text
            if (col.field.includes('deal')) {
              row[col.field] = `DEAL-${1001 + i}`;
            } else if (col.field.includes('tranche')) {
              row[col.field] = `TR-${String.fromCharCode(65 + i)}`;
            } else if (col.field.includes('cycle')) {
              row[col.field] = 202400 + i;
            } else {
              row[col.field] = `Sample ${col.header} ${i + 1}`;
            }
        }
      });
      
      skeletonRows.push(row);
    }
    
    return skeletonRows;
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
      const response = await reportingApi.runReportById(reportId, selectedCycle.value as number);
      
      // Handle the new API response structure
      const { data, columns } = response.data;
      setReportData(data);
      setBackendColumns(columns);
      setSkeletonColumns(null); // Clear skeleton columns when real data loads
      setIsSkeletonMode(false);
      setShowResults(true);
      
      showToast(`Report executed successfully! ${data.length} rows returned.`, 'success');
      
    } catch (error: any) {
      console.error('Error running saved report:', error);
      
      // Extract detailed error messages from the API response
      let errorMessage = 'Error running saved report';
      
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        
        if (detail.errors && Array.isArray(detail.errors)) {
          const errorMessages = detail.errors.join(', ');
          errorMessage = `${errorMessage}: ${errorMessages}`;
        } else if (typeof detail === 'string') {
          errorMessage = `${errorMessage}: ${detail}`;
        } else if (typeof detail === 'object' && detail.message) {
          errorMessage = `${errorMessage}: ${detail.message}`;
        }
      } else if (error.response?.data?.message) {
        errorMessage = `${errorMessage}: ${error.response.data.message}`;
      } else if (error.message) {
        errorMessage = `${errorMessage}: ${error.message}`;
      }
      
      showToast(errorMessage, 'error');
    } finally {
      setLoading(false);
    }
  };

  // ===== RENDER HELPERS =====
  const getCurrentReportConfig = (): DynamicReportConfig | null => {
    // Use skeleton columns when in skeleton mode, otherwise use actual data structure
    if (isSkeletonMode && skeletonColumns) {
      const selectedReport = savedReports.find(r => r.id.toString() === selectedSavedReport);
      
      return {
        apiEndpoint: `/reports/run/${selectedSavedReport}`,
        title: selectedReport?.name || 'Report Preview',
        columns: skeletonColumns.map(col => ({
          field: col.field,
          header: col.header,
          type: col.format_type as 'string' | 'number' | 'currency' | 'percentage' | 'date'
        }))
      };
    }
    
    if (selectedSavedReport && reportData.length > 0) {
      const firstRow = reportData[0];
      const columns = Object.keys(firstRow).map(key => ({
        field: key,
        header: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        type: (typeof firstRow[key] === 'number' ? 'number' : 'string') as 'string' | 'number' | 'currency' | 'percentage' | 'date'
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
          backendColumns={isSkeletonMode ? skeletonColumns || undefined : backendColumns || undefined}
          useBackendFormatting={!isSkeletonMode && backendColumns !== null}
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