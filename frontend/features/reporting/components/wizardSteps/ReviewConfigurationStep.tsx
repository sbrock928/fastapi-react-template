import React from 'react';
import type { Deal, ReportCalculation } from '@/types/reporting'; // Changed from ReportField

interface ReviewConfigurationStepProps {
  reportName: string;
  reportDescription: string;
  reportScope: 'DEAL' | 'TRANCHE' | '';
  selectedDeals: number[];
  selectedTranches: Record<number, string[]>;
  selectedCalculations: ReportCalculation[]; // Changed from selectedFields
  deals: Deal[];
}

const ReviewConfigurationStep: React.FC<ReviewConfigurationStepProps> = ({
  reportName,
  reportDescription,
  reportScope,
  selectedDeals,
  selectedTranches,
  selectedCalculations, // Changed from selectedFields
  deals
}) => {
  const stepNumber = reportScope === 'DEAL' ? '4' : '5';

  return (
    <div className="row">
      <div className="col-12">
        <h5 className="mb-3">Step {stepNumber}: Review Configuration</h5>
        <div className="card">
          <div className="card-body">
            <h6 className="card-title">Report Summary</h6>
            
            {/* Basic Information */}
            <div className="row g-3">
              <div className="col-md-4">
                <strong>Name:</strong> {reportName}
              </div>
              <div className="col-md-4">
                <strong>Scope:</strong> {reportScope}
              </div>
              <div className="col-md-4">
                <strong>Selected Deals:</strong> {selectedDeals.length}
              </div>
              {reportDescription && (
                <div className="col-12">
                  <strong>Description:</strong>
                  <div className="mt-1 p-2 bg-light rounded">
                    {reportDescription}
                  </div>
                </div>
              )}
            </div>
            
            {/* Selected Calculations Summary */}
            <div className="mt-3">
              <strong>Selected Calculations ({selectedCalculations.length}):</strong>
              <div className="mt-2">
                {selectedCalculations.map((calc: ReportCalculation) => (
                  <span key={calc.calculation_id} className="badge bg-info me-1 mb-1">
                    {calc.display_name || `Calculation ${calc.calculation_id}`}
                  </span>
                ))}
              </div>
            </div>

            {/* Tranche-specific summary */}
            {reportScope === 'TRANCHE' && (
              <div className="mt-3">
                <strong>Selected Tranches:</strong>
                <ul className="list-unstyled mt-2">
                  {selectedDeals.map((dlNbr: number) => {
                    const deal = deals.find((d: Deal) => d.dl_nbr === dlNbr);
                    const trancheCount = selectedTranches[dlNbr]?.length || 0;
                    return (
                      <li key={dlNbr} className="mb-1">
                        <span className="badge bg-primary me-2">{dlNbr}</span>
                        {deal?.issr_cde} - {trancheCount} tranches selected
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}

            {/* Deal-specific summary */}
            {reportScope === 'DEAL' && (
              <div className="mt-3">
                <strong>Selected Deals:</strong>
                <ul className="list-unstyled mt-2">
                  {selectedDeals.map((dlNbr: number) => {
                    const deal = deals.find((d: Deal) => d.dl_nbr === dlNbr);
                    return (
                      <li key={dlNbr} className="mb-1">
                        <span className="badge bg-primary me-2">{dlNbr}</span>
                        {deal?.issr_cde}
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReviewConfigurationStep;