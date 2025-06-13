import React, { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight, Settings, Eye } from 'lucide-react';
import ColumnManagement from '../ColumnManagement';
import type { 
  Deal, 
  ReportCalculation, 
  ReportColumnPreferences,
  ReportScope
} from '@/types/reporting';
import { getDefaultColumnPreferences } from '@/types/reporting';

interface EnhancedReviewConfigurationStepProps {
  reportName: string;
  reportDescription: string;
  reportScope: ReportScope | '';
  selectedDeals: number[];
  selectedTranches: Record<number, string[]>;
  selectedCalculations: ReportCalculation[];
  columnPreferences?: ReportColumnPreferences;
  onColumnPreferencesChange: (preferences: ReportColumnPreferences) => void;
  deals: Deal[];
}

const ReviewConfigurationStep: React.FC<EnhancedReviewConfigurationStepProps> = ({
  reportName,
  reportDescription,
  reportScope,
  selectedDeals,
  selectedTranches,
  selectedCalculations,
  columnPreferences,
  onColumnPreferencesChange,
  deals
}) => {
  const stepNumber = 4;
  const [activeSection, setActiveSection] = useState<'review' | 'columns'>('review');
  const [expandedSections, setExpandedSections] = useState({
    basicInfo: true,
    calculations: true,
    deals: false,
    tranches: false
  });

  // Initialize column preferences when calculations change
  useEffect(() => {
    if (selectedCalculations.length > 0 && !columnPreferences && reportScope) {
      const defaultPrefs = getDefaultColumnPreferences(
        selectedCalculations, 
        reportScope as ReportScope, 
        true
      );
      onColumnPreferencesChange(defaultPrefs);
    }
  }, [selectedCalculations, reportScope, columnPreferences, onColumnPreferencesChange]);

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const getTotalTrancheCount = (): number => {
    return Object.values(selectedTranches).reduce((total, tranches) => total + tranches.length, 0);
  };

  const getSelectedDealsWithNames = () => {
    return selectedDeals.map(dlNbr => {
      const deal = deals.find(d => d.dl_nbr === dlNbr);
      return {
        dlNbr,
        name: deal ? `${deal.issr_cde} - ${deal.cdi_file_nme}` : `Deal ${dlNbr}`,
        trancheCount: selectedTranches[dlNbr]?.length || 0
      };
    });
  };

  return (
    <div className="row">
      <div className="col-12">
        <h5 className="mb-3">Step {stepNumber}: Review & Configure Output</h5>
        
        {/* Section Tabs */}
        <div className="card">
          <div className="card-header p-0">
            <nav className="nav nav-tabs card-header-tabs">
              <button
                className={`nav-link ${activeSection === 'review' ? 'active' : ''}`}
                onClick={() => setActiveSection('review')}
                type="button"
              >
                <Eye size={16} className="me-1" />
                Review Configuration
              </button>
              <button
                className={`nav-link ${activeSection === 'columns' ? 'active' : ''}`}
                onClick={() => setActiveSection('columns')}
                type="button"
              >
                <Settings size={16} className="me-1" />
                Column Management
              </button>
            </nav>
          </div>

          <div className="card-body">
            {/* Review Section */}
            {activeSection === 'review' && (
              <div className="review-section">
                {/* Basic Information */}
                <div className="accordion mb-3">
                  <div className="accordion-item">
                    <h6 className="accordion-header">
                      <button
                        className="accordion-button"
                        type="button"
                        onClick={() => toggleSection('basicInfo')}
                        aria-expanded={expandedSections.basicInfo}
                      >
                        {expandedSections.basicInfo ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                        <span className="ms-2">Basic Information</span>
                      </button>
                    </h6>
                    {expandedSections.basicInfo && (
                      <div className="accordion-body">
                        <div className="row g-3">
                          <div className="col-md-4">
                            <strong>Report Name:</strong>
                            <div className="mt-1">{reportName}</div>
                          </div>
                          <div className="col-md-4">
                            <strong>Scope:</strong>
                            <div className="mt-1">
                              <span className={`badge ${reportScope === 'DEAL' ? 'bg-primary' : 'bg-info'}`}>
                                {reportScope} Level
                              </span>
                            </div>
                          </div>
                          <div className="col-md-4">
                            <strong>Selected Deals:</strong>
                            <div className="mt-1">{selectedDeals.length} deals</div>
                          </div>
                          {reportDescription && (
                            <div className="col-12">
                              <strong>Description:</strong>
                              <div className="mt-1 p-2 bg-light rounded">
                                {reportDescription}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Selected Calculations */}
                <div className="accordion mb-3">
                  <div className="accordion-item">
                    <h6 className="accordion-header">
                      <button
                        className="accordion-button"
                        type="button"
                        onClick={() => toggleSection('calculations')}
                        aria-expanded={expandedSections.calculations}
                      >
                        {expandedSections.calculations ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                        <span className="ms-2">Selected Calculations ({selectedCalculations.length})</span>
                      </button>
                    </h6>
                    {expandedSections.calculations && (
                      <div className="accordion-body">
                        {selectedCalculations.length === 0 ? (
                          <div className="text-muted">No calculations selected</div>
                        ) : (
                          <div className="row">
                            {selectedCalculations.map((calc: ReportCalculation, index: number) => (
                              <div key={`${calc.calculation_id}-${index}`} className="col-md-6 mb-2">
                                <div className="d-flex align-items-center">
                                  <span className={`badge me-2 ${
                                    calc.calculation_type === 'user' ? 'bg-primary' :
                                    calc.calculation_type === 'system' ? 'bg-warning' : 'bg-secondary'
                                  }`}>
                                    {calc.calculation_type || 'calc'}
                                  </span>
                                  <span className="flex-grow-1">
                                    {calc.display_name || `Calculation ${calc.calculation_id}`}
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Selected Deals */}
                <div className="accordion mb-3">
                  <div className="accordion-item">
                    <h6 className="accordion-header">
                      <button
                        className="accordion-button collapsed"
                        type="button"
                        onClick={() => toggleSection('deals')}
                        aria-expanded={expandedSections.deals}
                      >
                        {expandedSections.deals ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                        <span className="ms-2">Selected Deals ({selectedDeals.length})</span>
                      </button>
                    </h6>
                    {expandedSections.deals && (
                      <div className="accordion-body">
                        <div className="row">
                          {getSelectedDealsWithNames().map((deal) => (
                            <div key={deal.dlNbr} className="col-md-6 mb-2">
                              <div className="card border-light">
                                <div className="card-body py-2 px-3">
                                  <div className="d-flex justify-content-between align-items-center">
                                    <div>
                                      <strong>Deal {deal.dlNbr}</strong>
                                      <br />
                                      <small className="text-muted">{deal.name}</small>
                                    </div>
                                    {reportScope === 'TRANCHE' && (
                                      <span className="badge bg-info">
                                        {deal.trancheCount} tranches
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Tranche Details (for TRANCHE scope only) */}
                {reportScope === 'TRANCHE' && (
                  <div className="accordion mb-3">
                    <div className="accordion-item">
                      <h6 className="accordion-header">
                        <button
                          className="accordion-button collapsed"
                          type="button"
                          onClick={() => toggleSection('tranches')}
                          aria-expanded={expandedSections.tranches}
                        >
                          {expandedSections.tranches ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                          <span className="ms-2">Selected Tranches ({getTotalTrancheCount()})</span>
                        </button>
                      </h6>
                      {expandedSections.tranches && (
                        <div className="accordion-body">
                          {selectedDeals.map((dlNbr: number) => {
                            const dealTranches = selectedTranches[dlNbr] || [];
                            const deal = deals.find(d => d.dl_nbr === dlNbr);
                            
                            if (dealTranches.length === 0) return null;
                            
                            return (
                              <div key={dlNbr} className="mb-3">
                                <strong>Deal {dlNbr}</strong>
                                {deal && <small className="text-muted ms-2">({deal.issr_cde})</small>}
                                <div className="mt-1">
                                  {dealTranches.map((trId: string) => (
                                    <span key={trId} className="badge bg-light text-dark me-1 mb-1">
                                      {trId}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Summary Alert */}
                <div className="alert alert-info">
                  <strong>Report Summary:</strong> This {reportScope?.toLowerCase()} level report will include{' '}
                  {selectedCalculations.length} calculation{selectedCalculations.length !== 1 ? 's' : ''} across{' '}
                  {selectedDeals.length} deal{selectedDeals.length !== 1 ? 's' : ''}
                  {reportScope === 'TRANCHE' && ` (${getTotalTrancheCount()} tranches)`}.
                  <br />
                  <small className="text-muted">
                    <em>Use the Column Management tab to customize the output format and column order.</em>
                  </small>
                </div>
              </div>
            )}

            {/* Column Management Section */}
            {activeSection === 'columns' && (
              <div className="column-management-section">
                <div className="mb-3">
                  <p className="text-muted">
                    Customize how your report columns appear in the final output. You can reorder columns by dragging,
                    toggle visibility, rename columns, and apply formatting.
                  </p>
                </div>
                
                {selectedCalculations.length > 0 && reportScope ? (
                  <ColumnManagement
                    calculations={selectedCalculations}
                    reportScope={reportScope as ReportScope}
                    columnPreferences={columnPreferences}
                    onColumnPreferencesChange={onColumnPreferencesChange}
                  />
                ) : (
                  <div className="alert alert-warning">
                    <strong>No calculations selected.</strong> Please go back and select some calculations before configuring columns.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReviewConfigurationStep;