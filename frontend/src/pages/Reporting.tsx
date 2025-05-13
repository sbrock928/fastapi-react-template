import { useState } from 'react';
import { reportsApi } from '@/services/api';
import reportConfig from '@/config/reports';
import { formatDate, formatNumber, formatPercentage } from '@/utils/formatters';
import usePagination from '@/hooks/usePagination';
import type { ReportRow } from '@/types';

const Reporting = () => {
  // State variables
  const [activeReport, setActiveReport] = useState<string>('');
  const [reportData, setReportData] = useState<ReportRow[]>([]);
  const [filteredReportData, setFilteredReportData] = useState<ReportRow[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [parameters, setParameters] = useState<Record<string, string>>({
    date_range: 'last_30_days'
  });
  const [filterText, setFilterText] = useState<string>('');
  const [showResults, setShowResults] = useState<boolean>(false);
  
  // Replace pagination state with usePagination hook
  const getPagination = usePagination<ReportRow>({ initialPage: 1, itemsPerPage: 2 });
  const pagination = getPagination(filteredReportData);
  
  // Handle report type selection
  const handleReportChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const reportType = e.target.value;
    setActiveReport(reportType);
    setShowResults(false);
    
    // Reset parameters for the new report type
    if (reportType) {
      const config = reportConfig[reportType];
      const newParams: Record<string, string> = {};
      
      config.parameters.forEach(param => {
        if (param.field === 'date_range') {
          newParams[param.field] = 'last_30_days';
        } else if (param.options && param.options.length > 0) {
          newParams[param.field] = param.options[0].value;
        } else {
          newParams[param.field] = '';
        }
      });
      
      setParameters(newParams);
      
      // Also update the form elements if they exist
      config.parameters.forEach(param => {
        const element = document.getElementById(param.field) as HTMLSelectElement | HTMLInputElement;
        if (element) {
          if (param.type === 'select') {
            (element as HTMLSelectElement).value = newParams[param.field] || '';
          } else {
            (element as HTMLInputElement).value = newParams[param.field] || '';
          }
        }
      });
    }
  };
  
  // Handle parameter changes
  const handleParameterChange = (e: React.ChangeEvent<HTMLSelectElement | HTMLInputElement>) => {
    const { name, value } = e.target;
    setParameters(prev => ({
      ...prev,
      [name]: value
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
      const config = reportConfig[activeReport];
      
      const response = await reportsApi.runReport(config.apiEndpoint, parameters);
      
      setReportData(response.data);
      setFilteredReportData(response.data);
      setShowResults(true);
      setFilterText('');
      
    } catch (error) {
      console.error('Error running report:', error);
      alert('Error running report. See console for details.');
    } finally {
      setLoading(false);
    }
  };
  
  // Filter report data based on search input
  const filterReportData = (e: React.ChangeEvent<HTMLInputElement>) => {
    const filterValue = e.target.value.toLowerCase();
    setFilterText(filterValue);
    
    if (!filterValue.trim()) {
      setFilteredReportData(reportData);
    } else {
      const config = reportConfig[activeReport];
      const filtered = reportData.filter(item => {
        return config.columns.some(column => {
          if (item[column.field] !== undefined && item[column.field] !== null) {
            return item[column.field].toString().toLowerCase().includes(filterValue);
          }
          return false;
        });
      });
      
      setFilteredReportData(filtered);
    }
  };
  
  // Clear filter
  const clearFilter = () => {
    setFilterText('');
    setFilteredReportData(reportData);
  };
  
  // Export to CSV
  const exportToCsv = () => {
    if (reportData.length === 0) {
      alert('No data to export');
      return;
    }
    
    const config = reportConfig[activeReport];
    
    // Create CSV header
    let csvContent = config.columns.map(col => `"${col.header}"`).join(',') + '\n';
    
    // Add data rows
    reportData.forEach(row => {
      const csvRow = config.columns.map(col => {
        let value = row[col.field];
        
        // Format based on column type
        if (col.type === 'number') {
          value = formatNumber(value);
        } else if (col.type === 'percentage') {
          value = formatPercentage(value);
        } else if (col.type === 'date') {
          value = formatDate(value);
        }
        
        // Escape quotes and wrap in quotes
        return `"${String(value).replace(/"/g, '""')}"`;
      }).join(',');
      
      csvContent += csvRow + '\n';
    });
    
    // Create and download the file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `${config.title.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };
  
  // Export to XLSX
  const exportToXlsx = async () => {
    if (reportData.length === 0) {
      alert('No data to export');
      return;
    }
    
    setLoading(true);
    
    try {
      const config = reportConfig[activeReport];
      const fileName = `${config.title.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}`;
      
      const exportData = {
        reportType: activeReport,
        data: reportData,
        fileName: fileName
      };
      
      const response = await reportsApi.exportXlsx(exportData);
      
      // Create and download the file
      const blob = new Blob([response.data], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute('download', `${fileName}.xlsx`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
    } catch (error) {
      console.error('Error exporting to XLSX:', error);
      alert('Error exporting to XLSX. See console for details.');
    } finally {
      setLoading(false);
    }
  };
  
  // Render dynamic parameter inputs
  const renderReportParameters = () => {
    if (!activeReport) return null;
    
    const config = reportConfig[activeReport];
    
    if (config.parameters.length === 0) {
      return <div className="col-md-6"><p className="form-text text-muted">This report has no parameters.</p></div>;
    }
    
    return (
      <>
        {config.parameters.map(param => (
          <div className="col-md-6" key={param.field}>
            <label htmlFor={param.field} className="form-label">{param.label}</label>
            {param.type === 'select' ? (
              <select 
                id={param.field}
                name={param.field}
                className="form-select"
                value={parameters[param.field] || ''}
                onChange={handleParameterChange}
              >
                {param.options?.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            ) : (
              <input 
                type={param.type}
                id={param.field}
                name={param.field}
                className="form-control"
                value={parameters[param.field] || ''}
                onChange={handleParameterChange}
              />
            )}
          </div>
        ))}
      </>
    );
  };
  
  // Render the report table
  const renderReportTable = () => {
    if (!showResults || !activeReport) return null;
    
    const config = reportConfig[activeReport];
    
    if (pagination.pageItems.length === 0) {
      return (
        <table className="table table-striped" id="reportTable">
          <thead>
            <tr>
              {config.columns.map(column => (
                <th key={column.field}>{column.header}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={config.columns.length} className="text-center py-4">
                No matching data found. Try changing your filter or report parameters.
              </td>
            </tr>
          </tbody>
        </table>
      );
    }
    
    return (
      <>
        <table className="table table-striped" id="reportTable">
          <thead>
            <tr>
              {config.columns.map(column => (
                <th key={column.field}>{column.header}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pagination.pageItems.map((row, idx) => (
              <tr key={idx}>
                {config.columns.map(column => {
                  let cellValue = row[column.field];
                  let className = '';
                  
                  // Format cell based on type
                  if (column.type === 'number') {
                    className = 'report-num-cell';
                    cellValue = formatNumber(cellValue);
                  } else if (column.type === 'percentage') {
                    className = 'report-num-cell';
                    cellValue = formatPercentage(cellValue);
                  } else if (column.type === 'date') {
                    className = 'report-date-cell';
                    cellValue = formatDate(cellValue);
                  }
                  
                  return (
                    <td key={column.field} className={className}>
                      {cellValue}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
        
        {/* Replace pagination controls with usePagination */}
        {pagination.totalPages > 1 && (
          <nav aria-label="Report pagination" id="reportPagination" className="mt-3 pagination-actions-aligned">
            <ul className="pagination">
              <li className={`page-item ${pagination.currentPage === 1 ? 'disabled' : ''}`}>
                <button 
                  className="page-link" 
                  onClick={pagination.goToFirstPage}
                  disabled={pagination.currentPage === 1}
                  title="First Page"
                >
                  <i className="bi bi-chevron-double-left"></i>
                </button>
              </li>
              <li className={`page-item ${pagination.currentPage === 1 ? 'disabled' : ''}`}>
                <button 
                  className="page-link"
                  onClick={pagination.goToPreviousPage}
                  disabled={pagination.currentPage === 1}
                  title="Previous Page"
                >
                  &laquo;
                </button>
              </li>
              
              {/* Page numbers */}
              {Array.from({length: Math.min(5, pagination.totalPages)}, (_, i) => {
                let startPage = Math.max(1, pagination.currentPage - 2);
                let endPage = Math.min(pagination.totalPages, startPage + 4);
                
                if (endPage - startPage < 4) {
                  startPage = Math.max(1, endPage - 4);
                }
                
                const pageNum = i + startPage;
                
                if (pageNum <= endPage) {
                  return (
                    <li 
                      key={pageNum} 
                      className={`page-item ${pageNum === pagination.currentPage ? 'active' : ''}`}
                    >
                      <button 
                        className="page-link"
                        onClick={() => pagination.goToPage(pageNum)}
                      >
                        {pageNum}
                      </button>
                    </li>
                  );
                }
                return null;
              })}
              
              <li className={`page-item ${pagination.currentPage === pagination.totalPages ? 'disabled' : ''}`}>
                <button 
                  className="page-link"
                  onClick={pagination.goToNextPage}
                  disabled={pagination.currentPage === pagination.totalPages}
                  title="Next Page"
                >
                  &raquo;
                </button>
              </li>
              <li className={`page-item ${pagination.currentPage === pagination.totalPages ? 'disabled' : ''}`}>
                <button 
                  className="page-link"
                  onClick={pagination.goToLastPage}
                  disabled={pagination.currentPage === pagination.totalPages}
                  title="Last Page"
                >
                  <i className="bi bi-chevron-double-right"></i>
                </button>
              </li>
            </ul>
          </nav>
        )}
        
        <div className="mt-2 pagination-info">
          <small>
            Showing {filteredReportData.length === 0 ? 0 : pagination.startIndex + 1} to {pagination.endIndex} of {filteredReportData.length} rows
          </small>
        </div>
      </>
    );
  };
  
  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h1>Reporting Dashboard</h1>
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
              >
                <option value="" disabled>Choose a report...</option>
                {Object.entries(reportConfig).map(([key, config]) => (
                  <option key={key} value={key}>
                    {config.title}
                  </option>
                ))}
              </select>
            </div>
            
            {/* Dynamic parameters based on report type */}
            {renderReportParameters()}
            
            <div className="col-12 mt-3">
              <button 
                type="button" 
                id="runReportBtn" 
                className="btn btn-primary"
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

      {/* Report Results Card */}
      {showResults && (
        <div id="reportResultsCard" className="card">
          <div className="card-header bg-success text-white d-flex justify-content-between align-items-center">
            <h5 className="card-title mb-0" id="reportTitle">
              {activeReport ? reportConfig[activeReport].title : 'Report Results'}
            </h5>
            <div className="btn-group">
              <button 
                type="button" 
                id="exportCsvBtn" 
                className="btn btn-sm btn-light"
                onClick={exportToCsv}
                disabled={reportData.length === 0}
              >
                <i className="bi bi-file-earmark-text"></i> Export CSV
              </button>
              <button 
                type="button" 
                id="exportXlsxBtn" 
                className="btn btn-sm btn-light ms-2"
                onClick={exportToXlsx}
                disabled={reportData.length === 0 || loading}
              >
                <i className="bi bi-file-earmark-excel"></i> Export XLSX
              </button>
            </div>
          </div>
          <div className="card-body">
            {/* Search bar for filtering report results */}
            <div className="mb-3">
              <div className="input-group">
                <span className="input-group-text"><i className="bi bi-search"></i></span>
                <input 
                  type="text" 
                  id="reportFilterInput" 
                  className="form-control" 
                  placeholder="Filter results..."
                  value={filterText}
                  onChange={filterReportData}
                />
                {filterText && (
                  <button 
                    className="btn btn-outline-secondary" 
                    type="button"
                    onClick={clearFilter}
                    title="Clear filter"
                  >
                    <i className="bi bi-x"></i>
                  </button>
                )}
              </div>
            </div>
            
            {/* Report Table */}
            <div className="table-responsive">
              {renderReportTable()}
            </div>
          </div>
        </div>
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
  );
};

export default Reporting;