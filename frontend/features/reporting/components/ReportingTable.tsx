import React, { useState, useEffect } from 'react';
import { formatDate, formatNumber, formatPercentage } from '@/utils/formatters';
import usePagination from '@/hooks/usePagination';
import type { ReportRow, DynamicReportConfig } from '@/types';
import { reportingApi } from '@/services/api';
import styles from '@/styles/components/ReportingTable.module.css';

interface ReportingTableProps {
  reportType: string;
  reportData: ReportRow[];
  loading: boolean;
  reportConfig: DynamicReportConfig;
  isSkeletonMode?: boolean;
  // New props for backend column management
  backendColumns?: Array<{
    field: string;
    header: string;
    format_type: string;
    display_order: number;
  }>;
  useBackendFormatting?: boolean;
}

const ReportingTable: React.FC<ReportingTableProps> = ({ 
  reportType, 
  reportData, 
  loading,
  reportConfig,
  isSkeletonMode = false,
  backendColumns,
  useBackendFormatting = false
}) => {
  const [filteredReportData, setFilteredReportData] = useState<ReportRow[]>([]);
  const [filterText, setFilterText] = useState<string>('');
  const getPagination = usePagination<ReportRow>({ initialPage: 1, itemsPerPage: 10 });
  const pagination = getPagination(filteredReportData);
  
  useEffect(() => {
    setFilteredReportData(reportData);
    setFilterText('');
  }, [reportData]);
  
  // Generate smart placeholder text based on column information
  const generatePlaceholderValue = (column: any, rowIndex: number): string => {
    const formatType = useBackendFormatting && 'format_type' in column 
      ? column.format_type 
      : (column as any).type;
    
    const fieldName = column.field.toLowerCase();
    
    // Generate contextual placeholder data
    if (formatType === 'number') {
      if (fieldName.includes('deal')) {
        return (1001 + rowIndex).toString();
      } else if (fieldName.includes('cycle')) {
        return (202400 + rowIndex).toString();
      }
      return (12345 + rowIndex * 100).toString();
    } else if (formatType === 'currency') {
      const baseAmount = 100000 + (rowIndex * 15000);
      return `$${baseAmount.toLocaleString()}.00`;
    } else if (formatType === 'percentage') {
      const percentage = (15.5 + (rowIndex * 2.5)).toFixed(1);
      return `${percentage}%`;
    } else if (formatType === 'date' || formatType === 'date_mdy' || formatType === 'date_dmy') {
      const date = new Date(2025, 0, 15 + rowIndex);
      return formatType === 'date_dmy' 
        ? date.toLocaleDateString('en-GB')
        : date.toLocaleDateString('en-US');
    } else {
      // Text fields with smart defaults
      if (fieldName.includes('deal')) {
        return `DEAL-${1001 + rowIndex}`;
      } else if (fieldName.includes('tranche')) {
        return `TR-${String.fromCharCode(65 + (rowIndex % 26))}`;
      } else if (fieldName.includes('issuer') || fieldName.includes('sponsor')) {
        const issuers = ['Goldman Sachs', 'JP Morgan', 'Wells Fargo', 'Bank of America', 'Citibank'];
        return issuers[rowIndex % issuers.length];
      } else if (fieldName.includes('rating')) {
        const ratings = ['AAA', 'AA+', 'AA', 'AA-', 'A+'];
        return ratings[rowIndex % ratings.length];
      } else if (fieldName.includes('type') || fieldName.includes('category')) {
        const types = ['Fixed Rate', 'Floating Rate', 'Interest Only', 'Principal Only'];
        return types[rowIndex % types.length];
      }
      return `${column.header} ${rowIndex + 1}`;
    }
  };
  
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
        fileName: fileName,
        columnPreferences: undefined // Changed from null to undefined to match the type
      };
      
      const response = await reportingApi.exportXlsx(exportData);
      
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
      URL.revokeObjectURL(url);
      
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
      <div className={`card-header text-white d-flex justify-content-between align-items-center ${styles.reportHeader}`}>
        <h5 className={`card-title mb-0 ${styles.reportTitle}`} id="reportTitle">
          {reportConfig.title}
        </h5>
        <div className="btn-group">
          <button 
            type="button" 
            id="exportCsvBtn" 
            className={`btn btn-sm btn-light ${styles.exportButton}`}
            onClick={exportToCsv}
            disabled={reportData.length === 0 || isSkeletonMode}
          >
            <i className="bi bi-file-earmark-text"></i> Export CSV
          </button>
          <button 
            type="button" 
            id="exportXlsxBtn" 
            className={`btn btn-sm btn-light ms-2 ${styles.exportButton}`}
            onClick={exportToXlsx}
            disabled={reportData.length === 0 || loading || isSkeletonMode}
          >
            <i className="bi bi-file-earmark-excel"></i> Export XLSX
          </button>
        </div>
      </div>
      <div className="card-body">
        {/* Search bar and rows per page selector */}
        <div className="mb-3">
          <div className="row g-2">
            <div className="col-md-8">
              <div className="input-group">
                <span className="input-group-text"><i className="bi bi-search"></i></span>
                <input 
                  type="text" 
                  id="reportFilterInput" 
                  className={`form-control ${styles.filterInput}`} 
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
            <div className="col-md-4">
              <div className="d-flex align-items-center">
                <label htmlFor="rowsPerPageSelect" className="form-label me-2 mb-0 text-nowrap">
                  Rows per page:
                </label>
                <select 
                  id="rowsPerPageSelect"
                  className="form-select"
                  value={pagination.itemsPerPage}
                  onChange={(e) => {
                    const newItemsPerPage = parseInt(e.target.value);
                    pagination.setItemsPerPage(newItemsPerPage);
                    // Reset to first page on items per page change
                    pagination.goToFirstPage();
                  }}
                  disabled={isSkeletonMode}
                >
                  <option value={5}>5</option>
                  <option value={10}>10</option>
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                  <option value={250}>250</option>
                  <option value={500}>500</option>
                  <option value={1000}>1000</option>
                  <option value={filteredReportData.length || reportData.length}>All ({filteredReportData.length || reportData.length})</option>
                </select>
              </div>
            </div>
          </div>
        </div>
        
        {/* Add skeleton mode notice */}
        {isSkeletonMode && (
          <div className={`alert alert-info mb-3 ${styles.skeletonNotice}`}>
            <div className="d-flex align-items-center">
              <div className={styles.skeletonIcon}>
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
        <div className={`table-responsive ${styles.tableResponsive}`}>
          {renderReportTable()}
        </div>
        
        {/* Pagination controls */}
        {pagination.totalPages > 1 && !isSkeletonMode && (
          <nav aria-label="Report pagination" id="reportPagination" className="mt-3 pagination-actions-aligned">
            <ul className="pagination justify-content-center">
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
      </div>
    </div>
  );
  
  function renderReportTable() {
    // Use backend columns if available and backend formatting is enabled
    const columnsToUse = useBackendFormatting && backendColumns ? backendColumns : reportConfig.columns;
    
    if (filteredReportData.length === 0) {
      return (
        <table className="table table-striped" id="reportTable">
          <thead>
            <tr>
              {columnsToUse.map(column => (
                <th key={column.field}>{column.header}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={columnsToUse.length} className="text-center py-4">
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
              {columnsToUse.map(column => (
                <th key={column.field}>{column.header}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pagination.pageItems.map((row, idx) => (
              <tr key={idx}>
                {columnsToUse.map(column => {
                  let cellValue = row[column.field];
                  let className = '';
                  
                  // Use backend formatting if available, otherwise fall back to frontend formatting
                  if (useBackendFormatting && 'format_type' in column) {
                    // Backend formatting - data is already formatted, just apply CSS classes
                    const formatType = column.format_type;
                    
                    if (formatType === 'number') {
                      className = 'report-num-cell';
                    } else if (formatType === 'currency') {
                      className = 'report-num-cell';
                    } else if (formatType === 'percentage') {
                      className = 'report-num-cell';
                    } else if (formatType === 'date_mdy' || formatType === 'date_dmy') {
                      className = 'report-date-cell';
                    }
                    // For 'text' format type, no additional formatting or CSS class needed
                    
                  } else {
                    // Legacy frontend formatting (for backwards compatibility)
                    const legacyColumn = column as any;
                    if (legacyColumn.type === 'number') {
                      className = 'report-num-cell';
                      cellValue = formatNumber(cellValue);
                    } else if (legacyColumn.type === 'percentage') {
                      className = 'report-num-cell';
                      cellValue = formatPercentage(cellValue);
                    } else if (legacyColumn.type === 'date') {
                      className = 'report-date-cell';
                      cellValue = formatDate(cellValue);
                    }
                  }
                  
                  // Add skeleton class if in skeleton mode
                  if (isSkeletonMode) {
                    className += ' skeleton-shimmer';
                    
                    // For skeleton mode, replace actual values with reasonable placeholders
                    cellValue = generatePlaceholderValue(column, idx);
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
      </>
    );
  }
};

export default ReportingTable;