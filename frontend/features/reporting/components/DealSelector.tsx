import React, { useState, useMemo, useRef, useEffect } from 'react';
import type { Deal } from '@/types';

interface DealSelectorProps {
  deals: Deal[];
  selectedDeals: number[];
  onDealToggle: (dlNbr: number) => void;
  onSelectAllDeals: () => void;
  loading?: boolean;
}

const DealSelector: React.FC<DealSelectorProps> = ({
  deals,
  selectedDeals,
  onDealToggle,
  onSelectAllDeals,
  loading = false
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortField, setSortField] = useState<'deal_number' | 'issuer_code' | 'cdi_file' | 'cdb_file'>('deal_number');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [selectedIssuer, setSelectedIssuer] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(50);
  const masterCheckboxRef = useRef<HTMLInputElement>(null);

  // Get unique issuers for the filter dropdown
  const uniqueIssuers = useMemo(() => {
    const issuers = Array.from(new Set(deals.map(deal => deal.issr_cde))).sort();
    return issuers;
  }, [deals]);
  // Filter and sort deals
  const filteredAndSortedDeals = useMemo(() => {
    let filtered = deals.filter(deal => {
      const searchLower = searchTerm.toLowerCase();
      const matchesSearch = (
        deal.dl_nbr.toString().includes(searchLower) ||
        deal.issr_cde.toLowerCase().includes(searchLower) ||
        deal.cdi_file_nme.toLowerCase().includes(searchLower) ||
        (deal.CDB_cdi_file_nme && deal.CDB_cdi_file_nme.toLowerCase().includes(searchLower))
      );
      
      const matchesIssuer = selectedIssuer === '' || deal.issr_cde === selectedIssuer;
      
      return matchesSearch && matchesIssuer;
    });

    // Sort deals
    filtered.sort((a, b) => {
      let aValue: any, bValue: any;
      
      switch (sortField) {
        case 'deal_number':
          aValue = a.dl_nbr;
          bValue = b.dl_nbr;
          break;
        case 'issuer_code':
          aValue = a.issr_cde;
          bValue = b.issr_cde;
          break;
        case 'cdi_file':
          aValue = a.cdi_file_nme;
          bValue = b.cdi_file_nme;
          break;
        case 'cdb_file':
          aValue = a.CDB_cdi_file_nme || '';
          bValue = b.CDB_cdi_file_nme || '';
          break;
        default:
          aValue = a.dl_nbr;
          bValue = b.dl_nbr;
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        const comparison = aValue.localeCompare(bValue);
        return sortDirection === 'asc' ? comparison : -comparison;
      } else {
        const comparison = aValue - bValue;
        return sortDirection === 'asc' ? comparison : -comparison;
      }
    });    return filtered;
  }, [deals, searchTerm, sortField, sortDirection, selectedIssuer]);

  // Pagination
  const totalPages = Math.ceil(filteredAndSortedDeals.length / itemsPerPage);
  const paginatedDeals = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return filteredAndSortedDeals.slice(startIndex, startIndex + itemsPerPage);
  }, [filteredAndSortedDeals, currentPage, itemsPerPage]);

  // Update master checkbox state
  useEffect(() => {
    if (masterCheckboxRef.current) {
      const visibleDealNumbers = paginatedDeals.map(deal => deal.dl_nbr);
      const selectedVisibleDeals = visibleDealNumbers.filter(dlNbr => selectedDeals.includes(dlNbr));
      
      if (selectedVisibleDeals.length === 0) {
        masterCheckboxRef.current.checked = false;
        masterCheckboxRef.current.indeterminate = false;
      } else if (selectedVisibleDeals.length === visibleDealNumbers.length) {
        masterCheckboxRef.current.checked = true;
        masterCheckboxRef.current.indeterminate = false;
      } else {
        masterCheckboxRef.current.checked = false;
        masterCheckboxRef.current.indeterminate = true;
      }
    }
  }, [paginatedDeals, selectedDeals]);

  // Handle sorting
  const handleSort = (field: typeof sortField) => {
    if (field === sortField) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
    setCurrentPage(1);
  };

  const getSortIcon = (field: typeof sortField) => {
    if (field !== sortField) return ' ↕️';
    return sortDirection === 'asc' ? ' ↑' : ' ↓';
  };

  // Handle master checkbox toggle
  const handleMasterToggle = () => {
    const visibleDealNumbers = paginatedDeals.map(deal => deal.dl_nbr);
    const selectedVisibleDeals = visibleDealNumbers.filter(dlNbr => selectedDeals.includes(dlNbr));
    
    if (selectedVisibleDeals.length === visibleDealNumbers.length) {
      // All visible deals are selected, so unselect them
      visibleDealNumbers.forEach(dlNbr => {
        if (selectedDeals.includes(dlNbr)) {
          onDealToggle(dlNbr);
        }
      });
    } else {
      // Not all visible deals are selected, so select all visible deals
      visibleDealNumbers.forEach(dlNbr => {
        if (!selectedDeals.includes(dlNbr)) {
          onDealToggle(dlNbr);
        }
      });
    }
  };

  // Handle pagination
  const handlePageChange = (newPage: number) => {
    setCurrentPage(Math.max(1, Math.min(newPage, totalPages)));
  };

  if (loading) {
    return (
      <div className="card">
        <div className="card-header">
          <h5 className="mb-0">Select Deals</h5>
        </div>
        <div className="card-body">
          <div className="d-flex justify-content-center p-4">
            <div className="spinner-border" role="status">
              <span className="visually-hidden">Loading deals...</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">
        <div className="d-flex justify-content-between align-items-center">
          <h5 className="mb-0">Select Deals</h5>
          <div className="d-flex gap-2">
            <span className="badge bg-secondary">
              {selectedDeals.length} selected
            </span>
            <span className="badge bg-info">
              {filteredAndSortedDeals.length} total
            </span>
          </div>
        </div>
      </div>
      
      <div className="card-body">        {/* Search and Controls */}
        <div className="row mb-3">
          <div className="col-md-3">
            <input
              type="text"
              className="form-control"
              placeholder="Search deals..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
            />
          </div>
          <div className="col-md-2">
            <select
              className="form-select"
              value={selectedIssuer}
              onChange={(e) => {
                setSelectedIssuer(e.target.value);
                setCurrentPage(1);
              }}
            >
              <option value="">All Issuers</option>
              {uniqueIssuers.map(issuer => (
                <option key={issuer} value={issuer}>{issuer}</option>
              ))}
            </select>
          </div>
          <div className="col-md-2">
          </div>
          <div className="col-md-2">
            <select
              className="form-select"
              value={itemsPerPage}
              onChange={(e) => {
                setItemsPerPage(Number(e.target.value));
                setCurrentPage(1);
              }}
            >
              <option value={25}>25 per page</option>
              <option value={50}>50 per page</option>
              <option value={100}>100 per page</option>
            </select>
          </div>
          <div className="col-md-3">
            <div className="d-flex gap-2">
              <button
                className="btn btn-outline-secondary btn-sm"
                onClick={() => {
                  setSearchTerm('');
                  setSelectedIssuer('');
                  setCurrentPage(1);
                }}
                disabled={searchTerm === '' && selectedIssuer === ''}
              >
                Clear Filters
              </button>
              <button
                className="btn btn-outline-primary"
                onClick={onSelectAllDeals}
                disabled={deals.length === 0}
              >
                Select All
              </button>
            </div>
          </div>
        </div>

        {/* Deals Table */}
        <div className="table-responsive">
          <table className="table table-hover">
            <thead>
              <tr>
                <th style={{ width: '50px' }}>
                  <input
                    ref={masterCheckboxRef}
                    type="checkbox"
                    className="form-check-input"
                    onChange={handleMasterToggle}
                    disabled={paginatedDeals.length === 0}
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
                  onClick={() => handleSort('cdi_file')}
                  style={{ cursor: 'pointer' }}
                >
                  CDI File{getSortIcon('cdi_file')}
                </th>
                <th 
                  className="sortable"
                  onClick={() => handleSort('cdb_file')}
                  style={{ cursor: 'pointer' }}
                >
                  CDB File{getSortIcon('cdb_file')}
                </th>
                <th style={{ width: '100px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {paginatedDeals.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-4">
                    {searchTerm ? 'No deals found matching your search.' : 'No deals available.'}
                  </td>
                </tr>
              ) : (
                paginatedDeals.map((deal) => (
                  <tr key={deal.dl_nbr}>
                    <td>
                      <input
                        type="checkbox"
                        className="form-check-input"
                        checked={selectedDeals.includes(deal.dl_nbr)}
                        onChange={() => onDealToggle(deal.dl_nbr)}
                      />
                    </td>
                    <td>{deal.dl_nbr}</td>
                    <td>{deal.issr_cde}</td>
                    <td>{deal.cdi_file_nme}</td>
                    <td>{deal.CDB_cdi_file_nme || '-'}</td>
                    <td>
                      <button
                        className="btn btn-sm btn-outline-primary"
                        onClick={() => onDealToggle(deal.dl_nbr)}
                      >
                        {selectedDeals.includes(deal.dl_nbr) ? 'Remove' : 'Add'}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="d-flex justify-content-between align-items-center mt-3">
            <div>
              Showing {Math.min((currentPage - 1) * itemsPerPage + 1, filteredAndSortedDeals.length)} to{' '}
              {Math.min(currentPage * itemsPerPage, filteredAndSortedDeals.length)} of{' '}
              {filteredAndSortedDeals.length} deals
            </div>
            <nav>
              <ul className="pagination mb-0">
                <li className={`page-item ${currentPage === 1 ? 'disabled' : ''}`}>
                  <button
                    className="page-link"
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                  >
                    Previous
                  </button>
                </li>
                
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
                        onClick={() => handlePageChange(pageNum)}
                      >
                        {pageNum}
                      </button>
                    </li>
                  );
                })}
                
                <li className={`page-item ${currentPage === totalPages ? 'disabled' : ''}`}>
                  <button
                    className="page-link"
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage === totalPages}
                  >
                    Next
                  </button>
                </li>
              </ul>
            </nav>
          </div>
        )}
      </div>
    </div>
  );
};

export default DealSelector;