import React from 'react';
import { TrancheSelector } from '../';
import type { Deal, TrancheReportSummary } from '@/types/reporting';

interface TrancheSelectionStepProps {
  reportScope: 'DEAL' | 'TRANCHE' | '';
  deals: Deal[];
  selectedDeals: number[];
  tranches: Record<string, TrancheReportSummary[]>;
  selectedTranches: Record<number, string[]>;
  onTrancheToggle: (dlNbr: number, trId: string) => void;
  onSelectAllTranches: (dlNbr: number) => void;
  loading: boolean;
}

const TrancheSelectionStep: React.FC<TrancheSelectionStepProps> = ({
  reportScope,
  deals,
  selectedDeals,
  tranches,
  selectedTranches,
  onTrancheToggle,
  onSelectAllTranches,
  loading
}) => {
  // Allow tranche selection for both DEAL and TRANCHE reports
  if (reportScope !== 'TRANCHE' && reportScope !== 'DEAL') {
    return (
      <div className="text-center p-5">
        <div className="alert alert-warning">
          <i className="bi bi-info-circle me-2"></i>
          Please select a report scope first.
        </div>
      </div>
    );
  }

  return (
    <div>
      <h5 className="mb-3">Step 3: Select Tranches</h5>
      
      {/* Show different messaging based on report scope */}
      <div className="alert alert-info mb-3">
        <i className="bi bi-info-circle me-2"></i>
        {reportScope === 'DEAL' ? (
          <span>
            <strong>Deal-Level Report:</strong> Select specific tranches to include in your deal-level analysis. 
            You can exclude certain tranches if they should not be part of the deal calculations.
          </span>
        ) : (
          <span>
            <strong>Tranche-Level Report:</strong> Select the specific tranches you want to analyze. 
            Each selected tranche will appear as a separate row in your report.
          </span>
        )}
      </div>
      
      <TrancheSelector
        deals={deals}
        selectedDeals={selectedDeals}
        tranches={tranches}
        selectedTranches={selectedTranches}
        onTrancheToggle={onTrancheToggle}
        onSelectAllTranches={onSelectAllTranches}
        loading={loading}
      />
    </div>
  );
};

export default TrancheSelectionStep;