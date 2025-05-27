import React, { useState, useMemo, useRef, useEffect } from 'react';
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
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState<'deal_name' | 'tranche_name' | 'principal_amount' | 'interest_rate' | 'payment_priority'>('deal_name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [selectedDealFilter, setSelectedDealFilter] = useState<number | 'all'>('all');
  const masterCheckboxRef = useRef<HTMLInputElement>(null);

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

  // Create flat list of all tranches with deal info
  const allTranches = useMemo(() => {
    const trancheList: Array<Tranche & { deal: Deal; dealId: number }> = [];
    
    selectedDeals.forEach(dealId => {
      const deal = deals.find(d => d.id === dealId);
      const dealTranches = tranches[dealId] || [];
      
      if (deal) {
        dealTranches.forEach(tranche => {
          trancheList.push({
            ...tranche,
            deal,
            dealId
          });
        });
      }
    });
    
    return trancheList;
  }, [selectedDeals, deals, tranches]);

  // Filter and sort tranches
  const filteredAndSortedTranches = useMemo(() => {
    let filtered = allTranches;

    // Apply search filter
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      filtered = filtered.filter(tranche => 
        tranche.name.toLowerCase().includes(search) ||
        tranche.class_name.toLowerCase().includes(search) ||
        tranche.deal.name.toLowerCase().includes(search) ||
        tranche.credit_rating.toLowerCase().includes(search)
      );
    }

    // Apply deal filter
    if (selectedDealFilter !== 'all') {
      filtered = filtered.filter(tranche => tranche.dealId === selectedDealFilter);
    }

    // Sort
    filtered.sort((a, b) => {
      let aValue: any;
      let bValue: any;

      switch (sortField) {
        case 'deal_name':
          aValue = a.deal.name;
          bValue = b.deal.name;
          break;
        case 'tranche_name':
          aValue = a.name;
          bValue = b.name;
          break;
        case 'principal_amount':
          aValue = a.principal_amount;
          bValue = b.principal_amount;
          break;
        case 'interest_rate':
          aValue = a.interest_rate;
          bValue = b.interest_rate;
          break;
        case 'payment_priority':
          aValue = a.payment_priority;
          bValue = b.payment_priority;
          break;
        default:
          aValue = a.name;
          bValue = b.name;
      }

      if (typeof aValue === 'string') {
        const comparison = aValue.localeCompare(bValue);
        return sortDirection === 'asc' ? comparison : -comparison;
      } else {
        const comparison = aValue - bValue;
        return sortDirection === 'asc' ? comparison : -comparison;
      }
    });

    return filtered;
  }, [allTranches, searchTerm, selectedDealFilter, sortField, sortDirection]);

  const handleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  // Bulk selection handlers
  const handleSelectAll = () => {
    filteredAndSortedTranches.forEach(tranche => {
      const selectedDealTranches = selectedTranches[tranche.dealId] || [];
      if (!selectedDealTranches.includes(tranche.id)) {
        onTrancheToggle(tranche.dealId, tranche.id);
      }
    });
  };

  const handleDeselectAll = () => {
    filteredAndSortedTranches.forEach(tranche => {
      const selectedDealTranches = selectedTranches[tranche.dealId] || [];
      if (selectedDealTranches.includes(tranche.id)) {
        onTrancheToggle(tranche.dealId, tranche.id);
      }
    });
  };

  const handleSelectAllForDeal = (dealId: number) => {
    onSelectAllTranches(dealId);
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

  if (allTranches.length === 0) {
    return (
      <div className="alert alert-info">
        <i className="bi bi-info-circle me-2"></i>
        No tranches available for the selected deals.
      </div>
    );
  }

  const totalSelected = Object.values(selectedTranches).flat().length;
  const totalVisible = filteredAndSortedTranches.length;
  const allVisibleSelected = totalVisible > 0 && filteredAndSortedTranches.every(tranche => 
    (selectedTranches[tranche.dealId] || []).includes(tranche.id)
  );
  const someVisibleSelected = filteredAndSortedTranches.some(tranche => 
    (selectedTranches[tranche.dealId] || []).includes(tranche.id)
  );

  // Update master checkbox indeterminate state
  useEffect(() => {
    if (masterCheckboxRef.current) {
      masterCheckboxRef.current.indeterminate = !allVisibleSelected && someVisibleSelected;
    }
  }, [allVisibleSelected, someVisibleSelected]);

  return (
    <div>
      <h5 className="mb-3">Step 3: Select Tranches</h5>
      <p className="text-muted">Choose which tranches to include in your report template for the selected deals.</p>
      
      {/* Search and Filter Controls */}
      <div className="card mb-3">
        <div className="card-body">
          <div className="row g-3">
            <div className="col-md-4">
              <div className="input-group">
                <span className="input-group-text">
                  <i className="bi bi-search"></i>
                </span>
                <input
                  type="text"
                  className="form-control"
                  placeholder="Search tranches..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </div>
            <div className="col-md-3">
              <select
                className="form-select"
                value={selectedDealFilter}
                onChange={(e) => setSelectedDealFilter(e.target.value === 'all' ? 'all' : parseInt(e.target.value))}
              >
                <option value="all">All Deals</option>
                {selectedDeals.map(dealId => {
                  const deal = deals.find(d => d.id === dealId);
                  return deal ? (
                    <option key={dealId} value={dealId}>{deal.name}</option>
                  ) : null;
                })}
              </select>
            </div>
            <div className="col-md-5">
              <div className="btn-group" role="group">
                <button
                  type="button"
                  className="btn btn-outline-primary btn-sm"
                  onClick={handleSelectAll}
                  disabled={allVisibleSelected}
                >
                  <i className="bi bi-check-all"></i> Select Visible ({totalVisible})
                </button>
                <button
                  type="button"
                  className="btn btn-outline-secondary btn-sm"
                  onClick={handleDeselectAll}
                >
                  <i className="bi bi-x-square"></i> Deselect Visible
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tranches Table */}
      <div className="card">
        <div className="card-header">
          <div className="d-flex justify-content-between align-items-center">
            <h6 className="mb-0">Available Tranches</h6>
            <div className="text-muted">
              Showing {totalVisible} of {allTranches.length} tranches
            </div>
          </div>
        </div>
        <div className="card-body p-0">
          <div className="table-responsive" style={{ maxHeight: '600px' }}>
            <table className="table table-sm table-hover mb-0">
              <thead className="sticky-top bg-light">
                <tr>
                  <th style={{ width: '40px' }}>
                    <input
                      ref={masterCheckboxRef}
                      type="checkbox"
                      className="form-check-input"
                      checked={allVisibleSelected}
                      onChange={allVisibleSelected ? handleDeselectAll : handleSelectAll}
                    />
                  </th>
                  <th 
                    style={{ cursor: 'pointer', minWidth: '200px' }}
                    onClick={() => handleSort('deal_name')}
                  >
                    Deal
                    {sortField === 'deal_name' && (
                      <i className={`bi bi-chevron-${sortDirection === 'asc' ? 'up' : 'down'} ms-1`}></i>
                    )}
                  </th>
                  <th 
                    style={{ cursor: 'pointer', minWidth: '150px' }}
                    onClick={() => handleSort('tranche_name')}
                  >
                    Tranche
                    {sortField === 'tranche_name' && (
                      <i className={`bi bi-chevron-${sortDirection === 'asc' ? 'up' : 'down'} ms-1`}></i>
                    )}
                  </th>
                  <th style={{ minWidth: '80px' }}>Class</th>
                  <th 
                    style={{ cursor: 'pointer', minWidth: '120px' }}
                    onClick={() => handleSort('principal_amount')}
                    className="text-end"
                  >
                    Principal
                    {sortField === 'principal_amount' && (
                      <i className={`bi bi-chevron-${sortDirection === 'asc' ? 'up' : 'down'} ms-1`}></i>
                    )}
                  </th>
                  <th 
                    style={{ cursor: 'pointer', minWidth: '100px' }}
                    onClick={() => handleSort('interest_rate')}
                    className="text-end"
                  >
                    Rate
                    {sortField === 'interest_rate' && (
                      <i className={`bi bi-chevron-${sortDirection === 'asc' ? 'up' : 'down'} ms-1`}></i>
                    )}
                  </th>
                  <th style={{ minWidth: '80px' }}>Rating</th>
                  <th 
                    style={{ cursor: 'pointer', minWidth: '80px' }}
                    onClick={() => handleSort('payment_priority')}
                    className="text-center"
                  >
                    Priority
                    {sortField === 'payment_priority' && (
                      <i className={`bi bi-chevron-${sortDirection === 'asc' ? 'up' : 'down'} ms-1`}></i>
                    )}
                  </th>
                  <th style={{ width: '80px' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredAndSortedTranches.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="text-center text-muted py-4">
                      <i className="bi bi-search me-2"></i>
                      No tranches match your search criteria
                    </td>
                  </tr>
                ) : (
                  filteredAndSortedTranches.map(tranche => {
                    const isSelected = (selectedTranches[tranche.dealId] || []).includes(tranche.id);
                    return (
                      <tr 
                        key={`${tranche.dealId}-${tranche.id}`}
                        className={isSelected ? 'table-primary' : ''}
                        style={{ cursor: 'pointer' }}
                        onClick={() => onTrancheToggle(tranche.dealId, tranche.id)}
                      >
                        <td>
                          <input
                            type="checkbox"
                            className="form-check-input"
                            checked={isSelected}
                            onChange={() => onTrancheToggle(tranche.dealId, tranche.id)}
                            onClick={(e) => e.stopPropagation()}
                          />
                        </td>
                        <td>
                          <div className="fw-bold">{tranche.deal.name}</div>
                          <div className="small text-muted">{tranche.deal.originator}</div>
                        </td>
                        <td>
                          <div className="fw-bold">{tranche.name}</div>
                        </td>
                        <td>
                          <span className="badge bg-secondary">{tranche.class_name}</span>
                        </td>
                        <td className="text-end">{formatCurrency(tranche.principal_amount)}</td>
                        <td className="text-end">{formatPercent(tranche.interest_rate)}</td>
                        <td>
                          <span className="badge bg-success">{tranche.credit_rating}</span>
                        </td>
                        <td className="text-center">
                          <span className="badge bg-info">{tranche.payment_priority}</span>
                        </td>
                        <td>
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-primary"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSelectAllForDeal(tranche.dealId);
                            }}
                            title={`Select all tranches for ${tranche.deal.name}`}
                          >
                            <i className="bi bi-collection"></i>
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Selection Summary */}
      <div className="alert alert-warning mt-3">
        <i className="bi bi-check-circle me-2"></i>
        Selected {totalSelected} tranche{totalSelected !== 1 ? 's' : ''} 
        across {selectedDeals.length} deal{selectedDeals.length !== 1 ? 's' : ''}
        {filteredAndSortedTranches.length !== allTranches.length && (
          <span className="text-muted ms-2">
            ({filteredAndSortedTranches.filter(tranche => 
              (selectedTranches[tranche.dealId] || []).includes(tranche.id)
            ).length} of {filteredAndSortedTranches.length} visible)
          </span>
        )}
      </div>
    </div>
  );
};

export default TrancheSelector;