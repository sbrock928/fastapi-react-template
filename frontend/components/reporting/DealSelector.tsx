import React, { useState, useEffect, useMemo } from 'react';
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
  // Search and pagination state
  const [searchText, setSearchText] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const dealsPerPage = 20; // More deals per page since cards are simpler

  // Reset page when search changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchText]);

  // Filter deals based on search
  const filteredDeals = useMemo(() => {
    if (!searchText) return deals;
    
    const searchLower = searchText.toLowerCase();
    return deals.filter(deal => 
      deal.name.toLowerCase().includes(searchLower) ||
      deal.originator.toLowerCase().includes(searchLower)
    );
  }, [deals, searchText]);

  // Paginate filtered deals
  const paginatedDeals = useMemo(() => {
    const startIndex = (currentPage - 1) * dealsPerPage;
    return filteredDeals.slice(startIndex, startIndex + dealsPerPage);
  }, [filteredDeals, currentPage, dealsPerPage]);

  // Calculate pagination info
  const totalPages = Math.ceil(filteredDeals.length / dealsPerPage);
  const startIndex = (currentPage - 1) * dealsPerPage + 1;
  const endIndex = Math.min(currentPage * dealsPerPage, filteredDeals.length);

  // Handle select all visible deals
  const handleSelectAllVisible = () => {
    paginatedDeals.forEach(deal => {
      if (!selectedDeals.includes(deal.id)) {
        onDealToggle(deal.id);
      }
    });
  };

  // Handle deselect all visible deals
  const handleDeselectAllVisible = () => {
    paginatedDeals.forEach(deal => {
      if (selectedDeals.includes(deal.id)) {
        onDealToggle(deal.id);
      }
    });
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
      
      {/* Search and Actions */}
      <div className="card mb-3">
        <div className="card-body">
          <div className="row g-3 align-items-end">
            {/* Search */}
            <div className="col-md-6">
              <label htmlFor="dealSearch" className="form-label">Search Deals ({deals.length} total)</label>
              <div className="input-group">
                <span className="input-group-text"><i className="bi bi-search"></i></span>
                <input
                  type="text"
                  id="dealSearch"
                  className="form-control"
                  placeholder="Search by deal number or name..."
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                />
                {searchText && (
                  <button
                    className="btn btn-outline-secondary"
                    type="button"
                    onClick={() => setSearchText('')}
                  >
                    <i className="bi bi-x"></i>
                  </button>
                )}
              </div>
            </div>
            
            {/* Actions */}
            <div className="col-md-6">
              <div className="d-flex gap-2 justify-content-end">
                <button
                  type="button"
                  className="btn btn-outline-primary btn-sm"
                  onClick={handleSelectAllVisible}
                  disabled={paginatedDeals.length === 0}
                >
                  <i className="bi bi-check-all"></i> Select All Visible
                </button>
                <button
                  type="button"
                  className="btn btn-outline-secondary btn-sm"
                  onClick={handleDeselectAllVisible}
                  disabled={paginatedDeals.length === 0}
                >
                  <i className="bi bi-x-square"></i> Deselect All Visible
                </button>
              </div>
            </div>
          </div>
          
          {/* Search Results Info */}
          <div className="d-flex justify-content-between align-items-center mt-3">
            <span className="text-muted">
              {searchText 
                ? `Found ${filteredDeals.length} of ${deals.length} deals`
                : `Showing all ${deals.length} deals`
              }
            </span>
            {totalPages > 1 && (
              <span className="text-muted">
                Page {currentPage} of {totalPages}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Selected Deals Summary */}
      {selectedDeals.length > 0 && (
        <div className="card mb-3 border-primary">
          <div className="card-header bg-primary text-white">
            <h6 className="mb-0">
              <i className="bi bi-check-circle me-2"></i>
              Selected Deals ({selectedDeals.length})
            </h6>
          </div>
          <div className="card-body">
            <div className="d-flex flex-wrap gap-2">
              {selectedDeals.map(dealId => {
                const deal = deals.find(d => d.id === dealId);
                if (!deal) return null;
                return (
                  <span key={dealId} className="badge bg-primary fs-6 p-2">
                    {deal.id}: {deal.name}
                    <button
                      type="button"
                      className="btn-close btn-close-white btn-sm ms-2"
                      onClick={() => onDealToggle(dealId)}
                      aria-label="Remove"
                    ></button>
                  </span>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Deals List */}
      {filteredDeals.length === 0 ? (
        <div className="alert alert-warning">
          <i className="bi bi-search me-2"></i>
          No deals match your search "{searchText}". Try adjusting your search terms.
        </div>
      ) : (
        <>
          {/* Pagination Info */}
          {totalPages > 1 && (
            <div className="d-flex justify-content-between align-items-center mb-3">
              <span className="text-muted">
                Showing {startIndex} to {endIndex} of {filteredDeals.length} deals
              </span>
            </div>
          )}

          {/* Deals Grid - Compact Cards */}
          <div className="row">
            {paginatedDeals.map(deal => (
              <div key={deal.id} className="col-md-4 col-lg-3 mb-3">
                <div className={`card h-100 ${selectedDeals.includes(deal.id) ? 'border-primary bg-light' : ''}`}>
                  <div className="card-body p-3">
                    <div className="form-check">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id={`deal-${deal.id}`}
                        checked={selectedDeals.includes(deal.id)}
                        onChange={() => onDealToggle(deal.id)}
                      />
                      <label className="form-check-label" htmlFor={`deal-${deal.id}`}>
                        <div className="fw-bold text-truncate" title={deal.name}>
                          {deal.name}
                        </div>
                        <div className="small text-muted text-truncate" title={deal.name}>
                          {deal.name}
                        </div>
                      </label>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <nav aria-label="Deal pagination" className="mt-4">
              <ul className="pagination justify-content-center">
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
                
                {/* Page Numbers */}
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let startPage = Math.max(1, currentPage - 2);
                  let endPage = Math.min(totalPages, startPage + 4);
                  
                  if (endPage - startPage < 4) {
                    startPage = Math.max(1, endPage - 4);
                  }
                  
                  const pageNum = i + startPage;
                  
                  if (pageNum <= endPage) {
                    return (
                      <li key={pageNum} className={`page-item ${pageNum === currentPage ? 'active' : ''}`}>
                        <button
                          className="page-link"
                          onClick={() => setCurrentPage(pageNum)}
                        >
                          {pageNum}
                        </button>
                      </li>
                    );
                  }
                  return null;
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
          )}
        </>
      )}

      {/* Final Selection Summary */}
      <div className="alert alert-success mt-4">
        <i className="bi bi-check-circle me-2"></i>
        <strong>Selected {selectedDeals.length} deal{selectedDeals.length !== 1 ? 's' : ''}</strong>
      </div>
    </div>
  );
};

export default DealSelector;