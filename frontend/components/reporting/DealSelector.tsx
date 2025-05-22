import React from 'react';
import type { Deal } from '@/types';

interface DealSelectorProps {
  deals: Deal[];
  selectedDeals: number[];
  onDealToggle: (dealId: number) => void;
  loading?: boolean;
}

const DealSelector: React.FC<DealSelectorProps> = ({
  deals,
  selectedDeals,
  onDealToggle,
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
        <p className="mt-2">Loading available deals...</p>
      </div>
    );
  }

  if (deals.length === 0) {
    return (
      <div className="alert alert-info">
        <i className="bi bi-info-circle me-2"></i>
        No deals available for configuration. Please contact your administrator if this seems incorrect.
      </div>
    );
  }

  return (
    <div>
      <h5 className="mb-3">Step 2: Select Deals</h5>
      <p className="text-muted">Choose which deals to include in your report template. Data will be pulled for the selected cycle when you run the report.</p>
      <div className="row">
        {deals.map(deal => (
          <div key={deal.id} className="col-md-6 mb-3">
            <div className={`card h-100 ${selectedDeals.includes(deal.id) ? 'border-primary' : ''}`}>
              <div className="card-body">
                <div className="form-check mb-2">
                  <input
                    className="form-check-input"
                    type="checkbox"
                    id={`deal-${deal.id}`}
                    checked={selectedDeals.includes(deal.id)}
                    onChange={() => onDealToggle(deal.id)}
                  />
                  <label className="form-check-label fw-bold" htmlFor={`deal-${deal.id}`}>
                    {deal.name}
                  </label>
                </div>
                <div className="small text-muted">
                  <div><strong>Originator:</strong> {deal.originator}</div>
                  <div><strong>Type:</strong> {deal.deal_type}</div>
                  <div><strong>Principal:</strong> {formatCurrency(deal.total_principal)}</div>
                  <div><strong>Rating:</strong> <span className="badge bg-success">{deal.credit_rating}</span></div>
                  <div><strong>Yield:</strong> {formatPercent(deal.yield_rate)}</div>
                  <div><strong>Closing Date:</strong> {new Date(deal.closing_date).toLocaleDateString()}</div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="alert alert-warning">
        <i className="bi bi-check-circle me-2"></i>
        Selected {selectedDeals.length} deal{selectedDeals.length !== 1 ? 's' : ''}
      </div>
    </div>
  );
};

export default DealSelector;