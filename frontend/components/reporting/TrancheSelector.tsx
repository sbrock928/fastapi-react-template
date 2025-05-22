import React from 'react';
import type { Deal, Tranche } from '@/types';

interface TrancheSelectorProps {
  deals: Deal[];
  selectedDeals: number[];
  tranches: Record<number, Tranche[]>;
  selectedTranches: Record<number, number[]>;
  onTrancheToggle: (dealId: number, trancheId: number) => void;
  onSelectAllTranches: (dealId: number) => void;
  loading?: boolean;
}

const TrancheSelector: React.FC<TrancheSelectorProps> = ({
  deals,
  selectedDeals,
  tranches,
  selectedTranches,
  onTrancheToggle,
  onSelectAllTranches,
  loading = false
}) => {
  // Format currency
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      notation: 'compact',
      maximumFractionDigits: 1
    }).format(amount);
  };

  // Format percentage
  const formatPercent = (rate: number) => {
    return (rate * 100).toFixed(2) + '%';
  };

  if (loading) {
    return (
      <div className="text-center py-4">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
        <p className="mt-2">Loading tranches...</p>
      </div>
    );
  }

  return (
    <div>
      <h5 className="mb-3">Step 3: Select Tranches</h5>
      <p className="text-muted">Choose which tranches to include in your report template for the selected deals.</p>
      {selectedDeals.map(dealId => {
        const deal = deals.find(d => d.id === dealId);
        const dealTranches = tranches[dealId] || [];
        const selectedDealTranches = selectedTranches[dealId] || [];
        
        if (!deal) return null;
        
        return (
          <div key={dealId} className="card mb-3">
            <div className="card-header d-flex justify-content-between align-items-center">
              <h6 className="mb-0">{deal.name}</h6>
              <button
                type="button"
                className="btn btn-sm btn-outline-primary"
                onClick={() => onSelectAllTranches(dealId)}
                disabled={dealTranches.length === 0}
              >
                Select All ({dealTranches.length})
              </button>
            </div>
            <div className="card-body">
              {dealTranches.length === 0 ? (
                <div className="text-muted text-center py-3">
                  <i className="bi bi-info-circle me-2"></i>
                  No tranches available for this deal
                </div>
              ) : (
                <div className="row">
                  {dealTranches.map(tranche => (
                    <div key={tranche.id} className="col-md-6 mb-2">
                      <div className={`p-2 border rounded ${selectedDealTranches.includes(tranche.id) ? 'border-primary bg-light' : ''}`}>
                        <div className="form-check">
                          <input
                            className="form-check-input"
                            type="checkbox"
                            id={`tranche-${tranche.id}`}
                            checked={selectedDealTranches.includes(tranche.id)}
                            onChange={() => onTrancheToggle(dealId, tranche.id)}
                          />
                          <label className="form-check-label" htmlFor={`tranche-${tranche.id}`}>
                            <strong>{tranche.name}</strong>
                          </label>
                        </div>
                        <div className="small text-muted mt-1">
                          <div>Principal: {formatCurrency(tranche.principal_amount)}</div>
                          <div>Rate: {formatPercent(tranche.interest_rate)} • Rating: {tranche.credit_rating}</div>
                          <div>Priority: {tranche.payment_priority}</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        );
      })}
      <div className="alert alert-warning">
        <i className="bi bi-check-circle me-2"></i>
        Selected {Object.values(selectedTranches).flat().length} tranche{Object.values(selectedTranches).flat().length !== 1 ? 's' : ''} 
        across {selectedDeals.length} deal{selectedDeals.length !== 1 ? 's' : ''}
      </div>
    </div>
  );
};

export default TrancheSelector;