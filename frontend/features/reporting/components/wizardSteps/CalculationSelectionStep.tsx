import React from 'react';
import CalculationSelector from '../CalculationSelector';
import type { AvailableCalculation, ReportCalculation } from '@/types/reporting';

interface CalculationSelectionStepProps {
  reportScope: 'DEAL' | 'TRANCHE' | '';
  availableCalculations: AvailableCalculation[];
  selectedCalculations: ReportCalculation[];
  onCalculationsChange: (calculations: ReportCalculation[]) => void;
  loading: boolean;
}

const CalculationSelectionStep: React.FC<CalculationSelectionStepProps> = ({
  reportScope,
  availableCalculations,
  selectedCalculations,
  onCalculationsChange,
  loading
}) => {
  const stepNumber = 3; // Fixed step number since we now have 4 steps total
  
  return (
    <div className="col-12">
      <h5 className="mb-3">Step {stepNumber}: Select Report Calculations</h5>
      <CalculationSelector
        scope={reportScope as 'DEAL' | 'TRANCHE'}
        availableCalculations={availableCalculations}
        selectedCalculations={selectedCalculations}
        onCalculationsChange={onCalculationsChange}
        loading={loading}
      />
    </div>
  );
};

export default CalculationSelectionStep;