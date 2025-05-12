import { useState, useEffect } from 'react';
import { logsApi } from '@/services/api';
import LogDetailsModal from '@/components/LogDetailsModal';
import StatusDistributionChart from '@/components/StatusDistributionChart';
import type { Log, StatusDistribution } from '@/types';

const Logs = () => {
  // State
  const [allLogs, setAllLogs] = useState<Log[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<Log[]>([]);
  const [timeRange, setTimeRange] = useState<string>('24');
  const [filterText, setFilterText] = useState<string>('');
  const [currentOffset, setCurrentOffset] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [selectedLog, setSelectedLog] = useState<Log | null>(null);
  const [showModal, setShowModal] = useState<boolean>(false);
  
  // Add a refresh timer state
  const [autoRefresh, setAutoRefresh] = useState<boolean>(false);
  const [refreshInterval, setRefreshInterval] = useState<number>(30); // seconds
  const [refreshTimerId, setRefreshTimerId] = useState<number | null>(null);
  
  // Add status distribution states
  const [statusDistribution, setStatusDistribution] = useState<StatusDistribution[]>([]);
  const [selectedStatusCategory, setSelectedStatusCategory] = useState<string | null>(null);
  const [loadingDistribution, setLoadingDistribution] = useState<boolean>(false);
  
  const limit = 50;
  // Add pagination state
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pagesCount, setPagesCount] = useState<number>(1);
  // Add state to track total log count
  const [totalCount, setTotalCount] = useState<number>(0);

  // Load logs on component mount and when dependencies change
  useEffect(() => {
    loadLogs();
    loadStatusDistribution();
  }, [timeRange, currentOffset]);
  
  // Filter logs when filter text, selected status category, or all logs change
  useEffect(() => {
    filterLogs();
  }, [filterText, selectedStatusCategory, allLogs]);
  
  // Auto-refresh functionality
  useEffect(() => {
    if (autoRefresh) {
      const timerId = window.setInterval(() => {
        console.log('Auto-refreshing logs...');
        loadLogs();
        loadStatusDistribution();
      }, refreshInterval * 1000);
      
      setRefreshTimerId(timerId as unknown as number);
      
      return () => {
        if (refreshTimerId) {
          window.clearInterval(refreshTimerId);
        }
      };
    } else if (refreshTimerId) {
      window.clearInterval(refreshTimerId);
      setRefreshTimerId(null);
    }
  }, [autoRefresh, refreshInterval]);
  
  const loadLogs = async (append = false) => {
    setIsLoading(true);
    try {
      // Build the URL with status filter if present
      const params: Record<string, string | number> = {
        limit,
        offset: currentOffset,
        hours: timeRange
      };
      
      // Add status code filter based on selected category
      if (selectedStatusCategory) {
        if (selectedStatusCategory === "Success") {
          params.status_min = 200;
          params.status_max = 299;
        } else if (selectedStatusCategory === "Redirection") {
          params.status_min = 300;
          params.status_max = 399;
        } else if (selectedStatusCategory === "Client Error") {
          params.status_min = 400;
          params.status_max = 499;
        } else if (selectedStatusCategory === "Server Error") {
          params.status_min = 500;
          params.status_max = 599;
        }
      }
      
      const response = await logsApi.getLogs(params);
      
      // Get total count from headers or response data
      const totalCount = parseInt(response.headers['x-total-count'] || '0');
      if (totalCount > 0) {
        setPagesCount(Math.ceil(totalCount / limit));
        setTotalCount(totalCount); // Store the total count
      }
      
      // Assign status category to each log
      const logsWithCategory = response.data.map((log: Log) => {
        const status = log.status_code;
        let statusCategory: string;
        
        if (status >= 500) statusCategory = "Server Error";
        else if (status >= 400) statusCategory = "Client Error";
        else if (status >= 300) statusCategory = "Redirection";
        else if (status >= 200) statusCategory = "Success";
        else statusCategory = "Unknown";
        
        return {...log, status_category: statusCategory};
      });
      
      if (!append) {
        setAllLogs(logsWithCategory);
        setFilteredLogs(logsWithCategory); // Set filtered logs directly
      } else {
        const newLogs = [...allLogs, ...logsWithCategory];
        setAllLogs(newLogs);
        setFilteredLogs(newLogs); // Set filtered logs directly
      }
    } catch (error) {
      console.error('Error loading logs:', error);
    } finally {
      setIsLoading(false);
    }
  };
  
  const loadStatusDistribution = async () => {
    setLoadingDistribution(true);
    try {
      const response = await logsApi.getStatusDistribution(timeRange);
      if (response.data && response.data.status_distribution) {
        setStatusDistribution(response.data.status_distribution);
      } else {
        console.error('Invalid response format:', response.data);
        setStatusDistribution([]);
      }
    } catch (error) {
      console.error('Error loading status distribution:', error);
      setStatusDistribution([]);
    } finally {
      setLoadingDistribution(false);
    }
  };
  
  // Modify filterLogs to include searching by username
  const filterLogs = () => {
    // Only filter by text since status filtering is now server-side
    if (!filterText.trim()) {
      setFilteredLogs([...allLogs]);
    } else {
      const filtered = allLogs.filter(log => 
        log.method.toLowerCase().includes(filterText.toLowerCase()) ||
        log.path.toLowerCase().includes(filterText.toLowerCase()) ||
        log.status_code.toString().includes(filterText) ||
        (log.client_ip && log.client_ip.toLowerCase().includes(filterText.toLowerCase())) ||
        (log.username && log.username.toLowerCase().includes(filterText.toLowerCase())) ||
        (log.hostname && log.hostname.toLowerCase().includes(filterText.toLowerCase()))
      );
      setFilteredLogs(filtered);
    }
  };

  const handleRefresh = () => {
    setCurrentOffset(0);
    loadLogs();
    loadStatusDistribution();
  };

  const handleTimeRangeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setTimeRange(e.target.value);
    setCurrentOffset(0);
  };

  const handleFilterChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilterText(e.target.value);
  };

  const handleStatusCategoryClick = (statusCategory: string) => {
    setCurrentOffset(0); // Reset pagination
    if (selectedStatusCategory === statusCategory) {
      // If clicking the already selected category, clear the filter
      setSelectedStatusCategory(null);
    } else {
      setSelectedStatusCategory(statusCategory);
    }
  };

  const showLogDetails = async (logId: number) => {
    try {
      const response = await logsApi.getLogDetail(logId);
      if (response.data.length > 0) {
        setSelectedLog(response.data[0]);
        setShowModal(true);
      }
    } catch (error) {
      console.error('Error fetching log details:', error);
    }
  };

  const handleAutoRefreshChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setAutoRefresh(e.target.checked);
  };

  const handleRefreshIntervalChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setRefreshInterval(parseInt(e.target.value));
  };

  // Add useEffect to reload logs when selectedStatusCategory changes
  useEffect(() => {
    if (currentOffset === 0) {
      loadLogs();
    } else {
      setCurrentOffset(0); // This will trigger loadLogs via the other useEffect
    }
  }, [selectedStatusCategory]);

  const handlePageChange = (page: number) => {
    if (page < 1 || page > pagesCount || page === currentPage) {
      return;
    }
    setCurrentPage(page);
    setCurrentOffset((page - 1) * limit);
    // Logs will be loaded by the useEffect that watches currentOffset
  };

  const handleFirstPage = () => {
    if (currentPage !== 1) {
      setCurrentPage(1);
      setCurrentOffset(0);
    }
  };

  const handlePreviousPage = () => {
    if (currentPage > 1) {
      const newPage = currentPage - 1;
      setCurrentPage(newPage);
      setCurrentOffset((newPage - 1) * limit);
    }
  };

  const handleNextPage = () => {
    if (currentPage < pagesCount) {
      const newPage = currentPage + 1;
      setCurrentPage(newPage);
      setCurrentOffset((newPage - 1) * limit);
    }
  };

  const handleLastPage = () => {
    if (currentPage !== pagesCount) {
      setCurrentPage(pagesCount);
      setCurrentOffset((pagesCount - 1) * limit);
    }
  };

  // Generate pagination items
  const renderPaginationItems = () => {
    const items = [];
    const maxVisiblePages = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(pagesCount, startPage + maxVisiblePages - 1);
    // Adjust if we're near the end
    if (endPage - startPage + 1 < maxVisiblePages) {
      startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }
    // First ellipsis
    if (startPage > 1) {
      items.push(
        <li key="start-ellipsis" className="page-item disabled">
          <span className="page-link">...</span>
        </li>
      );
    }
    // Page numbers
    for (let i = startPage; i <= endPage; i++) {
      items.push(
        <li key={i} className={`page-item ${currentPage === i ? 'active' : ''}`}>
          <button 
            className="page-link" 
            onClick={() => handlePageChange(i)}
            disabled={currentPage === i}
          >
            {i}
          </button>
        </li>
      );
    }
    // Last ellipsis
    if (endPage < pagesCount) {
      items.push(
        <li key="end-ellipsis" className="page-item disabled">
          <span className="page-link">...</span>
        </li>
      );
    }
    return items;
  };

  // Update useEffect to also update current page when currentOffset changes
  useEffect(() => {
    const newPage = Math.floor(currentOffset / limit) + 1;
    if (newPage !== currentPage) {
      setCurrentPage(newPage);
    }
  }, [currentOffset]);

  return (
    <div>
      <h1>System Logs</h1>
      <p>View and filter system logs and API requests.</p>
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
            onClick={handleRefresh}
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
              placeholder="Filter by path, status, user, etc..." 
              value={filterText}
              onChange={handleFilterChange}
            />
            {filterText && (
              <button 
                className="btn btn-outline-secondary" 
                type="button"
                onClick={() => setFilterText('')}
              >
                <i className="bi bi-x"></i>
              </button>
            )}
          </div>
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
            onClick={() => setSelectedStatusCategory(null)}
          >
            Clear Filter
          </button>
        </div>
      )}
      <div className="card mb-4">
        <div className="card-header d-flex justify-content-between align-items-center">
          <span>
            Log Entries
            <span id="totalCount" className="badge bg-secondary ms-2">
              {totalCount > 0 ? `${totalCount} total` : 'No'} logs
              {filterText && ` (${filteredLogs.length} shown)`}
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
                <th>Method</th>
                <th>Path</th>
                <th>Status</th>
                <th>Client IP / User</th>
                <th>Processing Time</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="logsTableBody">
              {isLoading && currentOffset === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-4">
                    <div className="spinner-border text-primary" role="status">
                      <span className="visually-hidden">Loading...</span>
                    </div>
                    <p className="mt-2">Loading logs...</p>
                  </td>
                </tr>
              ) : filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-4">
                    No logs found. Try changing your filter or time range.
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log) => (
                  <tr key={log.id}>
                    <td>{new Date(log.timestamp).toLocaleString()}</td>
                    <td><span className="badge bg-primary">{log.method}</span></td>
                    <td>{log.path}</td>
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
                    <td>
                      {log.client_ip || 'unknown'}
                      {log.username && (
                        <div className="small text-muted">
                          <i className="bi bi-person-circle me-1"></i>
                          {log.username}
                        </div>
                      )}
                    </td>
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
        <div className="card-footer d-flex justify-content-between align-items-center">
          <nav aria-label="Log pagination">
            <ul className="pagination mb-0">
              <li className={`page-item ${currentPage === 1 ? 'disabled' : ''}`}>
                <button className="page-link" onClick={handleFirstPage} disabled={currentPage === 1 || isLoading}>
                  <i className="bi bi-chevron-double-left"></i>
                </button>
              </li>
              <li className={`page-item ${currentPage === 1 ? 'disabled' : ''}`}>
                <button className="page-link" onClick={handlePreviousPage} disabled={currentPage === 1 || isLoading}>
                  <i className="bi bi-chevron-left"></i>
                </button>
              </li>
              {renderPaginationItems()}
              <li className={`page-item ${currentPage === pagesCount ? 'disabled' : ''}`}>
                <button className="page-link" onClick={handleNextPage} disabled={currentPage === pagesCount || isLoading}>
                  <i className="bi bi-chevron-right"></i>
                </button>
              </li>
              <li className={`page-item ${currentPage === pagesCount ? 'disabled' : ''}`}>
                <button className="page-link" onClick={handleLastPage} disabled={currentPage === pagesCount || isLoading}>
                  <i className="bi bi-chevron-double-right"></i>
                </button>
              </li>
            </ul>
          </nav>
          <small className="text-muted d-none d-md-block">
            Showing logs from {new Date(Date.now() - parseInt(timeRange) * 60 * 60 * 1000).toLocaleString()}
            {selectedStatusCategory && ` filtered by ${selectedStatusCategory} status`}
            <br />
            Page {currentPage} of {pagesCount} ({filteredLogs.length} of {totalCount} logs)
          </small>
        </div>
      </div>
      {selectedLog && (
        <LogDetailsModal 
          log={selectedLog}
          show={showModal}
          onHide={() => setShowModal(false)}
        />
      )}
    </div>
  );
};

export default Logs;
