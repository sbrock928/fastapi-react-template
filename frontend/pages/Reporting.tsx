import { useState, useEffect } from 'react';
import { reportsApi } from '@/services/api';
import { CycleProvider, useCycleContext } from '@/context/CycleContext';
import ReportingTable from '@/components/ReportingTable';
import { ConfigureReportsCard, RunReportsCard } from '@/features/reporting/components';
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
      </div>      {/* Configure Reports Card */}
      <ConfigureReportsCard 
        reportConfigurations={reportConfigurations}
        configLoading={configLoading}
        selectedReportToEdit={selectedReportToEdit}
        configureMode={configureMode}
        reportName={reportName}
        reportAggregationLevel={reportAggregationLevel}
        selectedAttributes={selectedAttributes}
        availableAttributes={availableAttributes}
        onReportEditChange={handleReportEditChange}
        onCreateNewReport={handleCreateNewReport}
        onReportNameChange={(value) => setReportName(value)}
        onAggregationLevelChange={(value) => setReportAggregationLevel(value)}
        onAttributeToggle={handleAttributeToggle}
        onSaveReportConfig={handleSaveReportConfig}
        onCancelConfig={() => setConfigureMode(null)}        onDeleteReport={() => {
          alert('This would delete the report in a real implementation');
          setSelectedReportToEdit('');
        }}
      />      {/* Report Parameters Card */}
      <RunReportsCard 
        activeReport={activeReport}
        reportConfigurations={reportConfigurations}
        configLoading={configLoading}
        loading={loading}
        onReportChange={handleReportChange}
        onRunReport={runReport}
      />

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
