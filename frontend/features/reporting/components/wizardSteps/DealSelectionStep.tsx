import React from 'react';
import { DealSelector } from '../';
import type { Deal } from '@/types/reporting';

interface DealSelectionStepProps {
  deals: Deal[];
  selectedDeals: number[];
  onDealToggle: (dlNbr: number) => void;
  loading: boolean;
}

const DealSelectionStep: React.FC<DealSelectionStepProps> = ({
  deals,
  selectedDeals,
  onDealToggle,
  loading
}) => {
  return (
    <div>
      <h5 className="mb-3">Step 2: Select Deals</h5>
      <DealSelector
        deals={deals}
        selectedDeals={selectedDeals}
        onDealToggle={onDealToggle}
        loading={loading}
      />
    </div>
  );
};

export default DealSelectionStep;