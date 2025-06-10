// frontend/features/calculations/components/CalculationStatsFooter.tsx
import React from 'react';
import type { Calculation } from '@/types/calculations';

interface CalculationStatsFooterProps {
  userCalculations: Calculation[];
  systemCalculations: Calculation[];
  userUsage: Record<number, any>;
  systemUsage: Record<number, any>;
}

const CalculationStatsFooter: React.FC<CalculationStatsFooterProps> = ({
  userCalculations,
  systemCalculations,
  userUsage,
  systemUsage
}) => {
  // Calculate in-use counts
  const userInUse = Object.values(userUsage).filter(u => u?.is_in_use).length;
  const systemInUse = Object.values(systemUsage).filter(u => u?.is_in_use).length;

  return (
    <div className="card bg-light mt-4">
      <div className="card-body">
        <h6 className="card-title text-center mb-3">
          <i className="bi bi-bar-chart me-2"></i>
          Calculation Statistics
        </h6>
        <div className="row text-center">
          {/* User Calculations */}
          <div className="col-md-3">
            <div className="h4 mb-0 text-primary">{userCalculations.length}</div>
            <small className="text-muted">Total User Calculations</small>
          </div>
          
          {/* User In Use */}
          <div className="col-md-3">
            <div className="h4 mb-0 text-info">{userInUse}</div>
            <small className="text-muted">User Calcs In Use</small>
          </div>
          
          {/* System Calculations */}
          <div className="col-md-3">
            <div className="h4 mb-0 text-success">{systemCalculations.length}</div>
            <small className="text-muted">Total System Calculations</small>
          </div>
          
          {/* System In Use */}
          <div className="col-md-3">
            <div className="h4 mb-0 text-warning">{systemInUse}</div>
            <small className="text-muted">System Calcs In Use</small>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CalculationStatsFooter;