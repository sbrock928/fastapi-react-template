import React, { useState, useEffect } from 'react';
import { reportsApi } from '@/services/api';
import type { ScheduledReport } from '@/types';

interface ScheduledReportsCardProps {
  userId?: number;
  refreshTrigger?: number;
  onEditSchedule: (schedule: ScheduledReport) => void;
}

const ScheduledReportsCard: React.FC<ScheduledReportsCardProps> = ({
  userId,
  refreshTrigger = 0,
  onEditSchedule
}) => {
  const [schedules, setSchedules] = useState<ScheduledReport[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSchedules = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await reportsApi.getScheduledReports(userId);
        setSchedules(response.data);
      } catch (err) {
        console.error('Error fetching scheduled reports:', err);
        setError('Failed to load scheduled reports');
      } finally {
        setLoading(false);
      }
    };

    fetchSchedules();
  }, [userId, refreshTrigger]);

  const handleToggleActive = async (schedule: ScheduledReport) => {
    try {
      await reportsApi.updateScheduledReport(schedule.id, {
        is_active: !schedule.is_active
      });
      
      // Update local state
      setSchedules(prevSchedules => 
        prevSchedules.map(s => 
          s.id === schedule.id 
            ? { ...s, is_active: !s.is_active } 
            : s
        )
      );
    } catch (err) {
      console.error('Error toggling schedule status:', err);
      alert('Failed to update schedule status');
    }
  };

  const handleDelete = async (scheduleId: number) => {
    if (!window.confirm('Are you sure you want to delete this scheduled report?')) {
      return;
    }
    
    try {
      await reportsApi.deleteScheduledReport(scheduleId);
      
      // Update local state
      setSchedules(prevSchedules => 
        prevSchedules.filter(s => s.id !== scheduleId)
      );
    } catch (err) {
      console.error('Error deleting scheduled report:', err);
      alert('Failed to delete scheduled report');
    }
  };

  const formatSchedule = (schedule: ScheduledReport): string => {
    const time = schedule.time_of_day;
    
    switch (schedule.frequency) {
      case 'DAILY':
        return `Daily at ${time}`;
      case 'WEEKLY':
        return `Weekly on ${schedule.day_of_week?.toLowerCase()} at ${time}`;
      case 'MONTHLY':
        return `Monthly on day ${schedule.day_of_month} at ${time}`;
      default:
        return `${schedule.frequency} at ${time}`;
    }
  };

  return (
    <div className="card mb-4">
      <div className="card-header bg-warning text-dark d-flex justify-content-between align-items-center">
        <h5 className="card-title mb-0">Scheduled Reports</h5>
      </div>
      <div className="card-body">
        {loading ? (
          <div className="text-center py-4">
            <div className="spinner-border text-primary" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
            <p className="mt-2">Loading scheduled reports...</p>
          </div>
        ) : error ? (
          <div className="alert alert-danger">{error}</div>
        ) : schedules.length === 0 ? (
          <div className="alert alert-info">No scheduled reports found.</div>
        ) : (
          <div className="table-responsive">
            <table className="table table-striped table-hover">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Report</th>
                  <th>Schedule</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {schedules.map(schedule => (
                  <tr key={schedule.id}>
                    <td>{schedule.name}</td>
                    <td>{schedule.report_name || `Report ${schedule.report_id}`}</td>
                    <td>{formatSchedule(schedule)}</td>
                    <td>
                      <div className="form-check form-switch">
                        <input
                          className="form-check-input"
                          type="checkbox"
                          checked={schedule.is_active}
                          onChange={() => handleToggleActive(schedule)}
                          id={`schedule-toggle-${schedule.id}`}
                        />
                        <label className="form-check-label" htmlFor={`schedule-toggle-${schedule.id}`}>
                          {schedule.is_active ? 'Active' : 'Inactive'}
                        </label>
                      </div>
                    </td>
                    <td>
                      <div className="btn-group btn-group-sm">
                        <button
                          className="btn btn-outline-primary"
                          onClick={() => onEditSchedule(schedule)}
                          title="Edit Schedule"
                        >
                          <i className="bi bi-pencil"></i>
                        </button>
                        <button
                          className="btn btn-outline-danger"
                          onClick={() => handleDelete(schedule.id)}
                          title="Delete Schedule"
                        >
                          <i className="bi bi-trash"></i>
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

export default ScheduledReportsCard;
