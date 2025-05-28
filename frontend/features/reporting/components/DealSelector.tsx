import React, { useState, useMemo, useEffect } from 'react';
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
  const [searchTerm, setSearchTerm] = useState('');
  const [dealTypeFilter, setDealTypeFilter] = useState('');
  const [originatorFilter, setOriginatorFilter] = useState('');
  const [sortField, setSortField] = useState<keyof Deal>('name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(50); // Default to 50 items per page

  // Get unique values for filters
  const uniqueDealTypes = useMemo(() => {
    return [...new Set(deals.map(deal => deal.deal_type))].sort();
  }, [deals]);

  const uniqueOriginators = useMemo(() => {
    return [...new Set(deals.map(deal => deal.originator))].sort();
  }, [deals]);

  // Filter and search deals
  const filteredDeals = useMemo(() => {
    let filtered = deals.filter(deal => {
      const matchesSearch = deal.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           deal.originator.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesDealType = !dealTypeFilter || deal.deal_type === dealTypeFilter;
      const matchesOriginator = !originatorFilter || deal.originator === originatorFilter;
      
      return matchesSearch && matchesDealType && matchesOriginator;
    });

    // Sort deals
    filtered.sort((a, b) => {
      let aValue = a[sortField];
      let bValue = b[sortField];
      
      // Handle numeric fields
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
      }
      
      // Handle string fields
      aValue = String(aValue).toLowerCase();
      bValue = String(bValue).toLowerCase();
      
      if (sortDirection === 'asc') {
        return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
      } else {
        return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
      }
    });

    return filtered;
  }, [deals, searchTerm, dealTypeFilter, originatorFilter, sortField, sortDirection]);

  // Paginate the filtered results
  const paginatedDeals = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return filteredDeals.slice(startIndex, endIndex);
  }, [filteredDeals, currentPage, itemsPerPage]);

  const totalPages = Math.ceil(filteredDeals.length / itemsPerPage);

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, dealTypeFilter, originatorFilter, sortField, sortDirection]);

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

  // Handle sort
  const handleSort = (field: keyof Deal) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  // Handle select all visible deals (now works with current page)
  const handleSelectAllVisible = () => {
    const visibleDealIds = paginatedDeals.map(deal => deal.id);
    const allVisibleSelected = visibleDealIds.every(id => selectedDeals.includes(id));
    
    if (allVisibleSelected) {
      // Unselect all visible deals
      visibleDealIds.forEach(dealId => {
        if (selectedDeals.includes(dealId)) {
          onDealToggle(dealId);
        }
      });
    } else {
      // Select all visible deals
      visibleDealIds.forEach(dealId => {
        if (!selectedDeals.includes(dealId)) {
          onDealToggle(dealId);
        }
      });
    }
  };

  // Clear all filters
  const clearFilters = () => {
    setSearchTerm('');
    setDealTypeFilter('');
    setOriginatorFilter('');
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

  const allVisibleSelected = paginatedDeals.length > 0 && paginatedDeals.every(deal => selectedDeals.includes(deal.id));
  const someVisibleSelected = paginatedDeals.some(deal => selectedDeals.includes(deal.id));

  return (
    <div>
      <h5 className="mb-3">Step 2: Select Deals</h5>
      <p className="text-muted">Choose which deals to include in your report template. Data will be pulled for the selected cycle when you run the report.</p>
      
      {/* Search and Filter Controls */}
      <div className="card mb-3">
        <div className="card-body">
          <div className="row g-3">
            <div className="col-md-3">
              <label htmlFor="dealSearch" className="form-label">Search Deals</label>
              <div className="input-group">
                <span className="input-group-text">
                  <i className="bi bi-search"></i>
                </span>
                <input
                  type="text"
                  id="dealSearch"
                  className="form-control"
                  placeholder="Search by deal name or originator..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
                {searchTerm && (
                  <button
                    className="btn btn-outline-secondary"
                    type="button"
                    onClick={() => setSearchTerm('')}
                  >
                    <i className="bi bi-x"></i>
                  </button>
                )}
              </div>
            </div>
            <div className="col-md-2">
              <label htmlFor="dealTypeFilter" className="form-label">Deal Type</label>
              <select
                id="dealTypeFilter"
                className="form-select"
                value={dealTypeFilter}
                onChange={(e) => setDealTypeFilter(e.target.value)}
              >
                <option value="">All Types</option>
                {uniqueDealTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>
            <div className="col-md-2">
              <label htmlFor="originatorFilter" className="form-label">Originator</label>
              <select
                id="originatorFilter"
                className="form-select"
                value={originatorFilter}
                onChange={(e) => setOriginatorFilter(e.target.value)}
              >
                <option value="">All Originators</option>
                {uniqueOriginators.map(originator => (
                  <option key={originator} value={originator}>{originator}</option>
                ))}
              </select>
            </div>
            <div className="col-md-2">
              <label htmlFor="itemsPerPage" className="form-label">Per Page</label>
              <select
                id="itemsPerPage"
                className="form-select"
                value={itemsPerPage}
                onChange={(e) => {
                  setItemsPerPage(parseInt(e.target.value));
                  setCurrentPage(1);
                }}
              >
                <option value={25}>25 per page</option>
                <option value={50}>50 per page</option>
                <option value={100}>100 per page</option>
                <option value={250}>250 per page</option>
              </select>
            </div>
            <div className="col-md-3 d-flex align-items-end gap-2">
              <button
                type="button"
                className="btn btn-outline-secondary"
                onClick={clearFilters}
                disabled={!searchTerm && !dealTypeFilter && !originatorFilter}
              >
                Clear Filters
              </button>
              <button
                type="button"
                className="btn btn-outline-primary"
                onClick={handleSelectAllVisible}
                disabled={paginatedDeals.length === 0}
              >
                {allVisibleSelected ? 'Unselect Page' : 'Select Page'} 
                ({paginatedDeals.length})
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Deals Table */}
      <div className="card">
        <div className="card-header">
          <div className="d-flex justify-content-between align-items-center">
            <h6 className="mb-0">Available Deals</h6>
            <div className="text-muted">
              Showing {Math.min((currentPage - 1) * itemsPerPage + 1, filteredDeals.length)}-{Math.min(currentPage * itemsPerPage, filteredDeals.length)} of {filteredDeals.length} deals
              {deals.length !== filteredDeals.length && ` (${deals.length} total)`}
            </div>
          </div>
        </div>
        <div className="card-body p-0">
          <div className="table-responsive">
            <table className="table table-hover mb-0">
              <thead className="sticky-top bg-light">
                <tr>
                  <th style={{ width: '50px' }}>
                    <input
                      type="checkbox"
                      className="form-check-input"
                      checked={allVisibleSelected}
                      ref={(input) => {
                        if (input) input.indeterminate = someVisibleSelected && !allVisibleSelected;
                      }}
                      onChange={handleSelectAllVisible}
                      disabled={paginatedDeals.length === 0}
                    />
                  </th>
                  <th 
                    style={{ cursor: 'pointer', minWidth: '250px' }}
                    onClick={() => handleSort('name')}
                  >
                    Deal Name
                    {sortField === 'name' && (
                      <i className={`bi bi-chevron-${sortDirection === 'asc' ? 'up' : 'down'} ms-1`}></i>
                    )}
                  </th>
                  <th 
                    style={{ cursor: 'pointer', minWidth: '150px' }}
                    onClick={() => handleSort('originator')}
                  >
                    Originator
                    {sortField === 'originator' && (
                      <i className={`bi bi-chevron-${sortDirection === 'asc' ? 'up' : 'down'} ms-1`}></i>
                    )}
                  </th>
                  <th 
                    style={{ cursor: 'pointer', minWidth: '100px' }}
                    onClick={() => handleSort('deal_type')}
                  >
                    Type
                    {sortField === 'deal_type' && (
                      <i className={`bi bi-chevron-${sortDirection === 'asc' ? 'up' : 'down'} ms-1`}></i>
                    )}
                  </th>
                  <th 
                    style={{ cursor: 'pointer', minWidth: '120px' }}
                    onClick={() => handleSort('total_principal')}
                    className="text-end"
                  >
                    Principal
                    {sortField === 'total_principal' && (
                      <i className={`bi bi-chevron-${sortDirection === 'asc' ? 'up' : 'down'} ms-1`}></i>
                    )}
                  </th>
                  <th style={{ minWidth: '100px' }}>Rating</th>
                  <th 
                    style={{ cursor: 'pointer', minWidth: '100px' }}
                    onClick={() => handleSort('yield_rate')}
                    className="text-end"
                  >
                    Yield
                    {sortField === 'yield_rate' && (
                      <i className={`bi bi-chevron-${sortDirection === 'asc' ? 'up' : 'down'} ms-1`}></i>
                    )}
                  </th>
                  <th 
                    style={{ cursor: 'pointer', minWidth: '120px' }}
                    onClick={() => handleSort('closing_date')}
                  >
                    Closing Date
                    {sortField === 'closing_date' && (
                      <i className={`bi bi-chevron-${sortDirection === 'asc' ? 'up' : 'down'} ms-1`}></i>
                    )}
                  </th>
                </tr>
              </thead>
              <tbody>
                {paginatedDeals.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center py-4 text-muted">
                      <i className="bi bi-search me-2"></i>
                      No deals match your current filters.
                    </td>
                  </tr>
                ) : (
                  paginatedDeals.map(deal => (
                    <tr 
                      key={deal.id} 
                      className={selectedDeals.includes(deal.id) ? 'table-primary' : ''}
                      style={{ cursor: 'pointer' }}
                      onClick={() => onDealToggle(deal.id)}
                    >
                      <td>
                        <input
                          type="checkbox"
                          className="form-check-input"
                          checked={selectedDeals.includes(deal.id)}
                          onChange={() => onDealToggle(deal.id)}
                          onClick={(e) => e.stopPropagation()}
                        />
                      </td>
                      <td>
                        <div className="fw-bold">{deal.name}</div>
                      </td>
                      <td>{deal.originator}</td>
                      <td>
                        <span className="badge bg-secondary">{deal.deal_type}</span>
                      </td>
                      <td className="text-end">{formatCurrency(deal.total_principal)}</td>
                      <td>
                        <span className="badge bg-success">{deal.credit_rating}</span>
                      </td>
                      <td className="text-end">{formatPercent(deal.yield_rate)}</td>
                      <td>{new Date(deal.closing_date).toLocaleDateString()}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="d-flex justify-content-between align-items-center p-3 border-top">
              <div className="text-muted">
                Page {currentPage} of {totalPages}
              </div>
              <nav>
                <ul className="pagination pagination-sm mb-0">
                  <li className={`page-item ${currentPage === 1 ? 'disabled' : ''}`}>
                    <button
                      className="page-link"
                      onClick={() => setCurrentPage(1)}
                      disabled={currentPage === 1}
                    >
                      <i className="bi bi-chevron-double-left"></i>
                    </button>
                  </li>
                  <li className={`page-item ${currentPage === 1 ? 'disabled' : ''}`}>
                    <button
                      className="page-link"
                      onClick={() => setCurrentPage(currentPage - 1)}
                      disabled={currentPage === 1}
                    >
                      <i className="bi bi-chevron-left"></i>
                    </button>
                  </li>
                  
                  {/* Show page numbers around current page */}
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    let pageNum;
                    if (totalPages <= 5) {
                      pageNum = i + 1;
                    } else if (currentPage <= 3) {
                      pageNum = i + 1;
                    } else if (currentPage >= totalPages - 2) {
                      pageNum = totalPages - 4 + i;
                    } else {
                      pageNum = currentPage - 2 + i;
                    }
                    
                    return (
                      <li key={pageNum} className={`page-item ${currentPage === pageNum ? 'active' : ''}`}>
                        <button
                          className="page-link"
                          onClick={() => setCurrentPage(pageNum)}
                        >
                          {pageNum}
                        </button>
                      </li>
                    );
                  })}
                  
                  <li className={`page-item ${currentPage === totalPages ? 'disabled' : ''}`}>
                    <button
                      className="page-link"
                      onClick={() => setCurrentPage(currentPage + 1)}
                      disabled={currentPage === totalPages}
                    >
                      <i className="bi bi-chevron-right"></i>
                    </button>
                  </li>
                  <li className={`page-item ${currentPage === totalPages ? 'disabled' : ''}`}>
                    <button
                      className="page-link"
                      onClick={() => setCurrentPage(totalPages)}
                      disabled={currentPage === totalPages}
                    >
                      <i className="bi bi-chevron-double-right"></i>
                    </button>
                  </li>
                </ul>
              </nav>
            </div>
          )}
        </div>
      </div>

      {/* Selection Summary */}
      <div className="alert alert-warning mt-3">
        <i className="bi bi-check-circle me-2"></i>
        Selected {selectedDeals.length} deal{selectedDeals.length !== 1 ? 's' : ''}
        {filteredDeals.length !== deals.length && (
          <span className="text-muted ms-2">
            ({selectedDeals.filter(id => filteredDeals.some(deal => deal.id === id)).length} of {filteredDeals.length} visible)
          </span>
        )}
      </div>
    </div>
  );
};

export default DealSelector;