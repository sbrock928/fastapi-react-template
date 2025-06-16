import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { useApiRequest } from '@/hooks';
import reportingApi from '@/services/reportingApi';
import { useToast } from '@/context/ToastContext';
import type { Deal, TrancheReportSummary } from '@/types/reporting';

interface DealTrancheTreeItem {
  dlNbr: number;
  deal: Deal;
  totalTranches: number;
  selectedTranches: number;
  isExpanded: boolean;
  tranches: TrancheReportSummary[];
}

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
  
  // State for tree view management
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

  // Create tree items from selected deals
  const treeItems = useMemo<DealTrancheTreeItem[]>(() => {
    console.log(`🔍 Creating tree items for ${selectedDeals.length} selected deals:`, selectedDeals);
    console.log(`📊 Tranches data:`, tranches);
    console.log(`🎯 Selected tranches:`, selectedTranches);
    
    return selectedDeals.map(dlNbr => {
      const dealTranches = tranches[dlNbr] || [];
      const selectedTrancheIds = selectedTranches[dlNbr] || [];
      
      console.log(`  - Deal ${dlNbr}: ${dealTranches.length} tranches, ${selectedTrancheIds.length} selected`);
      
      // First try to get deal info from cache, then from search results, then create placeholder
      const deal: Deal = dealInfoCache[dlNbr] || 
        dealSearchResults.find(d => d.dl_nbr === dlNbr) || {
          dl_nbr: dlNbr,
          issr_cde: 'Loading...',
          cdi_file_nme: 'Loading...',
          CDB_cdi_file_nme: null
        };

      return {
        dlNbr,
        deal,
        totalTranches: dealTranches.length,
        selectedTranches: selectedTrancheIds.length,
        isExpanded: expandedDeals.has(dlNbr),
        tranches: dealTranches
      };
    });
  }, [selectedDeals, tranches, selectedTranches, expandedDeals, dealSearchResults, dealInfoCache]);

  // DEBUG: Add an effect to log when tranches prop changes
  useEffect(() => {
    console.log(`🔄 Tranches prop updated:`, tranches);
  }, [tranches]);

  // DEBUG: Add an effect to log when selectedTranches prop changes  
  useEffect(() => {
    console.log(`🎯 SelectedTranches prop updated:`, selectedTranches);
  }, [selectedTranches]);

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
    // Clean up expanded state and tranche search
    setExpandedDeals(prev => {
      const newSet = new Set(prev);
      newSet.delete(dlNbr);
      return newSet;
    });
    setTrancheSearchTerms(prev => {
      const newTerms = { ...prev };
      delete newTerms[dlNbr];
      return newTerms;
    });
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

  // Filter tranches for a deal based on search term
  const getFilteredTranches = (dlNbr: number, tranches: TrancheReportSummary[]) => {
    const searchTerm = trancheSearchTerms[dlNbr];
    if (!searchTerm?.trim()) return tranches;
    
    const searchLower = searchTerm.toLowerCase();
    return tranches.filter(tranche => 
      tranche.tr_id.toLowerCase().includes(searchLower)
    );
  };

  // Handle tranche search term change
  const handleTrancheSearchChange = (dlNbr: number, searchTerm: string) => {
    setTrancheSearchTerms(prev => ({
      ...prev,
      [dlNbr]: searchTerm
    }));
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
        <div className="card-header">
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

      {/* Selected Deals Tree View */}
      {hasSelections && (
        <div className="card">
          <div className="card-header">
            <h6 className="mb-0">Selected Deals ({selectedDeals.length})</h6>
          </div>
          <div className="card-body">
            {treeItems.map(item => (
              <div key={item.dlNbr} className="border rounded mb-3 p-3">
                {/* Deal Header */}
                <div className="d-flex justify-content-between align-items-center">
                  <div className="d-flex align-items-center">
                    <button
                      className="btn btn-sm btn-outline-secondary me-2"
                      onClick={() => toggleExpansion(item.dlNbr)}
                    >
                      <i className={`bi bi-chevron-${item.isExpanded ? 'down' : 'right'}`}></i>
                    </button>
                    <div>
                      <strong>Deal {item.dlNbr}</strong>
                      <span className="badge bg-primary ms-2">
                        {item.selectedTranches}/{item.totalTranches} tranches selected
                      </span>
                      <br />
                      <small className="text-muted">
                        {item.deal.issr_cde} | {item.deal.cdi_file_nme}
                      </small>
                    </div>
                  </div>
                  <button
                    className="btn btn-sm btn-outline-danger"
                    onClick={() => handleRemoveDeal(item.dlNbr)}
                    title="Remove deal from report"
                  >
                    <i className="bi bi-trash"></i>
                  </button>
                </div>

                {/* Expanded Tranche Selection */}
                {item.isExpanded && (
                  <div className="mt-3 ps-4">
                    <div className="row g-3 mb-3">
                      {/* Tranche Search */}
                      <div className="col-md-6">
                        <div className="input-group input-group-sm">
                          <input
                            type="text"
                            className="form-control"
                            placeholder="Search tranches by tr_id..."
                            value={trancheSearchTerms[item.dlNbr] || ''}
                            onChange={(e) => handleTrancheSearchChange(item.dlNbr, e.target.value)}
                          />
                          {trancheSearchTerms[item.dlNbr] && (
                            <button
                              className="btn btn-outline-secondary"
                              type="button"
                              onClick={() => handleTrancheSearchChange(item.dlNbr, '')}
                              title="Clear search"
                            >
                              <i className="bi bi-x"></i>
                            </button>
                          )}
                        </div>
                      </div>
                      
                      {/* Bulk Actions */}
                      <div className="col-md-6">
                        <div className="btn-group" role="group">
                          <button
                            className="btn btn-sm btn-outline-primary"
                            onClick={() => onSelectAllTranches(item.dlNbr)}
                          >
                            Select All
                          </button>
                          <button
                            className="btn btn-sm btn-outline-secondary"
                            onClick={() => onDeselectAllTranches(item.dlNbr)}
                          >
                            Deselect All
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* Tranche List */}
                    <div className="row">
                      {getFilteredTranches(item.dlNbr, item.tranches).map(tranche => {
                        const isSelected = (selectedTranches[item.dlNbr] || []).includes(tranche.tr_id);
                        return (
                          <div key={tranche.tr_id} className="col-md-6 col-lg-4 mb-2">
                            <div className="form-check">
                              <input
                                className="form-check-input"
                                type="checkbox"
                                id={`tranche-${item.dlNbr}-${tranche.tr_id}`}
                                checked={isSelected}
                                onChange={() => onTrancheToggle(item.dlNbr, tranche.tr_id)}
                              />
                              <label
                                className="form-check-label"
                                htmlFor={`tranche-${item.dlNbr}-${tranche.tr_id}`}
                              >
                                {tranche.tr_id}
                              </label>
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {getFilteredTranches(item.dlNbr, item.tranches).length === 0 && (
                      <div className="text-muted text-center py-3">
                        {trancheSearchTerms[item.dlNbr] 
                          ? 'No tranches match your search'
                          : 'No tranches available for this deal'
                        }
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
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