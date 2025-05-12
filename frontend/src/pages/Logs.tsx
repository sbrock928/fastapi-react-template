import { useState, useEffect } from 'react'
import axios from 'axios'
import LogDetailsModal from '../components/LogDetailsModal'

interface Log {
  id: number;
  timestamp: string;
  method: string;
  path: string;
  status_code: number;
  client_ip: string;
  processing_time: number;
  request_headers?: string;
  request_body?: string;
  response_body?: string;
}

const Logs = () => {
  // State
  const [allLogs, setAllLogs] = useState<Log[]>([])
  const [filteredLogs, setFilteredLogs] = useState<Log[]>([])
  const [timeRange, setTimeRange] = useState<string>('24')
  const [filterText, setFilterText] = useState<string>('')
  const [currentOffset, setCurrentOffset] = useState<number>(0)
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [selectedLog, setSelectedLog] = useState<Log | null>(null)
  const [showModal, setShowModal] = useState<boolean>(false)
  
  // Add a refresh timer state
  const [autoRefresh, setAutoRefresh] = useState<boolean>(false)
  const [refreshInterval, setRefreshInterval] = useState<number>(30) // seconds
  const [refreshTimerId, setRefreshTimerId] = useState<number | null>(null)
  
  const limit = 50
  
  // Load logs on component mount and when dependencies change
  useEffect(() => {
    loadLogs()
  }, [timeRange, currentOffset])
  
  // Filter logs when filter text or all logs change
  useEffect(() => {
    filterLogs()
  }, [filterText, allLogs])
  
  // Auto-refresh functionality
  useEffect(() => {
    if (autoRefresh) {
      const timerId = window.setInterval(() => {
        console.log('Auto-refreshing logs...')
        loadLogs()
      }, refreshInterval * 1000)
      
      setRefreshTimerId(timerId as unknown as number)
      
      return () => {
        if (refreshTimerId) {
          window.clearInterval(refreshTimerId)
        }
      }
    } else if (refreshTimerId) {
      window.clearInterval(refreshTimerId)
      setRefreshTimerId(null)
    }
  }, [autoRefresh, refreshInterval])
  
  const loadLogs = async (append = false) => {
    setIsLoading(true)
    try {
      const url = `/api/logs/?limit=${limit}&offset=${currentOffset}&hours=${timeRange}`
      const response = await axios.get(url)
      
      if (!append) {
        setAllLogs(response.data)
      } else {
        setAllLogs(prev => [...prev, ...response.data])
      }
    } catch (error) {
      console.error('Error loading logs:', error)
    } finally {
      setIsLoading(false)
    }
  }
  
  const filterLogs = () => {
    if (!filterText.trim()) {
      setFilteredLogs([...allLogs])
    } else {
      const filtered = allLogs.filter(log => 
        log.method.toLowerCase().includes(filterText.toLowerCase()) ||
        log.path.toLowerCase().includes(filterText.toLowerCase()) ||
        log.status_code.toString().includes(filterText) ||
        (log.client_ip && log.client_ip.toLowerCase().includes(filterText.toLowerCase()))
      )
      setFilteredLogs(filtered)
    }
  }
  
  const handleRefresh = () => {
    setCurrentOffset(0)
    loadLogs()
  }
  
  const handleLoadMore = () => {
    setCurrentOffset(prev => prev + limit)
    loadLogs(true)
  }
  
  const handleTimeRangeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setTimeRange(e.target.value)
    setCurrentOffset(0)
  }
  
  const handleFilterChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilterText(e.target.value)
  }
  
  const showLogDetails = async (logId: number) => {
    try {
      const response = await axios.get(`/api/logs/?limit=1&offset=0&log_id=${logId}`)
      if (response.data.length > 0) {
        setSelectedLog(response.data[0])
        setShowModal(true)
      }
    } catch (error) {
      console.error('Error fetching log details:', error)
    }
  }
  
  const handleAutoRefreshChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setAutoRefresh(e.target.checked)
  }
  
  const handleRefreshIntervalChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setRefreshInterval(parseInt(e.target.value))
  }
  
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
              placeholder="Filter logs..." 
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
      
      <div className="card mb-4">
        <div className="card-header d-flex justify-content-between align-items-center">
          <span>
            Log Entries 
            <span id="totalCount" className="badge bg-secondary ms-2">
              {filteredLogs.length} logs
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
                <th>Client IP</th>
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
                          log.status_code >= 400 ? 'bg-danger' : 
                          log.status_code >= 300 ? 'bg-warning' : 
                          'bg-success'
                        }`}
                      >
                        {log.status_code}
                      </span>
                    </td>
                    <td>{log.client_ip || 'unknown'}</td>
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
          {filteredLogs.length >= limit && (
            <button 
              id="loadMoreBtn" 
              className="btn btn-outline-primary"
              onClick={handleLoadMore}
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                  <span className="ms-2">Loading...</span>
                </>
              ) : (
                'Load More Logs'
              )}
            </button>
          )}
          <small className="text-muted">
            Showing logs from {new Date(Date.now() - parseInt(timeRange) * 60 * 60 * 1000).toLocaleString()}
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
  )
}

export default Logs
