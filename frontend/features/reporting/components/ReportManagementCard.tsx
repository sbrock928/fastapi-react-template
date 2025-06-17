import React, { useState } from 'react';
import { ReportBuilderWizard, SavedReportsManager, ExecutionLogsModal } from './';
import type { ReportConfig } from '@/types';

interface ReportManagementCardProps {
  reportBuilderMode: boolean;
  wizardMode: 'create' | 'edit';
  editingReport: ReportConfig | null;
  selectedSavedReport: string;
  onReportSaved: () => void;
  onCreateNewReport: () => void;
  onEditReport: (report: ReportConfig) => void;
  onCancelWizard: () => void;
  onSavedReportSelect: (reportId: string) => void;
  onReportsUpdated: () => void;
}

const ReportManagementCard: React.FC<ReportManagementCardProps> = ({
  reportBuilderMode,
  wizardMode,
  editingReport,
  selectedSavedReport,
  onReportSaved,
  onCreateNewReport,
  onEditReport,
  onCancelWizard,
  onSavedReportSelect,
  onReportsUpdated
}) => {
  // State for execution logs modal at top level
  const [showExecutionLogs, setShowExecutionLogs] = useState(false);
  const [executionLogsReportId, setExecutionLogsReportId] = useState<number | null>(null);
  const [executionLogsReportName, setExecutionLogsReportName] = useState<string>('');

  // Handle showing execution logs modal
  const handleShowExecutionLogs = (reportId: number, reportName: string) => {
    setExecutionLogsReportId(reportId);
    setExecutionLogsReportName(reportName);
    setShowExecutionLogs(true);
  };

  // Handle closing execution logs modal
  const handleCloseExecutionLogs = () => {
    setShowExecutionLogs(false);
    setExecutionLogsReportId(null);
    setExecutionLogsReportName('');
  };

  return (
    <>
      <div className="card mb-4">
        <div className="card-header bg-primary text-white d-flex justify-content-between align-items-center">
          <h5 className="card-title mb-0">
            {reportBuilderMode 
              ? (wizardMode === 'edit' ? 'Edit Report Configuration' : 'Create New Report') 
              : 'Manage Reports'
            }
          </h5>
          {reportBuilderMode && (
            <button 
              type="button"
              className="btn btn-outline-light btn-sm"
              onClick={onCancelWizard}
            >
              <i className="bi bi-x-lg"></i> Cancel
            </button>
          )}
        </div>
        <div className="card-body">
          {reportBuilderMode ? (
            <ReportBuilderWizard
              onReportSaved={onReportSaved}
              editingReport={editingReport}
              mode={wizardMode}
            />
          ) : (
            <SavedReportsManager
              selectedReportId={selectedSavedReport}
              onReportSelect={onSavedReportSelect}
              onCreateNew={onCreateNewReport}
              onReportsUpdated={onReportsUpdated}
              onEditReport={onEditReport}
              onShowExecutionLogs={handleShowExecutionLogs}
            />
          )}
        </div>
      </div>

      {/* Top-level Execution Logs Modal */}
      {showExecutionLogs && executionLogsReportId && (
        <ExecutionLogsModal
          reportId={executionLogsReportId}
          reportName={executionLogsReportName}
          isOpen={showExecutionLogs}
          onClose={handleCloseExecutionLogs}
        />
      )}
    </>
  );
};

export default ReportManagementCard;