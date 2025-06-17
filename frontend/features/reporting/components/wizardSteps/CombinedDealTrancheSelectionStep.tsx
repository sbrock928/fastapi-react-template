import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { useApiRequest } from '@/hooks';
import reportingApi from '@/services/reportingApi';
import { useToast } from '@/context/ToastContext';
import type { Deal, TrancheReportSummary } from '@/types/reporting';

// Utility function to handle tranche ID trimming consistently
const normalizeTrancheId = (trId: string): string => {
  return trId?.trim() || '';
};

// Utility function to check if two tranche IDs match (handling padding)
const trancheIdsMatch = (trId1: string, trId2: string): boolean => {
  return normalizeTrancheId(trId1) === normalizeTrancheId(trId2);
};

interface CombinedDealTrancheSelectionStepProps {
  reportScope: 'DEAL' | 'TRANCHE' | '';
  selectedDeals: number[];
  selectedTranches: Record<number, string[]>;
  tranches: Record<number, TrancheReportSummary[]>;
  dealsBeingAdded: Set<number>;
  onDealAdd: (dlNbr: number) => void;
  onDealRemove: (dlNbr: number) => void;
  onTrancheToggle: (dlNbr: number, trId: string) => void;
  onSelectAllTranches: (dlNbr: number) => void;
  onDeselectAllTranches: (dlNbr: number) => void;
  loading: boolean;
}

const CombinedDealTrancheSelectionStep: React.FC<CombinedDealTrancheSelectionStepProps> = ({
  reportScope,
  selectedDeals,
  selectedTranches,
  tranches,
  dealsBeingAdded,
  onDealAdd,
  onDealRemove,
  onTrancheToggle,
  onSelectAllTranches,
  onDeselectAllTranches,
  loading,
}) => {
  const { showToast } = useToast();

  // State for deal search and filtering
  const [selectedIssuerCode, setSelectedIssuerCode] = useState<string>('');
  const [dealSearchTerm, setDealSearchTerm] = useState<string>('');
  const [dealSearchResults, setDealSearchResults] = useState<Deal[]>([]);
  const [isSearching, setIsSearching] = useState<boolean>(false);
  
  // State for table view management
  const [trancheFilter, setTrancheFilter] = useState<string>('');
  const [selectedDealFilter, setSelectedDealFilter] = useState<number | 'all'>('all');

  // State for hybrid card-table view management
  const [expandedDeals, setExpandedDeals] = useState<Set<number>>(new Set());
  const [trancheSearchTerms, setTrancheSearchTerms] = useState<Record<number, string>>({});

  // NEW: State to cache deal information for selected deals
  const [dealInfoCache, setDealInfoCache] = useState<Record<number, Deal>>({});

  // Load issuer codes using our anti-spam hook
  const {
    data: issuerCodes,
    error: issuerCodesError
  } = useApiRequest<string[]>(
    () => reportingApi.getIssuerCodes(),
    [], // No dependencies - load once on mount
    {
      immediate: true,
      throttleMs: 2000, // 2 second throttle between requests
      maxRetries: 2,
      retryDelayMs: 1000
    }
  );

  // Show error toast if issuer codes fail to load
  useEffect(() => {
    if (issuerCodesError) {
      showToast(`Error loading issuer codes: ${issuerCodesError}`, 'error');
    }
  }, [issuerCodesError, showToast]);

  // Search for deals based on issuer and search term
  const searchDeals = useCallback(async () => {
    if (!selectedIssuerCode || !dealSearchTerm.trim()) {
      setDealSearchResults([]);
      return;
    }

    setIsSearching(true);
    try {
      const response = await reportingApi.getDeals(selectedIssuerCode);
      const searchLower = dealSearchTerm.toLowerCase();
      
      const filtered = response.data.filter((deal: Deal) => 
        deal.dl_nbr.toString().includes(searchLower) ||
        deal.cdi_file_nme.toLowerCase().includes(searchLower) ||
        deal.CDB_cdi_file_nme?.toLowerCase().includes(searchLower)
      );
      
      setDealSearchResults(filtered);
    } catch (error) {
      console.error('Error searching deals:', error);
      showToast('Error searching deals', 'error');
      setDealSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  }, [selectedIssuerCode, dealSearchTerm, showToast]);

  // Debounced search effect
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      searchDeals();
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchDeals]);

  // Create hybrid card-table data from selected deals
  const cardTableData = useMemo(() => {
    return selectedDeals.map(dlNbr => {
      const dealTranches = tranches[dlNbr] || [];
      const selectedTrancheIds = selectedTranches[dlNbr] || [];
      const deal = dealInfoCache[dlNbr] || 
        dealSearchResults.find(d => d.dl_nbr === dlNbr) || {
          dl_nbr: dlNbr,
          issr_cde: 'Loading...',
          cdi_file_nme: 'Loading...',
          CDB_cdi_file_nme: null
        };

      // Filter tranches based on search term for this specific deal
      const searchTerm = trancheSearchTerms[dlNbr];
      const filteredTranches = searchTerm?.trim() 
        ? dealTranches.filter(tranche => 
            tranche.tr_id.toLowerCase().includes(searchTerm.toLowerCase())
          )
        : dealTranches;

      // Sort tranches within the deal
      const sortedTranches = [...filteredTranches].sort((a, b) => {
        return a.tr_id.localeCompare(b.tr_id);
      });

      return {
        dlNbr,
        deal,
        totalTranches: dealTranches.length,
        filteredTranches: sortedTranches,
        selectedTranches: selectedTrancheIds.length,
        isExpanded: expandedDeals.has(dlNbr)
      };
    });
  }, [selectedDeals, tranches, selectedTranches, dealInfoCache, dealSearchResults, expandedDeals, trancheSearchTerms]);

  // Get summary statistics
  const summaryStats = useMemo(() => {
    const totalTranches = cardTableData.reduce((sum, row) => sum + row.totalTranches, 0);
    const selectedCount = cardTableData.reduce((sum, row) => sum + row.selectedTranches, 0);
    const dealCount = cardTableData.length;

    return {
      totalTranches,
      selectedCount,
      dealCount
    };
  }, [cardTableData]);

  // Handle deal-specific bulk operations
  const handleSelectAllForDeal = (dlNbr: number) => {
    onSelectAllTranches(dlNbr);
  };

  const handleDeselectAllForDeal = (dlNbr: number) => {
    onDeselectAllTranches(dlNbr);
  };

  // Update deal info cache when search results change
  useEffect(() => {
    dealSearchResults.forEach(deal => {
      if (selectedDeals.includes(deal.dl_nbr)) {
        setDealInfoCache(prev => ({
          ...prev,
          [deal.dl_nbr]: deal
        }));
      }
    });
  }, [dealSearchResults, selectedDeals]);

  // Load deal information for selected deals that aren't in cache
  useEffect(() => {
    const loadMissingDealInfo = async () => {
      const missingDeals = selectedDeals.filter(dlNbr => !dealInfoCache[dlNbr]);
      
      if (missingDeals.length === 0) return;

      try {
        // Use the API endpoint to fetch deals by numbers directly
        console.log(`🔄 Loading deal info for ${missingDeals.length} deals: ${missingDeals.join(', ')}`);
        const response = await reportingApi.getDealsByNumbers(missingDeals);
        const foundDeals = response.data;

        // Update cache with found deals
        const newCacheEntries: Record<number, Deal> = {};
        foundDeals.forEach(deal => {
          newCacheEntries[deal.dl_nbr] = deal;
        });

        if (Object.keys(newCacheEntries).length > 0) {
          setDealInfoCache(prev => ({
            ...prev,
            ...newCacheEntries
          }));
          console.log(`✅ Loaded deal info for ${Object.keys(newCacheEntries).length} deals efficiently`);
        }
      } catch (error) {
        console.error('Error loading deal information:', error);
      }
    };

    // Load deal info whenever there are selected deals missing from cache
    if (selectedDeals.length > 0) {
      loadMissingDealInfo();
    }
  }, [selectedDeals]); // Run when selectedDeals changes

  // Handle deal addition
  const handleAddDeal = (deal: Deal) => {
    if (!selectedDeals.includes(deal.dl_nbr)) {
      onDealAdd(deal.dl_nbr);
      // Don't auto-expand newly added deals - keep them collapsed by default
      // setExpandedDeals(prev => new Set([...prev, deal.dl_nbr])); // REMOVED
      // REMOVED: Clear search - this was annoying for users selecting multiple deals
      // setDealSearchTerm('');
      // setDealSearchResults([]);
    }
  };

  // Handle deal removal
  const handleRemoveDeal = (dlNbr: number) => {
    onDealRemove(dlNbr);
    // Reset filters if removing the currently filtered deal
    if (selectedDealFilter === dlNbr) {
      setSelectedDealFilter('all');
    }
  };

  // Handle tree expansion toggle
  const toggleExpansion = (dlNbr: number) => {
    setExpandedDeals(prev => {
      const newSet = new Set(prev);
      if (newSet.has(dlNbr)) {
        newSet.delete(dlNbr);
      } else {
        newSet.add(dlNbr);
      }
      return newSet;
    });
  };

  // Check if any deals/tranches are selected
  const hasSelections = selectedDeals.length > 0;

  if (reportScope !== 'DEAL' && reportScope !== 'TRANCHE') {
    return (
      <div className="text-center p-5">
        <div className="alert alert-warning">
          <i className="bi bi-info-circle me-2"></i>
          Please select a report scope first.
        </div>
      </div>
    );
  }

  return (
    <div>
      <h5 className="mb-3">Step 2: Select Deals and Tranches</h5>
      
      {/* Instructions based on report scope */}
      <div className="alert alert-info mb-4">
        <i className="bi bi-info-circle me-2"></i>
        <span>
          <strong>Manual Tranche Selection:</strong> When you add a deal, no tranches are selected by default. 
          You'll need to expand each deal and manually select the tranches you want to include in your report.
          <br />
          <em>Tip: Use the "Select All" button to quickly select all tranches for a deal, or choose individual tranches as needed.</em>
        </span>
      </div>

      {/* Deal Search Section */}
      <div className="card mb-4">
        <div className="card-header" style={{ backgroundColor: '#93186c', color: 'white' }}>
          <h6 className="mb-0">Add Deals to Report</h6>
        </div>
        <div className="card-body">
          <div className="row g-3">
            {/* Issuer Code Filter */}
            <div className="col-md-4">
              <label htmlFor="issuerSelect" className="form-label">Filter by Issuer Code</label>
              <select
                id="issuerSelect"
                className="form-select"
                value={selectedIssuerCode}
                onChange={(e) => setSelectedIssuerCode(e.target.value)}
              >
                <option value="">Select an issuer...</option>
                {issuerCodes && Array.isArray(issuerCodes) && issuerCodes.map((code: string) => (
                  <option key={code} value={code}>{code}</option>
                ))}
              </select>
            </div>

            {/* Deal Search */}
            <div className="col-md-8">
              <label htmlFor="dealSearch" className="form-label">Search for Deal</label>
              <div className="input-group">
                <input
                  id="dealSearch"
                  type="text"
                  className="form-control"
                  placeholder="Search by deal number or CDI file name..."
                  value={dealSearchTerm}
                  onChange={(e) => setDealSearchTerm(e.target.value)}
                  disabled={!selectedIssuerCode}
                />
                {isSearching && (
                  <span className="input-group-text">
                    <div className="spinner-border spinner-border-sm" role="status">
                      <span className="visually-hidden">Searching...</span>
                    </div>
                  </span>
                )}
              </div>
              {!selectedIssuerCode && (
                <div className="form-text">Please select an issuer code first</div>
              )}
            </div>
          </div>

          {/* Search Results */}
          {dealSearchResults.length > 0 && (
            <div className="mt-3">
              <h6>Search Results</h6>
              <div className="list-group">
                {dealSearchResults.map(deal => (
                  <div
                    key={deal.dl_nbr}
                    className={`list-group-item d-flex justify-content-between align-items-center ${
                      selectedDeals.includes(deal.dl_nbr) ? 'list-group-item-success' : ''
                    }`}
                  >
                    <div>
                      <strong>Deal {deal.dl_nbr}</strong>
                      <br />
                      <small className="text-muted">
                        {deal.issr_cde} | {deal.cdi_file_nme}
                        {deal.CDB_cdi_file_nme && ` | ${deal.CDB_cdi_file_nme}`}
                      </small>
                    </div>
                    <button
                      className={`btn btn-sm ${
                        selectedDeals.includes(deal.dl_nbr) 
                          ? 'btn-outline-success disabled' 
                          : dealsBeingAdded.has(deal.dl_nbr)
                          ? 'btn-outline-warning disabled'
                          : 'btn-primary'
                      }`}
                      onClick={() => handleAddDeal(deal)}
                      disabled={selectedDeals.includes(deal.dl_nbr) || dealsBeingAdded.has(deal.dl_nbr)}
                    >
                      {selectedDeals.includes(deal.dl_nbr) ? (
                        <>
                          <i className="bi bi-check-circle me-1"></i>
                          Added
                        </>
                      ) : dealsBeingAdded.has(deal.dl_nbr) ? (
                        <>
                          <div className="spinner-border spinner-border-sm me-1" role="status">
                            <span className="visually-hidden">Loading...</span>
                          </div>
                          Adding...
                        </>
                      ) : (
                        'Add to Report'
                      )}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Selected Deals Hybrid Card-Table View */}
      {hasSelections && (
        <div className="card">
          <div className="card-header" style={{ backgroundColor: '#93186c', color: 'white' }}>
            <h6 className="mb-0">Selected Deals ({selectedDeals.length})</h6>
          </div>
          <div className="card-body">
            {/* Filter and Sort Controls */}
            <div className="row g-3 mb-3">
              {/* Tranche Search */}
              <div className="col-md-6">
                <div className="input-group input-group-sm">
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Search tranches by tr_id..."
                    value={trancheFilter}
                    onChange={(e) => setTrancheFilter(e.target.value)}
                  />
                  {trancheFilter && (
                    <button
                      className="btn btn-outline-secondary"
                      type="button"
                      onClick={() => setTrancheFilter('')}
                      title="Clear search"
                    >
                      <i className="bi bi-x"></i>
                    </button>
                  )}
                </div>
              </div>
              
              {/* Deal Filter */}
              <div className="col-md-6">
                <select
                  className="form-select form-select-sm"
                  value={selectedDealFilter}
                  onChange={(e) => setSelectedDealFilter(e.target.value === 'all' ? 'all' : Number(e.target.value))}
                >
                  <option value="all">All Deals</option>
                  {selectedDeals.map(dlNbr => (
                    <option key={dlNbr} value={dlNbr}>Deal {dlNbr}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Tranche Card-Table */}
            <div className="row g-3">
              {cardTableData.length === 0 && (
                <div className="col-12 text-center text-muted py-3">
                  No deals match your search criteria.
                </div>
              )}
              {cardTableData.map(row => (
                <div key={row.dlNbr} className="card mb-3">
                  <div className="card-header bg-light">
                    <div className="d-flex justify-content-between align-items-center">
                      <div>
                        <h6 className="mb-0">Deal {row.dlNbr}</h6>
                        <span className="badge bg-primary ms-2">
                          {row.selectedTranches}/{row.totalTranches} tranches selected
                        </span>
                      </div>
                      <button
                        className="btn btn-sm btn-outline-secondary"
                        onClick={() => toggleExpansion(row.dlNbr)}
                      >
                        <i className={`bi bi-chevron-${row.isExpanded ? 'down' : 'right'}`}></i>
                      </button>
                    </div>
                  </div>
                  <div className="card-body">
                    {/* Deal details */}
                    <div className="text-muted mb-2">
                      {row.deal.issr_cde} | {row.deal.cdi_file_nme}
                      {row.deal.CDB_cdi_file_nme && ` | ${row.deal.CDB_cdi_file_nme}`}
                    </div>

                    {/* Expanded tranche selection */}
                    {row.isExpanded && (
                      <>
                        {/* Tranche search and bulk actions */}
                        <div className="row g-3 mb-3">
                          <div className="col-md-6">
                            <div className="input-group input-group-sm">
                              <input
                                type="text"
                                className="form-control"
                                placeholder="Search tranches..."
                                value={trancheSearchTerms[row.dlNbr] || ''}
                                onChange={(e) => setTrancheSearchTerms(prev => ({
                                  ...prev,
                                  [row.dlNbr]: e.target.value
                                }))}
                              />
                              {trancheSearchTerms[row.dlNbr] && (
                                <button
                                  className="btn btn-outline-secondary"
                                  type="button"
                                  onClick={() => setTrancheSearchTerms(prev => ({
                                    ...prev,
                                    [row.dlNbr]: ''
                                  }))}
                                  title="Clear search"
                                >
                                  <i className="bi bi-x"></i>
                                </button>
                              )}
                            </div>
                          </div>
                          
                          {/* Bulk Actions for this deal */}
                          <div className="col-md-6">
                            <div className="btn-group" role="group">
                              <button
                                className="btn btn-sm btn-outline-primary"
                                onClick={() => handleSelectAllForDeal(row.dlNbr)}
                              >
                                Select All
                              </button>
                              <button
                                className="btn btn-sm btn-outline-secondary"
                                onClick={() => handleDeselectAllForDeal(row.dlNbr)}
                              >
                                Deselect All
                              </button>
                              <button
                                className="btn btn-sm btn-outline-danger"
                                onClick={() => handleRemoveDeal(row.dlNbr)}
                                title="Remove deal from report"
                              >
                                <i className="bi bi-trash"></i>
                              </button>
                            </div>
                          </div>
                        </div>

                        {/* Tranche Table */}
                        <div className="table-responsive">
                          <table className="table table-sm table-striped">
                            <thead>
                              <tr>
                                <th style={{ width: '60px' }}>Select</th>
                                <th>Tranche ID</th>
                                <th>CUSIP</th>
                              </tr>
                            </thead>
                            <tbody>
                              {row.filteredTranches.length === 0 && (
                                <tr>
                                  <td colSpan={3} className="text-center text-muted py-3">
                                    {trancheSearchTerms[row.dlNbr] 
                                      ? 'No tranches match your search'
                                      : 'No tranches available for this deal'
                                    }
                                  </td>
                                </tr>
                              )}
                              {row.filteredTranches.map(tranche => {
                                const selectedTrancheIds = selectedTranches[row.dlNbr] || [];
                                const isSelected = selectedTrancheIds.some(selectedId => 
                                  trancheIdsMatch(selectedId, tranche.tr_id)
                                );

                                return (
                                  <tr key={`${row.dlNbr}-${tranche.tr_id}`} className={isSelected ? 'table-active' : ''}>
                                    <td className="text-center">
                                      <input
                                        type="checkbox"
                                        className="form-check-input"
                                        checked={isSelected}
                                        onChange={() => onTrancheToggle(row.dlNbr, tranche.tr_id)}
                                      />
                                    </td>
                                    <td>{normalizeTrancheId(tranche.tr_id)}</td>
                                    <td>{tranche.tr_cusip_id || '-'}</td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Summary Stats */}
            <div className="mt-3">
              <strong>Summary:</strong> {summaryStats.dealCount} deals, {summaryStats.totalTranches} tranches total. 
              <br />
              <small className="text-muted">
                {summaryStats.selectedCount} tranches selected.
              </small>
            </div>
          </div>
        </div>
      )}

      {!hasSelections && (
        <div className="text-center text-muted py-5">
          <i className="bi bi-search display-4 d-block mb-3"></i>
          <h5>No deals selected</h5>
          <p>Search for and add deals using the form above to get started.</p>
        </div>
      )}

      {loading && (
        <div className="text-center py-4">
          <div className="spinner-border" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default CombinedDealTrancheSelectionStep;