import React, { useState, useEffect } from 'react';
import { reportsApi } from '@/services/api';
import type { ReportExecution } from '@/types';

interface ReportExecutionsCardProps {
  reportId?: number;
  userId?: number;
  refreshTrigger?: number;
}

const ReportExecutionsCard: React.FC<ReportExecutionsCardProps> = ({ 
  reportId, 
  userId,
  refreshTrigger = 0
}) => {
  const [executions, setExecutions] = useState<ReportExecution[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'recent' | 'all'>('recent');

  useEffect(() => {
    const fetchExecutions = async () => {
      setLoading(true);
      setError(null);
      try {
        const params: any = { limit: 20 };
        if (reportId) params.report_id = reportId;
        if (userId) params.user_id = userId;
        
        const response = await reportsApi.getReportExecutions(params);
        setExecutions(response.data);
      } catch (err) {
        console.error('Error fetching report executions:', err);
        setError('Failed to load report executions');
      } finally {
        setLoading(false);
      }
    };

    fetchExecutions();
  }, [reportId, userId, refreshTrigger]);

  const getStatusBadgeClass = (status: string): string => {
    switch (status) {
      case 'COMPLETED':
        return 'bg-success';
      case 'RUNNING':
        return 'bg-primary';
      case 'QUEUED':
        return 'bg-info';
      case 'FAILED':
        return 'bg-danger';
      default:
        return 'bg-secondary';
    }
  };

  const formatDate = (dateStr?: string): string => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleString();
  };

  const handleDownload = (execution: ReportExecution) => {
    // In a real implementation, this would download the report file
    // For now, just alert with the file path
    alert(`Downloading report from: ${execution.result_path}`);
  };

  const handleViewDetails = (execution: ReportExecution) => {
    // In a real implementation, this would show a modal with execution details
    alert(`Execution details:\n${JSON.stringify(execution, null, 2)}`);
  };

  const filteredExecutions = executions.filter(exec => {
    if (activeTab === 'recent') {
      // Filter to only show recent executions (last 7 days)
      const sevenDaysAgo = new Date();
      sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
      return new Date(exec.started_at || '') > sevenDaysAgo;
    }
    return true;
  });

  return (
    <div className="card mb-4">
      <div className="card-header bg-info text-white d-flex justify-content-between align-items-center">
        <h5 className="card-title mb-0">Report Executions</h5>
        <div className="nav nav-tabs card-header-tabs">
          <div className="nav-item">
            <button 
              className={`nav-link ${activeTab === 'recent' ? 'active bg-white text-info' : 'text-white'}`}
              onClick={() => setActiveTab('recent')}
            >
              Recent
            </button>
          </div>
          <div className="nav-item">
            <button 
              className={`nav-link ${activeTab === 'all' ? 'active bg-white text-info' : 'text-white'}`}
              onClick={() => setActiveTab('all')}
            >
              All
            </button>
          </div>
        </div>
      </div>
      <div className="card-body">
        {loading ? (
          <div className="text-center py-4">
            <div className="spinner-border text-primary" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
            <p className="mt-2">Loading executions...</p>
          </div>
        ) : error ? (
          <div className="alert alert-danger">{error}</div>
        ) : filteredExecutions.length === 0 ? (
          <div className="alert alert-info">No report executions found.</div>
        ) : (
          <div className="table-responsive">
            <table className="table table-striped table-hover">
              <thead>
                <tr>
                  <th>Report</th>
                  <th>Status</th>
                  <th>Started At</th>
                  <th>Completed At</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredExecutions.map(execution => (
                  <tr key={execution.id}>
                    <td>{execution.report_name || `Report ${execution.report_id}`}</td>
                    <td>
                      <span className={`badge ${getStatusBadgeClass(execution.status)}`}>
                        {execution.status}
                      </span>
                    </td>
                    <td>{formatDate(execution.started_at)}</td>
                    <td>{formatDate(execution.completed_at)}</td>
                    <td>
                      <div className="btn-group btn-group-sm">
                        {execution.status === 'COMPLETED' && execution.result_path && (
                          <button 
                            className="btn btn-outline-success"
                            onClick={() => handleDownload(execution)}
                            title="Download Report"
                          >
                            <i className="bi bi-download"></i>
                          </button>
                        )}
                        <button 
                          className="btn btn-outline-info"
                          onClick={() => handleViewDetails(execution)}
                          title="View Details"
                        >
                          <i className="bi bi-info-circle"></i>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReportExecutionsCard;
