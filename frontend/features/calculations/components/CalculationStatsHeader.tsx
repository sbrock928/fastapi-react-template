// frontend/features/calculations/components/CalculationStatsHeader.tsx
import React from 'react';
import type { UserCalculation, SystemCalculation } from '@/types/calculations';

interface CalculationStatsHeaderProps {
  userCalculations: UserCalculation[];
  systemCalculations: SystemCalculation[];
  userUsage: Record<number, any>;
}

// Define types for calculations that might have usage_info
type CalculationWithUsage = (UserCalculation | SystemCalculation) & {
  usage_info?: {
    calculation_id: number;
    calculation_name: string;
    is_in_use: boolean;
    report_count: number;
    reports: any[];
  };
};

const CalculationStatsHeader: React.FC<CalculationStatsHeaderProps> = ({
  userCalculations,
  systemCalculations,
  userUsage
}) => {
  // Calculate in-use counts from embedded usage_info and userUsage
  const userInUse = Object.values(userUsage).filter(u => u?.is_in_use).length;
  const systemInUse = systemCalculations.filter(calc => {
    const calcWithUsage = calc as CalculationWithUsage;
    return calcWithUsage.usage_info?.is_in_use;
  }).length;

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

export default CalculationStatsHeader;