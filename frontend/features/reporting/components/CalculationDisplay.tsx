// frontend/features/reporting/components/CalculationDisplay.tsx
// Component to display calculations with new string-based ID format

import React from 'react';
import { parseCalculationId, formatCalculationIdForDisplay } from '@/types/calculations';
import type { AvailableCalculation } from '@/types/calculations';

interface CalculationDisplayProps {
  calculation: AvailableCalculation;
  showDetails?: boolean;
  className?: string;
}

export const CalculationDisplay: React.FC<CalculationDisplayProps> = ({ 
  calculation, 
  showDetails = false,
  className = ''
}) => {
  const parsed = parseCalculationId(calculation.id);
  
  return (
    <div className={`calculation-item ${className}`}>
      <div className="calculation-header d-flex justify-content-between align-items-center">
        <span className="calculation-name fw-bold">{calculation.name}</span>
        <span className={`badge calculation-type type-${parsed.type}`}>
          {parsed.type.toUpperCase()}
        </span>
      </div>
      
      {showDetails && (
        <div className="calculation-details mt-2">
          {parsed.type === 'user' && (
            <div className="text-muted small">
              <div><strong>Source Field:</strong> {parsed.identifier}</div>
              {calculation.source_model && <div><strong>Model:</strong> {calculation.source_model}</div>}
              {calculation.aggregation_function && <div><strong>Function:</strong> {calculation.aggregation_function}</div>}
              {calculation.weight_field && <div><strong>Weight Field:</strong> {calculation.weight_field}</div>}
            </div>
          )}
          
          {parsed.type === 'system' && (
            <div className="text-muted small">
              <div><strong>Result Column:</strong> {parsed.identifier}</div>
              <div><strong>Type:</strong> Custom SQL Calculation</div>
            </div>
          )}
          
          {parsed.type === 'static' && (
            <div className="text-muted small">
              <div><strong>Field Path:</strong> {parsed.identifier}</div>
              <div><strong>Type:</strong> Static Database Field</div>
            </div>
          )}
          
          <div className="mt-1">
            <span className="badge bg-secondary me-1">{calculation.category}</span>
            <span className="badge bg-info">{calculation.group_level}</span>
            {calculation.is_default && (
              <span className="badge bg-warning text-dark ms-1">Default</span>
            )}
          </div>
        </div>
      )}
      
      {calculation.description && showDetails && (
        <div className="calculation-description mt-2 text-muted small">
          {calculation.description}
        </div>
      )}
      
      {!showDetails && (
        <div className="calculation-id-preview text-muted small mt-1">
          {formatCalculationIdForDisplay(calculation.id)}
        </div>
      )}
    </div>
  );
};

// Styles for calculation type badges
const calculationTypeStyles = `
.calculation-type.type-user {
  background-color: #0d6efd;
  color: white;
}

.calculation-type.type-system {
  background-color: #ffc107;
  color: #000;
}

.calculation-type.type-static {
  background-color: #0dcaf0;
  color: #000;
}
`;

// Export styles for inclusion in main CSS
export { calculationTypeStyles };

export default CalculationDisplay;