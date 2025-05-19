import { useState, useEffect } from 'react';
import { reportsApi } from '@/services/api';
import { CycleProvider } from '@/context/CycleContext';
import CycleDropdown from '@/components/CycleDropdown';
import ReportingTable from '@/components/ReportingTable';
import type { ReportRow, DynamicReportConfig, ReportConfigurationResponse } from '@/types';

const Reporting = () => {
  // State variables
  const [activeReport, setActiveReport] = useState<string>('');
  const [reportData, setReportData] = useState<ReportRow[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [parameters, setParameters] = useState<Record<string, string>>({
    cycle_code: ''
  });
  const [showResults, setShowResults] = useState<boolean>(false);
  const [isSkeletonMode, setIsSkeletonMode] = useState<boolean>(false);
  const [reportConfigurations, setReportConfigurations] = useState<ReportConfigurationResponse>({});
  const [configLoading, setConfigLoading] = useState<boolean>(true);
  
  // Generate skeleton data based on the selected report configuration
  const generateSkeletonData = (config: DynamicReportConfig, rowCount = 5): ReportRow[] => {
    const skeletonRows: ReportRow[] = [];
    
    // Create placeholder rows
    for (let i = 0; i < rowCount; i++) {
      const row: ReportRow = {};
      
      // For each column in the config, create a placeholder value based on type
      config.columns.forEach(column => {
        switch (column.type) {
          case 'number':
            row[column.field] = 0;
            break;
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
  
  // Fetch report configurations when component mounts
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
  
  // Handle report type selection
  const handleReportChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const reportType = e.target.value;
    setActiveReport(reportType);
    setShowResults(false);
    
    // Reset parameters for the new report type
    setParameters({
      cycle_code: ''
    });
    
    // If a report is selected, show skeleton
    if (reportType && reportConfigurations[reportType]) {
      setIsSkeletonMode(true);
      setShowResults(true);
      
      // Generate skeleton data
      const skeletonData = generateSkeletonData(reportConfigurations[reportType]);
      setReportData(skeletonData);
    } else {
      setIsSkeletonMode(false);
      setShowResults(false);
    }
  };
  
  // Handle parameter changes
  const handleCycleCodeChange = (value: string) => {
    setParameters(prev => ({
      ...prev,
      cycle_code: value
    }));
  };
  
  // Run the selected report
  const runReport = async () => {
    if (!activeReport) {
      alert('Please select a report to run');
      return;
    }
    
    setLoading(true);
    
    try {
      const config: DynamicReportConfig = reportConfigurations[activeReport];
      
      const response = await reportsApi.runReport(config.apiEndpoint, parameters);
      
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
  
  return (
    <CycleProvider>
      <div>
        <div className="d-flex justify-content-between align-items-center mb-4">
          <h3>Reporting Dashboard</h3>
        </div>

        {/* Report Parameters Card */}
        <div className="card mb-4">
          <div className="card-header bg-primary text-white">
            <h5 className="card-title mb-0">Report Parameters</h5>
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
              
              {/* Cycle Code dropdown is always included */}
              <div className="col-md-6">
                <CycleDropdown 
                  value={parameters.cycle_code}
                  onChange={handleCycleCodeChange}
                />
              </div>
              
              <div className="col-12 mt-3">
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
              </div>
            </form>
          </div>
        </div>

        {/* Report Results using ReportingTable component */}
        {showResults && (
          <ReportingTable 
            reportType={activeReport}
            reportData={reportData}
            loading={loading}
            reportConfig={reportConfigurations[activeReport]}
            isSkeletonMode={isSkeletonMode}
          />
        )}

        {/* Loading overlay */}
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
    </CycleProvider>
  );
};

export default Reporting;