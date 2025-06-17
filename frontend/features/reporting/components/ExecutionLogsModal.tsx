import React, { useState, useEffect, useMemo } from 'react';
import { reportingApi } from '@/services/api';
import { useToast } from '@/context/ToastContext';
import type { ReportExecutionLog } from '@/types/reporting';

interface ExecutionLogsModalProps {
  reportId: number;
  reportName: string;
  isOpen: boolean;
  onClose: () => void;
}

const ExecutionLogsModal: React.FC<ExecutionLogsModalProps> = ({
  reportId,
  reportName,
  isOpen,
  onClose
}) => {
  const [logs, setLogs] = useState<ReportExecutionLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(10); // Show 10 logs per page
  const { showToast } = useToast();

  // Reset to first page when modal opens
  useEffect(() => {
    if (isOpen) {
      setCurrentPage(1);
    }
  }, [isOpen]);

  useEffect(() => {
    if (isOpen && reportId) {
      fetchExecutionLogs();
    }
  }, [isOpen, reportId]);

  // Paginated data
  const paginatedLogs = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return logs.slice(startIndex, endIndex);
  }, [logs, currentPage, itemsPerPage]);

  // Pagination calculations
  const totalPages = Math.ceil(logs.length / itemsPerPage);
  const startItem = (currentPage - 1) * itemsPerPage + 1;
  const endItem = Math.min(currentPage * itemsPerPage, logs.length);

  const fetchExecutionLogs = async () => {
    setLoading(true);
    try {
      const response = await reportingApi.getExecutionLogs(reportId);
      setLogs(response.data);
    } catch (error: any) {
      console.error('Error fetching execution logs:', error);
      showToast('Failed to load execution logs', 'error');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const formatDuration = (milliseconds: number | null | undefined) => {
    if (!milliseconds) return 'N/A';
    if (milliseconds < 1000) return `${Math.round(milliseconds)}ms`;
    return `${(milliseconds / 1000).toFixed(2)}s`;
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handlePrevious = () => {
    setCurrentPage(prev => Math.max(prev - 1, 1));
  };

  const handleNext = () => {
    setCurrentPage(prev => Math.min(prev + 1, totalPages));
  };

  // Generate page numbers for pagination
  const getPageNumbers = () => {
    const pages = [];
    const maxVisiblePages = 5;
    
    if (totalPages <= maxVisiblePages) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      const startPage = Math.max(1, currentPage - 2);
      const endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
      
      for (let i = startPage; i <= endPage; i++) {
        pages.push(i);
      }
    }
    
    return pages;
  };

  if (!isOpen) return null;

  return (
    <div className="modal fade show d-block" tabIndex={-1} style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-xl">
        <div className="modal-content">
          {/* Purple Header */}
          <div className="modal-header bg-primary text-white">
            <h5 className="modal-title text-white">
              <i className="bi bi-clock-history me-2"></i>
              Execution Logs - {reportName}
            </h5>
            <button type="button" className="btn-close btn-close-white" onClick={onClose}></button>
          </div>
          <div className="modal-body">
            {loading ? (
              <div className="text-center py-4">
                <div className="spinner-border text-primary" role="status">
                  <span className="visually-hidden">Loading...</span>
                </div>
                <p className="mt-2">Loading execution logs...</p>
              </div>
            ) : logs.length === 0 ? (
              <div className="alert alert-info">
                <i className="bi bi-info-circle me-2"></i>
                No execution logs found for this report. Run the report to see execution history.
              </div>
            ) : (
              <>
                {/* Pagination Info */}
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <div className="text-muted">
                    Showing {startItem} to {endItem} of {logs.length} execution logs
                  </div>
                  <div className="text-muted">
                    Page {currentPage} of {totalPages}
                  </div>
                </div>

                {/* Table */}
                <div className="table-responsive">
                  <table className="table table-striped table-hover">
                    <thead className="table-dark">
                      <tr>
                        <th>Date & Time</th>
                        <th>Cycle</th>
                        <th>Status</th>
                        <th>Duration</th>
                        <th>Rows</th>
                        <th>Executed By</th>
                        <th>Error</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paginatedLogs.map((log) => (
                        <tr key={log.id}>
                          <td className="text-nowrap">
                            {formatDate(log.executed_at)}
                          </td>
                          <td>
                            <span className="badge bg-secondary">{log.cycle_code}</span>
                          </td>
                          <td>
                            <span className={`badge ${log.success ? 'bg-success' : 'bg-danger'}`}>
                              <i className={`bi ${log.success ? 'bi-check-circle' : 'bi-x-circle'} me-1`}></i>
                              {log.success ? 'Success' : 'Failed'}
                            </span>
                          </td>
                          <td className="text-end">
                            {formatDuration(log.execution_time_ms)}
                          </td>
                          <td className="text-end">
                            {(log.row_count !== null && log.row_count !== undefined) ? log.row_count.toLocaleString() : 'N/A'}
                          </td>
                          <td>
                            <span className="text-muted">
                              {log.executed_by || 'System'}
                            </span>
                          </td>
                          <td>
                            {log.error_message ? (
                              <span 
                                className="text-danger text-truncate d-inline-block" 
                                style={{ maxWidth: '200px' }}
                                title={log.error_message}
                              >
                                {log.error_message}
                              </span>
                            ) : (
                              <span className="text-muted">-</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination Controls */}
                {totalPages > 1 && (
                  <div className="d-flex justify-content-center align-items-center mt-3">
                    <nav aria-label="Execution logs pagination">
                      <ul className="pagination mb-0">
                        <li className={`page-item ${currentPage === 1 ? 'disabled' : ''}`}>
                          <button
                            className="page-link"
                            onClick={handlePrevious}
                            disabled={currentPage === 1}
                            title="Previous page"
                          >
                            <i className="bi bi-chevron-left"></i>
                          </button>
                        </li>
                        
                        {getPageNumbers().map((page) => (
                          <li key={page} className={`page-item ${currentPage === page ? 'active' : ''}`}>
                            <button
                              className="page-link"
                              onClick={() => handlePageChange(page)}
                            >
                              {page}
                            </button>
                          </li>
                        ))}
                        
                        <li className={`page-item ${currentPage === totalPages ? 'disabled' : ''}`}>
                          <button
                            className="page-link"
                            onClick={handleNext}
                            disabled={currentPage === totalPages}
                            title="Next page"
                          >
                            <i className="bi bi-chevron-right"></i>
                          </button>
                        </li>
                      </ul>
                    </nav>
                  </div>
                )}
              </>
            )}
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Close
            </button>
            <button 
              type="button" 
              className="btn btn-primary" 
              onClick={fetchExecutionLogs}
              disabled={loading}
            >
              <i className="bi bi-arrow-clockwise me-1"></i>
              Refresh
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExecutionLogsModal;