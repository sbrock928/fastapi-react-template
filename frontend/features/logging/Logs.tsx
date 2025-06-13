// frontend/features/logging/LogsRefactored.tsx
import { LogDetailsModal, StatusDistributionChart } from './components';
import { formatDateTime } from '@/utils';
import {
  useLogsData,
  useLogsAutoRefresh,
  useLogsStatusDistribution,
  useLogsModal,
  useLogsFiltering,
  useLogsPagination
} from './hooks';

const Logs = () => {
  // Filtering and control state
  const {
    timeRange,
    filterText,
    currentOffset,
    handleTimeRangeChange,
    handleFilterChange,
    clearFilter,
    handleRefresh,
    updateOffset
  } = useLogsFiltering({
    onOffsetChange: () => {},
    onStatusCategoryChange: () => {}
  });

  // Status distribution management
  const {
    statusDistribution,
    selectedStatusCategory,
    loadingDistribution,
    handleStatusCategoryClick,
    clearStatusFilter
  } = useLogsStatusDistribution({ timeRange });

  // Data management with all filters
  const {
    filteredLogs,
    isLoading,
    totalCount,
    serverFilterActive,
    limit,
    refreshLogs
  } = useLogsData({
    timeRange,
    currentOffset,
    selectedStatusCategory,
    filterText
  });

  // Auto-refresh functionality
  const {
    autoRefresh,
    refreshInterval,
    handleAutoRefreshChange,
    handleRefreshIntervalChange
  } = useLogsAutoRefresh({
    onRefresh: () => {
      refreshLogs();
      // Also refresh status distribution
      // loadStatusDistribution(); // This is handled automatically by the hook
    }
  });

  // Modal management
  const {
    selectedLog,
    showModal,
    showLogDetails,
    handleModalClose
  } = useLogsModal();

  // Pagination management
  const {
    currentPage,
    totalPages,
    paginationItems,
    handlePageChange,
    goToFirstPage,
    goToPreviousPage,
    goToNextPage,
    goToLastPage,
    getPaginationInfo
  } = useLogsPagination({
    totalCount,
    limit,
    currentOffset,
    onOffsetChange: updateOffset
  });

  // Combined refresh function
  const handleCombinedRefresh = () => {
    handleRefresh();
    refreshLogs();
  };

  return (
    <div>
      <h3>System Logs</h3>
      <p>View and filter system logs and API requests.</p>
      
      {/* Controls Section */}
      <div className="row mb-4">
        <div className="col-md-8 d-flex gap-2 align-items-center">
          <select 
            id="timeRangeSelect" 
            className="form-select" 
            style={{width: 'auto'}}
            value={timeRange}
            onChange={handleTimeRangeChange}
          >
            <option value="1">Last Hour</option>
            <option value="6">Last 6 Hours</option>
            <option value="24">Last 24 Hours</option>
            <option value="72">Last 3 Days</option>
            <option value="168">Last Week</option>
          </select>
          
          <button 
            id="refreshLogs" 
            className="btn btn-primary"
            onClick={handleCombinedRefresh}
          >
            <i className="bi bi-arrow-clockwise"></i> Refresh
          </button>
          
          {/* Auto refresh controls */}
          <div className="form-check ms-3">
            <input 
              type="checkbox"
              className="form-check-input"
              id="autoRefreshCheck"
              checked={autoRefresh}
              onChange={handleAutoRefreshChange}
            />
            <label className="form-check-label" htmlFor="autoRefreshCheck">
              Auto-refresh
            </label>
          </div>
          
          <select
            id="refreshIntervalSelect"
            className="form-select ms-2"
            style={{width: 'auto'}}
            value={refreshInterval}
            onChange={handleRefreshIntervalChange}
            disabled={!autoRefresh}
          >
            <option value="10">10 seconds</option>
            <option value="30">30 seconds</option>
            <option value="60">1 minute</option>
            <option value="300">5 minutes</option>
          </select>
        </div>
        
        <div className="col-md-4">
          <div className="input-group">
            <span className="input-group-text">
              <i className="bi bi-search"></i>
            </span>
            <input 
              type="text" 
              id="logFilterInput" 
              className="form-control" 
              placeholder="Search logs (path, method, status, user)..." 
              value={filterText}
              onChange={handleFilterChange}
            />
            {filterText && (
              <button 
                className="btn btn-outline-secondary" 
                type="button"
                onClick={clearFilter}
              >
                <i className="bi bi-x"></i>
              </button>
            )}
          </div>
          {serverFilterActive && (
            <div className="text-muted small mt-1">
              <i className="bi bi-funnel-fill me-1"></i> 
              Filter applied on server
            </div>
          )}
        </div>
      </div>
      
      {/* Status Distribution Chart */}
      {loadingDistribution ? (
        <div className="card mb-4">
          <div className="card-body text-center py-4">
            <div className="spinner-border text-primary" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
            <p className="mt-2">Loading status distribution...</p>
          </div>
        </div>
      ) : statusDistribution.length > 0 ? (
        <StatusDistributionChart 
          distribution={statusDistribution} 
          onStatusClick={handleStatusCategoryClick} 
        />
      ) : null}
      
      {/* Active filter indicators */}
      {selectedStatusCategory && (
        <div className="alert alert-info d-flex align-items-center mb-4">
          <span>
            <i className="bi bi-funnel-fill me-2"></i>
            Filtering by status: <strong>{selectedStatusCategory}</strong>
          </span>
          <button 
            className="btn btn-sm btn-outline-info ms-auto"
            onClick={clearStatusFilter}
          >
            Clear Filter
          </button>
        </div>
      )}
      
      {/* Logs Table */}
      <div className="card mb-4">
        <div className="card-header bg-primary text-white d-flex justify-content-between align-items-center">
          <span>
            Log Entries
            <span id="totalCount" className="badge bg-secondary ms-2">
              {totalCount > 0 ? `${totalCount} total` : 'No'} logs
              {serverFilterActive && ` (filtered)`}
            </span>
            {autoRefresh && (
              <span className="badge bg-info ms-2">
                <i className="bi bi-arrow-repeat me-1"></i>
                Auto-refreshing
              </span>
            )}
          </span>
        </div>
        
        <div className="card-body table-responsive">
          <table className="table table-striped table-hover">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>App ID</th>
                <th>User</th>
                <th>Status</th>
                <th>Method</th>
                <th>Path</th>
                <th>Processing Time</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="logsTableBody">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="text-center py-4">
                    <div className="spinner-border text-primary" role="status">
                      <span className="visually-hidden">Loading...</span>
                    </div>
                    <p className="mt-2">Loading logs...</p>
                  </td>
                </tr>
              ) : filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-4">
                    No logs found. Try changing your filter or time range.
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log) => (
                  <tr key={log.id}>
                    <td>{formatDateTime(log.timestamp)}</td>
                    <td>{log.application_id || 'N/A'}</td>
                    <td>
                      {log.username ? (
                        <span>{log.username}</span>
                      ) : '-'}
                    </td>
                    <td>
                      <span 
                        className={`badge ${
                          log.status_code >= 500 ? 'bg-danger' : 
                          log.status_code >= 400 ? 'bg-warning text-dark' : 
                          log.status_code >= 300 ? 'bg-info text-dark' : 
                          'bg-success'
                        }`}
                      >
                        {log.status_code}
                      </span>
                    </td>
                    <td><span className="badge bg-primary">{log.method}</span></td>
                    <td>{log.path}</td>
                    <td>{log.processing_time ? `${log.processing_time.toFixed(2)} ms` : 'N/A'}</td>
                    <td>
                      <button 
                        className="btn btn-sm btn-outline-secondary"
                        onClick={() => showLogDetails(log.id)}
                      >
                        Details
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {/* Pagination Footer */}
        <div className="card-footer d-flex justify-content-between align-items-center">
          <nav aria-label="Log pagination">
            <ul className="pagination mb-0">
              <li className={`page-item ${currentPage === 1 ? 'disabled' : ''}`}>
                <button 
                  className="page-link" 
                  onClick={goToFirstPage} 
                  disabled={currentPage === 1 || isLoading}
                >
                  <i className="bi bi-chevron-double-left"></i>
                </button>
              </li>
              <li className={`page-item ${currentPage === 1 ? 'disabled' : ''}`}>
                <button 
                  className="page-link" 
                  onClick={goToPreviousPage} 
                  disabled={currentPage === 1 || isLoading}
                >
                  <i className="bi bi-chevron-left"></i>
                </button>
              </li>
              
              {/* Dynamic page numbers */}
              {paginationItems.map((item) => {
                if (item.type === 'ellipsis') {
                  return (
                    <li key={item.key} className="page-item disabled">
                      <span className="page-link">{item.label}</span>
                    </li>
                  );
                } else {
                  return (
                    <li key={item.key} className={`page-item ${item.active ? 'active' : ''}`}>
                      <button
                        className="page-link"
                        onClick={() => handlePageChange(item.page!)}
                        disabled={item.disabled}
                      >
                        {item.label}
                      </button>
                    </li>
                  );
                }
              })}
              
              <li className={`page-item ${currentPage === totalPages ? 'disabled' : ''}`}>
                <button 
                  className="page-link" 
                  onClick={goToNextPage} 
                  disabled={currentPage === totalPages || isLoading}
                >
                  <i className="bi bi-chevron-right"></i>
                </button>
              </li>
              <li className={`page-item ${currentPage === totalPages ? 'disabled' : ''}`}>
                <button 
                  className="page-link" 
                  onClick={goToLastPage} 
                  disabled={currentPage === totalPages || isLoading}
                >
                  <i className="bi bi-chevron-double-right"></i>
                </button>
              </li>
            </ul>
          </nav>
          
          <small className="text-muted d-none d-md-block">
            Showing logs from {new Date(Date.now() - parseInt(timeRange) * 60 * 60 * 1000).toLocaleString()}
            {selectedStatusCategory && ` filtered by ${selectedStatusCategory} status`}
            {serverFilterActive && ` with search: "${filterText}"`}
            <br />
            Page {currentPage} of {totalPages} ({getPaginationInfo()})
          </small>
        </div>
      </div>
      
      {/* Log Details Modal */}
      {selectedLog && (
        <LogDetailsModal 
          log={selectedLog}
          show={showModal}
          onHide={handleModalClose}
        />
      )}
    </div>
  );
};

export default Logs;