import React, { useState } from 'react';
import type { ScheduledReport } from '@/types';

interface ScheduleReportModalProps {
  show: boolean;
  reportId: number;
  reportName: string;
  onHide: () => void;
  onSave: (scheduledReport: Partial<ScheduledReport>) => void;
}

const ScheduleReportModal: React.FC<ScheduleReportModalProps> = ({
  show,
  reportId,
  reportName,
  onHide,
  onSave
}) => {
  const [frequency, setFrequency] = useState<'DAILY' | 'WEEKLY' | 'MONTHLY'>('DAILY');
  const [dayOfWeek, setDayOfWeek] = useState<string>('MONDAY');
  const [dayOfMonth, setDayOfMonth] = useState<number>(1);
  const [timeOfDay, setTimeOfDay] = useState<string>('08:00');
  const [name, setName] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  
  const resetForm = () => {
    setFrequency('DAILY');
    setDayOfWeek('MONDAY');
    setDayOfMonth(1);
    setTimeOfDay('08:00');
    setName('');
    setDescription('');
  };
  
  const handleClose = () => {
    resetForm();
    onHide();
  };
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const scheduledReport: Partial<ScheduledReport> = {
      report_id: reportId,
      name: name || `Scheduled ${reportName}`,
      description,
      frequency,
      time_of_day: timeOfDay,
      is_active: true,
      parameters: {} // This should be populated with the current report parameters
    };
    
    if (frequency === 'WEEKLY') {
      scheduledReport.day_of_week = dayOfWeek as any;
    } else if (frequency === 'MONTHLY') {
      scheduledReport.day_of_month = dayOfMonth;
    }
    
    onSave(scheduledReport);
    handleClose();
  };
  
  if (!show) return null;
  
  return (
    <div className="modal fade show" style={{ display: 'block' }} tabIndex={-1}>
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header bg-primary text-white">
            <h5 className="modal-title">Schedule Report: {reportName}</h5>
            <button type="button" className="btn-close btn-close-white" onClick={handleClose}></button>
          </div>
          <div className="modal-body">
            <form onSubmit={handleSubmit}>
              <div className="mb-3">
                <label htmlFor="scheduleName" className="form-label">Schedule Name</label>
                <input 
                  type="text" 
                  className="form-control" 
                  id="scheduleName" 
                  value={name} 
                  onChange={(e) => setName(e.target.value)}
                  placeholder={`Scheduled ${reportName}`}
                />
              </div>
              
              <div className="mb-3">
                <label htmlFor="scheduleDescription" className="form-label">Description (Optional)</label>
                <textarea 
                  className="form-control" 
                  id="scheduleDescription" 
                  value={description} 
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                />
              </div>
              
              <div className="mb-3">
                <label htmlFor="frequency" className="form-label">Frequency</label>
                <select 
                  className="form-select" 
                  id="frequency"
                  value={frequency}
                  onChange={(e) => setFrequency(e.target.value as any)}
                  required
                >
                  <option value="DAILY">Daily</option>
                  <option value="WEEKLY">Weekly</option>
                  <option value="MONTHLY">Monthly</option>
                </select>
              </div>
              
              {frequency === 'WEEKLY' && (
                <div className="mb-3">
                  <label htmlFor="dayOfWeek" className="form-label">Day of Week</label>
                  <select 
                    className="form-select" 
                    id="dayOfWeek"
                    value={dayOfWeek}
                    onChange={(e) => setDayOfWeek(e.target.value)}
                    required
                  >
                    <option value="MONDAY">Monday</option>
                    <option value="TUESDAY">Tuesday</option>
                    <option value="WEDNESDAY">Wednesday</option>
                    <option value="THURSDAY">Thursday</option>
                    <option value="FRIDAY">Friday</option>
                    <option value="SATURDAY">Saturday</option>
                    <option value="SUNDAY">Sunday</option>
                  </select>
                </div>
              )}
              
              {frequency === 'MONTHLY' && (
                <div className="mb-3">
                  <label htmlFor="dayOfMonth" className="form-label">Day of Month</label>
                  <select 
                    className="form-select" 
                    id="dayOfMonth"
                    value={dayOfMonth}
                    onChange={(e) => setDayOfMonth(parseInt(e.target.value))}
                    required
                  >
                    {Array.from({ length: 31 }, (_, i) => i + 1).map(day => (
                      <option key={day} value={day}>{day}</option>
                    ))}
                  </select>
                </div>
              )}
              
              <div className="mb-3">
                <label htmlFor="timeOfDay" className="form-label">Time of Day</label>
                <input 
                  type="time" 
                  className="form-control" 
                  id="timeOfDay" 
                  value={timeOfDay}
                  onChange={(e) => setTimeOfDay(e.target.value)}
                  required
                />
              </div>
              
              <div className="d-flex justify-content-end gap-2">
                <button type="button" className="btn btn-secondary" onClick={handleClose}>Cancel</button>
                <button type="submit" className="btn btn-primary">Schedule Report</button>
              </div>
            </form>
          </div>
        </div>
      </div>
      <div className="modal-backdrop fade show"></div>
    </div>
  );
};

export default ScheduleReportModal;
