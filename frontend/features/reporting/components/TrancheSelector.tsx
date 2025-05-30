import React, { useState, useMemo, useRef, useEffect } from 'react';
import type { Deal, TrancheReportSummary } from '@/types';

interface TrancheSelectorProps {
  deals: Deal[];
  selectedDeals: number[];
  tranches: Record<number, TrancheReportSummary[]>;
  selectedTranches: Record<number, string[]>;
  onTrancheToggle: (dlNbr: number, trId: string) => void;
  onSelectAllTranches: (dlNbr: number) => void;
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
  const [sortField, setSortField] = useState<'deal_number' | 'tr_id' | 'issuer_code'>('deal_number');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [selectedDealFilter, setSelectedDealFilter] = useState<number | 'all'>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(50);
  const masterCheckboxRef = useRef<HTMLInputElement>(null);

  // Get sort icon for table headers
  const getSortIcon = (field: string) => {
    if (sortField !== field) {
      return <i className="bi bi-chevron-expand ms-1"></i>;
    }
    return <i className={`bi bi-chevron-${sortDirection === 'asc' ? 'up' : 'down'} ms-1`}></i>;
  };
  // Create flat list of all tranches with deal info
  const allTranches = useMemo(() => {
    const trancheList: Array<TrancheReportSummary & { deal: Deal; dlNbr: number }> = [];
    
    selectedDeals.forEach(dlNbr => {
      const deal = deals.find(d => d.dl_nbr === dlNbr);
      const dealTranches = tranches[dlNbr] || [];
      
      if (deal) {
        dealTranches.forEach(tranche => {
          trancheList.push({
            ...tranche,
            deal,
            dlNbr: tranche.dl_nbr
          });
        });
      }
    });
    
    return trancheList;
  }, [selectedDeals, deals, tranches]);

  // Filter and sort tranches
  const filteredAndSortedTranches = useMemo(() => {
    let filtered = allTranches;    // Apply search filter
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      filtered = filtered.filter(tranche => 
        tranche.tr_id.toLowerCase().includes(search) ||
        tranche.dl_nbr.toString().includes(search) ||
        tranche.deal.issr_cde.toLowerCase().includes(search) ||
        tranche.deal.cdi_file_nme?.toLowerCase().includes(search) ||
        tranche.deal.CDB_cdi_file_nme?.toLowerCase().includes(search)
      );
    }

    // Apply deal filter
    if (selectedDealFilter !== 'all') {
      filtered = filtered.filter(tranche => tranche.dlNbr === selectedDealFilter);
    }

    // Sort
    filtered.sort((a, b) => {
      let aValue: any;
      let bValue: any;

      switch (sortField) {
        case 'deal_number':
          aValue = a.deal.dl_nbr;
          bValue = b.deal.dl_nbr;
          break;        case 'tr_id':
          aValue = a.tr_id;
          bValue = b.tr_id;
          break;
        case 'issuer_code':
          aValue = a.deal.issr_cde;
          bValue = b.deal.issr_cde;
          break;
        default:
          aValue = a.tr_id;
          bValue = b.tr_id;
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

  // Handle select all visible tranches
  const handleSelectAllVisible = () => {
    const visibleTranches = paginatedTranches;
    const allVisibleSelected = visibleTranches.every(tranche => 
      (selectedTranches[tranche.dlNbr] || []).includes(tranche.tr_id)
    );
    
    if (allVisibleSelected) {
      // Unselect all visible tranches
      visibleTranches.forEach(tranche => {
        if ((selectedTranches[tranche.dlNbr] || []).includes(tranche.tr_id)) {
          onTrancheToggle(tranche.dlNbr, tranche.tr_id);
        }
      });
    } else {
      // Select all visible tranches
      visibleTranches.forEach(tranche => {
        if (!(selectedTranches[tranche.dlNbr] || []).includes(tranche.tr_id)) {
          onTrancheToggle(tranche.dlNbr, tranche.tr_id);
        }
      });
    }
  };

  // Handle select all tranches for a deal
  const handleDealSelectAll = (dlNbr: number) => {
    onSelectAllTranches(dlNbr);
  };

  // Clear all filters
  const clearFilters = () => {
    setSearchTerm('');
    setSelectedDealFilter('all');
  };

  if (loading) {
    return (
      <div className="text-center p-4">
        <div className="spinner-border" role="status">
          <span className="visually-hidden">Loading tranches...</span>
        </div>
      </div>
    );
  }

  const allVisibleSelected = paginatedTranches.length > 0 && 
    paginatedTranches.every(tranche => (selectedTranches[tranche.dlNbr] || []).includes(tranche.tr_id));

  return (
    <div>
      {/* Controls */}
      <div className="row mb-3">
        <div className="col-md-4">
          <input
            type="text"
            className="form-control"
            placeholder="Search tranches..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="col-md-3">          <select
            className="form-select"
            value={selectedDealFilter}
            onChange={(e) => setSelectedDealFilter(e.target.value === 'all' ? 'all' : Number(e.target.value))}
          >
            <option value="all">All Deals</option>
            {selectedDeals.map(dlNbr => {
              const deal = deals.find(d => d.dl_nbr === dlNbr);
              return deal ? (
                <option key={dlNbr} value={dlNbr}>{deal.dl_nbr} - {deal.issr_cde}</option>
              ) : null;
            })}
          </select>
        </div>
        <div className="col-md-2">
          <select
            className="form-select"
            value={itemsPerPage}
            onChange={(e) => setItemsPerPage(Number(e.target.value))}
          >
            <option value={25}>25 per page</option>
            <option value={50}>50 per page</option>
            <option value={100}>100 per page</option>
          </select>
        </div>
        <div className="col-md-3">
          <div className="btn-group w-100">
            <button
              className="btn btn-outline-primary"
              onClick={handleSelectAllVisible}
              disabled={paginatedTranches.length === 0}
            >
              {allVisibleSelected ? 'Deselect All' : 'Select All'}
            </button>
            <button
              className="btn btn-outline-secondary"
              onClick={clearFilters}
            >
              Clear Filters
            </button>
          </div>
        </div>
      </div>

      {/* Tranches Table */}
      <div className="table-responsive">
        <table className="table table-hover">
          <thead className="table-light">
            <tr>
              <th style={{ width: '40px' }}>
                <input
                  type="checkbox"
                  className="form-check-input"
                  ref={masterCheckboxRef}
                  checked={allVisibleSelected}
                  onChange={handleSelectAllVisible}
                />
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('deal_number')}
                style={{ cursor: 'pointer' }}
              >
                Deal Number{getSortIcon('deal_number')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('issuer_code')}
                style={{ cursor: 'pointer' }}
              >
                Issuer Code{getSortIcon('issuer_code')}
              </th>
              <th 
                className="sortable"
                onClick={() => handleSort('tr_id')}
                style={{ cursor: 'pointer' }}
              >
                Tranche ID{getSortIcon('tr_id')}
              </th>
              <th style={{ width: '100px' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {paginatedTranches.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center py-4 text-muted">
                  No tranches found matching your search criteria.
                </td>
              </tr>
            ) : (
              paginatedTranches.map((tranche) => {
                const isSelected = (selectedTranches[tranche.dlNbr] || []).includes(tranche.tr_id);
                return (
                  <tr
                    key={`${tranche.dlNbr}-${tranche.tr_id}`}
                    className={isSelected ? 'table-primary' : ''}
                    onClick={() => onTrancheToggle(tranche.dlNbr, tranche.tr_id)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td>
                      <input
                        type="checkbox"
                        className="form-check-input"
                        checked={isSelected}
                        onChange={() => onTrancheToggle(tranche.dlNbr, tranche.tr_id)}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </td>
                    <td>
                      <div className="fw-bold">{tranche.deal.dl_nbr}</div>
                      <div className="small text-muted">{tranche.deal.cdi_file_nme || '-'}</div>
                    </td>
                    <td>{tranche.deal.issr_cde}</td>
                    <td>
                      <div className="fw-bold">{tranche.tr_id}</div>
                    </td>
                    <td>
                      <button
                        className="btn btn-sm btn-outline-primary"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDealSelectAll(tranche.dlNbr);
                        }}
                        title={`Select all tranches for ${tranche.deal.dl_nbr}`}
                      >
                        Select All
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination and Summary */}
      <div className="row align-items-center mt-3">
        <div className="col-sm-6">
          <span className="text-muted">
            Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, filteredAndSortedTranches.length)} of {filteredAndSortedTranches.length} tranches
            ({
              paginatedTranches.filter(tranche => 
                (selectedTranches[tranche.dlNbr] || []).includes(tranche.tr_id)
              ).length
            } of {filteredAndSortedTranches.length} visible selected)
          </span>
        </div>
        <div className="col-sm-6">
          {totalPages > 1 && (
            <nav>
              <ul className="pagination justify-content-end mb-0">
                <li className={`page-item ${currentPage === 1 ? 'disabled' : ''}`}>
                  <button
                    className="page-link"
                    onClick={() => setCurrentPage(currentPage - 1)}
                    disabled={currentPage === 1}
                  >
                    Previous
                  </button>
                </li>
                
                {/* Page numbers */}
                {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
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
                    Next
                  </button>
                </li>
              </ul>
            </nav>
          )}
        </div>
      </div>
    </div>
  );
};

export default TrancheSelector;
