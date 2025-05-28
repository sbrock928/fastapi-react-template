import React, { useState, useMemo, useRef, useEffect } from 'react';
import type { Deal, TrancheReportSummary } from '@/types';
import styles from '@/styles/components/TrancheSelector.module.css';

interface TrancheSelectorProps {
  deals: Deal[];
  selectedDeals: number[];
  tranches: Record<number, TrancheReportSummary[]>;
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
  const [sortField, setSortField] = useState<'deal_name' | 'tranche_name' | 'principal_amount' | 'interest_rate' | 'payment_priority' | 'class_name' | 'credit_rating'>('deal_name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [selectedDealFilter, setSelectedDealFilter] = useState<number | 'all'>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(50); // Default to 50 items per page
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

  // Get sort icon for table headers
  const getSortIcon = (field: string) => {
    if (sortField !== field) {
      return <i className="bi bi-chevron-expand ms-1"></i>;
    }
    return <i className={`bi bi-chevron-${sortDirection === 'asc' ? 'up' : 'down'} ms-1`}></i>;
  };

  // Create flat list of all tranches with deal info
  const allTranches = useMemo(() => {
    const trancheList: Array<TrancheReportSummary & { deal: Deal; dealId: number }> = [];
    
    selectedDeals.forEach(dealId => {
      const deal = deals.find(d => d.id === dealId);
      const dealTranches = tranches[dealId] || [];
      
      if (deal) {
        dealTranches.forEach(tranche => {
          trancheList.push({
            ...tranche,
            deal,
            dealId: tranche.deal_id // Use deal_id from TrancheReportSummary
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
          aValue = a.payment_priority || 1; // Default to 1 if not available
          bValue = b.payment_priority || 1;
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

  // Paginate the filtered results
  const paginatedTranches = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return filteredAndSortedTranches.slice(startIndex, endIndex);
  }, [filteredAndSortedTranches, currentPage, itemsPerPage]);

  const totalPages = Math.ceil(filteredAndSortedTranches.length / itemsPerPage);

  const handleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, selectedDealFilter, sortField, sortDirection]);

  // Bulk selection handlers
  const handleSelectAll = () => {
    paginatedTranches.forEach(tranche => {
      const selectedDealTranches = selectedTranches[tranche.dealId] || [];
      if (!selectedDealTranches.includes(tranche.id)) {
        onTrancheToggle(tranche.dealId, tranche.id);
      }
    });
  };

  const handleDeselectAll = () => {
    paginatedTranches.forEach(tranche => {
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
  
  // Update selection calculations to work with paginated data
  const { allVisibleSelected, someVisibleSelected } = useMemo(() => {
    if (paginatedTranches.length === 0) {
      return { allVisibleSelected: false, someVisibleSelected: false };
    }
    
    let selectedCount = 0;
    for (const tranche of paginatedTranches) {
      if ((selectedTranches[tranche.dealId] || []).includes(tranche.id)) {
        selectedCount++;
      }
    }
    
    return {
      allVisibleSelected: selectedCount === paginatedTranches.length,
      someVisibleSelected: selectedCount > 0 && selectedCount < paginatedTranches.length
    };
  }, [paginatedTranches, selectedTranches]);

  // Debounce the useEffect to prevent too many DOM updates
  const timeoutRef = useRef<NodeJS.Timeout>();
  
  useEffect(() => {
    // Clear any existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    
    // Debounce the DOM update
    timeoutRef.current = setTimeout(() => {
      if (masterCheckboxRef.current) {
        try {
          masterCheckboxRef.current.indeterminate = someVisibleSelected && !allVisibleSelected;
        } catch (error) {
          console.warn('Error updating checkbox indeterminate state:', error);
        }
      }
    }, 10); // Small delay to batch updates
    
    // Cleanup function
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [allVisibleSelected, someVisibleSelected]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return (
    <div>
      <h5 className="mb-3">Step 3: Select Tranches</h5>
      <p className="text-muted">Choose which tranches to include in your report template for the selected deals.</p>
      
      {/* Search and Filter Controls */}
      <div className="card mb-3">
        <div className="card-body">
          <div className="row g-3">
            <div className="col-md-3">
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
            <div className="col-md-2">
              <select
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
            <div className="col-md-4">
              <div className="btn-group" role="group">
                <button
                  type="button"
                  className="btn btn-outline-primary btn-sm"
                  onClick={handleSelectAll}
                  disabled={allVisibleSelected}
                >
                  <i className="bi bi-check-all"></i> Select Page ({paginatedTranches.length})
                </button>
                <button
                  type="button"
                  className="btn btn-outline-secondary btn-sm"
                  onClick={handleDeselectAll}
                >
                  <i className="bi bi-x-square"></i> Deselect Page
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
              Showing {Math.min((currentPage - 1) * itemsPerPage + 1, totalVisible)}-{Math.min(currentPage * itemsPerPage, totalVisible)} of {totalVisible} tranches
              {allTranches.length !== totalVisible && ` (${allTranches.length} total)`}
            </div>
          </div>
        </div>
        <div className="card-body p-0">
          <div className={styles.tableContainer}>
            <table className="table table-sm table-hover mb-0">
              <thead className={styles.tableHeader}>
                <tr>
                  <th className={styles.headerMinWidth40}>
                    <input
                      ref={masterCheckboxRef}
                      type="checkbox"
                      className="form-check-input"
                      checked={allVisibleSelected}
                      onChange={allVisibleSelected ? handleDeselectAll : handleSelectAll}
                    />
                  </th>
                  <th 
                    className={`${styles.sortableHeader} ${styles.headerMinWidth200}`} 
                    onClick={() => handleSort('deal_name')}
                  >
                    Deal
                    {sortField === 'deal_name' && (
                      <i className={`bi bi-chevron-${sortDirection === 'asc' ? 'up' : 'down'} ms-1`}></i>
                    )}
                  </th>
                  <th 
                    className={`${styles.sortableHeader} ${styles.headerMinWidth150}`} 
                    onClick={() => handleSort('tranche_name')}
                  >
                    Tranche
                    {sortField === 'tranche_name' && (
                      <i className={`bi bi-chevron-${sortDirection === 'asc' ? 'up' : 'down'} ms-1`}></i>
                    )}
                  </th>
                  <th className={`${styles.headerMinWidth80}`} onClick={() => handleSort('class_name')}>
                    Class {getSortIcon('class_name')}
                  </th>
                  <th 
                    className={`${styles.sortableHeader} ${styles.headerMinWidth120} text-end`} 
                    onClick={() => handleSort('principal_amount')}
                  >
                    Principal
                    {sortField === 'principal_amount' && (
                      <i className={`bi bi-chevron-${sortDirection === 'asc' ? 'up' : 'down'} ms-1`}></i>
                    )}
                  </th>
                  <th 
                    className={`${styles.sortableHeader} ${styles.headerMinWidth100} text-end`} 
                    onClick={() => handleSort('interest_rate')}
                  >
                    Rate
                    {sortField === 'interest_rate' && (
                      <i className={`bi bi-chevron-${sortDirection === 'asc' ? 'up' : 'down'} ms-1`}></i>
                    )}
                  </th>
                  <th className={`${styles.headerMinWidth80}`} onClick={() => handleSort('credit_rating')}>
                    Rating {getSortIcon('credit_rating')}
                  </th>
                  <th 
                    className={`${styles.sortableHeader} ${styles.headerMinWidth80} text-center`} 
                    onClick={() => handleSort('payment_priority')}
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
                {paginatedTranches.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="text-center text-muted py-4">
                      <i className="bi bi-search me-2"></i>
                      No tranches match your search criteria
                    </td>
                  </tr>
                ) : (
                  paginatedTranches.map(tranche => {
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