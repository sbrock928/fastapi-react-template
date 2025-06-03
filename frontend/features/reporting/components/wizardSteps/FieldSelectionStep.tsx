import React from 'react';
import FieldSelector from '../FieldSelector';
import type { AvailableField, ReportField } from '@/types/reporting';

interface FieldSelectionStepProps {
  reportScope: 'DEAL' | 'TRANCHE' | '';
  availableFields: AvailableField[];
  selectedFields: ReportField[];
  onFieldsChange: (fields: ReportField[]) => void;
  loading: boolean;
}

const FieldSelectionStep: React.FC<FieldSelectionStepProps> = ({
  reportScope,
  availableFields,
  selectedFields,
  onFieldsChange,
  loading
}) => {
  const stepNumber = reportScope === 'DEAL' ? '3' : '4';
  
  return (
    <div className="col-12">
      <h5 className="mb-3">Step {stepNumber}: Select Report Fields</h5>
      <FieldSelector
        scope={reportScope as 'DEAL' | 'TRANCHE'}
        availableFields={availableFields}
        selectedFields={selectedFields}
        onFieldsChange={onFieldsChange}
        loading={loading}
      />
    </div>
  );
};

export default FieldSelectionStep;