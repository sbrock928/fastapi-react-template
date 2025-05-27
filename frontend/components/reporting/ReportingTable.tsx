import React, { useState, useEffect } from 'react';
import { formatDate, formatNumber, formatPercentage } from '@/utils/formatters';
import usePagination from '@/hooks/usePagination';
import type { ReportRow, DynamicReportConfig } from '@/types';
import { reportsApi } from '@/services/api';

interface ReportingTableProps {
  reportType: string;
  reportData: ReportRow[];
  loading: boolean;
  reportConfig: DynamicReportConfig;
  isSkeletonMode?: boolean;
}

const ReportingTable: React.FC<ReportingTableProps> = ({ 
  reportType, 
  reportData, 
  loading,
  reportConfig,
  isSkeletonMode = false
}) => {
  const [filteredReportData, setFilteredReportData] = useState<ReportRow[]>([]);
  const [filterText, setFilterText] = useState<string>('');
  const getPagination = usePagination<ReportRow>({ initialPage: 1, itemsPerPage: 10 });
  const pagination = getPagination(filteredReportData);
  
  useEffect(() => {
    setFilteredReportData(reportData);
    setFilterText('');
  }, [reportData]);
  
  // Export to CSV
  const exportToCsv = () => {
    if (reportData.length === 0) {
      alert('No data to export');
      return;
    }
    
    // Create CSV header
    let csvContent = reportConfig.columns.map(col => `"${col.header}"`).join(',') + '\n';
    
    // Add data rows
    reportData.forEach(row => {
      const csvRow = reportConfig.columns.map(col => {
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
    link.setAttribute('download', `${reportConfig.title.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.csv`);
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
    
    try {
      const fileName = `${reportConfig.title.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}`;
      
      const exportData = {
        reportType: reportType,
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
    }
  };
  
  // Filter report data based on search input
  const filterReportData = (e: React.ChangeEvent<HTMLInputElement>) => {
    const filterValue = e.target.value.toLowerCase();
    setFilterText(filterValue);
    
    if (!filterValue.trim()) {
      setFilteredReportData(reportData);
      return;
    }
    
    // Only filter if we have an active report and data
    if (reportType && reportData.length > 0) {
      const filtered = reportData.filter(item => 
        reportConfig.columns.some(column => {
          const value = item[column.field];
          return value != null && String(value).toLowerCase().includes(filterValue);
        })
      );
      setFilteredReportData(filtered);
    }
  };
  
  // Clear filter
  const clearFilter = () => {
    setFilterText('');
    setFilteredReportData(reportData);
  };
  
  if (!reportType || !reportConfig) return null;
  
  return (
    <div id="reportResultsCard" className="card">
      <div className="card-header text-white d-flex justify-content-between align-items-center" style={{ backgroundColor: '#28a745' }}>
        <h5 className="card-title mb-0" id="reportTitle">
          {reportConfig.title}
        </h5>
        <div className="btn-group">
          <button 
            type="button" 
            id="exportCsvBtn" 
            className="btn btn-sm btn-light"
            onClick={exportToCsv}
            disabled={reportData.length === 0 || isSkeletonMode}
          >
            <i className="bi bi-file-earmark-text"></i> Export CSV
          </button>
          <button 
            type="button" 
            id="exportXlsxBtn" 
            className="btn btn-sm btn-light ms-2"
            onClick={exportToXlsx}
            disabled={reportData.length === 0 || loading || isSkeletonMode}
          >
            <i className="bi bi-file-earmark-excel"></i> Export XLSX
          </button>
        </div>
      </div>
      <div className="card-body">
        {/* Search bar for filtering report results - disabled in skeleton mode */}
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
              disabled={isSkeletonMode}
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
        
        {/* Add skeleton mode notice */}
        {isSkeletonMode && (
          <div className="alert alert-info mb-3">
            <div className="d-flex align-items-center">
              <div className="me-3">
                <i className="bi bi-info-circle-fill"></i>
              </div>
              <div>
                <small>
                  This is a preview of the report structure. Click "Run Report" to see actual data.
                </small>
              </div>
            </div>
          </div>
        )}
        
        {/* Report Table */}
        <div className="table-responsive">
          {renderReportTable()}
        </div>
        
        {/* Add CSS for skeleton shimmer effect */}
        <style>
          {`
          @keyframes shimmer {
            0% {
              background-position: -1000px 0;
            }
            100% {
              background-position: 1000px 0;
            }
          }
          
          .skeleton-shimmer {
            animation: shimmer 2s infinite linear;
            background: linear-gradient(to right, #f6f7f8 8%, #edeef1 18%, #f6f7f8 33%);
            background-size: 1000px 100%;
            color: transparent !important;
            border-radius: 4px;
          }
          `}
        </style>
      </div>
    </div>
  );
  
  function renderReportTable() {
    if (filteredReportData.length === 0) {
      return (
        <table className="table table-striped" id="reportTable">
          <thead>
            <tr>
              {reportConfig.columns.map(column => (
                <th key={column.field}>{column.header}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={reportConfig.columns.length} className="text-center py-4">
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
              {reportConfig.columns.map(column => (
                <th key={column.field}>{column.header}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pagination.pageItems.map((row, idx) => (
              <tr key={idx}>
                {reportConfig.columns.map(column => {
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
                  
                  // Add skeleton class if in skeleton mode
                  if (isSkeletonMode) {
                    className += ' skeleton-shimmer';
                    
                    // For skeleton mode, replace actual values with reasonable placeholders
                    if (column.type === 'number') {
                      cellValue = '10000';
                    } else if (column.type === 'percentage') {
                      cellValue = '100%';
                    } else if (column.type === 'date') {
                      cellValue = '2025-01-01';
                    } else {
                      cellValue = 'Example data';
                    }
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
        
        {/* Pagination controls */}
        {pagination.totalPages > 1 && !isSkeletonMode && (
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
        
        {!isSkeletonMode && (
          <div className="mt-2 pagination-info">
            <small>
              Showing {filteredReportData.length === 0 ? 0 : pagination.startIndex + 1} to {pagination.endIndex} of {filteredReportData.length} rows
            </small>
          </div>
        )}
      </>
    );
  }
};

export default ReportingTable;