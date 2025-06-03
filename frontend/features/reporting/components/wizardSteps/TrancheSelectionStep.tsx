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
  if (reportScope !== 'TRANCHE') {
    return (
      <div className="text-center p-5">
        <div className="alert alert-warning">
          <i className="bi bi-info-circle me-2"></i>
          Tranche selection is only available for TRANCHE scope reports.
        </div>
      </div>
    );
  }

  return (
    <div>
      <h5 className="mb-3">Step 3: Select Tranches</h5>
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