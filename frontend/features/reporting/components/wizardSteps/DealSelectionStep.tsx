import React from 'react';
import { DealSelector } from '../';
import type { Deal } from '@/types/reporting';

interface DealSelectionStepProps {
  deals: Deal[];
  selectedDeals: number[];
  onDealToggle: (dlNbr: number) => void;
  onSelectAllDeals: () => void;
  loading: boolean;
}

const DealSelectionStep: React.FC<DealSelectionStepProps> = ({
  deals,
  selectedDeals,
  onDealToggle,
  onSelectAllDeals,
  loading
}) => {
  return (
    <div>
      <h5 className="mb-3">Step 2: Select Deals</h5>
      <DealSelector
        deals={deals}
        selectedDeals={selectedDeals}
        onDealToggle={onDealToggle}
        onSelectAllDeals={onSelectAllDeals}
        loading={loading}
      />
    </div>
  );
};

export default DealSelectionStep;