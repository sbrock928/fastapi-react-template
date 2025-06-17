import React, { useState, useEffect, useRef, useCallback } from 'react';
import { reportingApi } from '@/services/api';
import { useToast } from '@/context/ToastContext';
import useModal from '@/hooks/useModal';
import type { ReportExecutionLog } from '@/types/reporting';
import styles from '@/styles/components/ExecutionLogsModal.module.css';

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
  const { showToast } = useToast();
  const modalMounted = useRef(false);
  const { modalRef, closeModal } = useModal(isOpen, onClose);

  // Mark when modal is mounted
  useEffect(() => {
    modalMounted.current = true;
    return () => {
      modalMounted.current = false;
    };
  }, []);

  useEffect(() => {
    if (isOpen && reportId) {
      fetchExecutionLogs();
    }
  }, [isOpen, reportId]);

  // Handle modal container click to isolate its event bubble
  const handleModalClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
  }, []);

  // Handle manual close of the modal
  const handleClose = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    closeModal();
  }, [closeModal]);

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

  if (!reportId) return null;

  return (
    <div 
      className={`modal fade ${styles.modal}`}
      tabIndex={-1}
      aria-labelledby="executionLogsModalLabel"
      aria-hidden="true"
      ref={modalRef}
      onClick={handleModalClick}
      data-bs-backdrop="static"
      data-bs-keyboard="false"
    >
      <div className={`modal-dialog modal-xl ${styles.modalDialog}`}>
        <div className={`modal-content ${styles.modalContent}`}>
          <div className={`modal-header ${styles.modalHeader}`}>
            <h5 className="modal-title" id="executionLogsModalLabel">
              <i className="bi bi-clock-history me-2"></i>
              Execution Logs - {reportName}
            </h5>
            <button 
              type="button" 
              className={`btn-close ${styles.closeButton}`}
              onClick={handleClose}
              aria-label="Close"
            ></button>
          </div>
          <div className={`modal-body ${styles.modalBody}`}>
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
              <div className={`table-responsive ${styles.tableContainer}`}>
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
                    {logs.map((log) => (
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
            )}
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={handleClose}>
              Close
            </button>
            <button 
              type="button" 
              className={`btn btn-primary ${styles.refreshButton}`}
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