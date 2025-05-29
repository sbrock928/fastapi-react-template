import React, { useState, useEffect } from 'react';
import { reportingApi } from '@/services/api';
import { DealSelector, TrancheSelector } from './';
import { useToast } from '@/context/ToastContext';
import type { Deal, TrancheReportSummary, ReportConfig } from '@/types/reporting';

interface ReportBuilderWizardProps {
  onReportSaved: () => void;
  editingReport?: ReportConfig | null; // New prop for editing mode
  mode?: 'create' | 'edit'; // New prop to track mode
}

const ReportBuilderWizard: React.FC<ReportBuilderWizardProps> = ({
  onReportSaved,
  editingReport = null,
  mode = 'create'
}) => {
  const { showToast } = useToast();
  const isEditMode = mode === 'edit' && editingReport !== null;

  // Wizard state
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(false);
  // Report configuration state
  const [reportName, setReportName] = useState<string>('');
  const [reportDescription, setReportDescription] = useState<string>('');
  const [reportScope, setReportScope] = useState<'DEAL' | 'TRANCHE' | ''>('');const [selectedDeals, setSelectedDeals] = useState<number[]>([]);
  const [selectedTranches, setSelectedTranches] = useState<Record<number, string[]>>({});

  // Data state
  const [deals, setDeals] = useState<Deal[]>([]);
  const [tranches, setTranches] = useState<Record<string, TrancheReportSummary[]>>({});
  const [dealsLoading, setDealsLoading] = useState<boolean>(false);
  const [tranchesLoading, setTranchesLoading] = useState<boolean>(false);

  // Load deals when wizard opens
  useEffect(() => {
    loadDeals();
  }, []);
  // Initialize form with editing data if in edit mode
  useEffect(() => {
    if (isEditMode && editingReport) {
      setReportName(editingReport.name);
      setReportDescription(editingReport.description || '');
      setReportScope(editingReport.scope);
      
      // Convert from backend normalized format to frontend format
      if (editingReport.selected_deals) {
        // Extract deal numbers
        const dlNbrs = editingReport.selected_deals.map(deal => deal.dl_nbr);
        setSelectedDeals(dlNbrs);
        
        // Convert tranches back to frontend format: Record<dlNbr, trId[]>
        const tranchesFormat: Record<string, string[]> = {};
        editingReport.selected_deals.forEach(deal => {
          if (deal.selected_tranches && deal.selected_tranches.length > 0) {
            tranchesFormat[deal.dl_nbr] = deal.selected_tranches.map(tranche => tranche.tr_id);
          }
        });
        setSelectedTranches(tranchesFormat);
      }
    }
  }, [isEditMode, editingReport]);

  // Load tranches when deals are selected
  useEffect(() => {
    const loadTranches = async () => {
      if (selectedDeals.length > 0 && reportScope === 'TRANCHE') {
        setTranchesLoading(true);
        try {
          const response = await reportingApi.getTranches(selectedDeals);
          setTranches(response.data);
        } catch (error) {
          console.error('Error loading tranches:', error);
          showToast('Error loading tranches', 'error');
        } finally {
          setTranchesLoading(false);
        }
      }
    };

    loadTranches();
  }, [selectedDeals, reportScope]);

  // Load available deals (no cycle filtering during configuration)
  const loadDeals = async () => {
    setDealsLoading(true);
    try {
      const response = await reportingApi.getDeals(); // No cycle parameter
      setDeals(response.data);
    } catch (error) {
      console.error('Error loading deals:', error);
      showToast('Error loading deals', 'error');
    } finally {
      setDealsLoading(false);
    }
  };

  // Handle deal selection
  const handleDealToggle = (dlNbr: number) => {
    setSelectedDeals(prev => {
      if (prev.includes(dlNbr)) {
        // Remove deal and its tranches
        const newSelected = prev.filter(id => id !== dlNbr);
        setSelectedTranches(prevTranches => {
          const newTranches = { ...prevTranches };
          delete newTranches[dlNbr];
          return newTranches;
        });
        return newSelected;
      } else {
        return [...prev, dlNbr];
      }
    });
  };

  // Handle tranche selection
  const handleTrancheToggle = (dlNbr: number, trId: string) => {
    setSelectedTranches(prev => {
      const dealTranches = prev[dlNbr] || [];
      const newDealTranches = dealTranches.includes(trId)
        ? dealTranches.filter(id => id !== trId)
        : [...dealTranches, trId];
      
      return {
        ...prev,
        [dlNbr]: newDealTranches
      };
    });
  };
  // Handle select all deals
  const handleSelectAllDeals = () => {
    const allDealNumbers = deals.map(deal => deal.dl_nbr);
    setSelectedDeals(allDealNumbers);
  };

  // Handle select all tranches for a deal
  const handleSelectAllTranches = (dlNbr: number) => {
    const allTrancheIds = (tranches[dlNbr] || []).map(t => t.tr_id);
    setSelectedTranches(prev => ({
      ...prev,
      [dlNbr]: allTrancheIds
    }));
  };
  // Wizard navigation
  const nextStep = () => {
    let nextStepNum = currentStep + 1;
    
    // Skip step 3 (tranche selection) for DEAL scope reports
    if (currentStep === 2 && reportScope === 'DEAL') {
      nextStepNum = 4; // Jump directly to step 4 (review)
    }
    
    if (nextStepNum <= 4) setCurrentStep(nextStepNum);
  };

  const prevStep = () => {
    let prevStepNum = currentStep - 1;
    
    // Skip step 3 (tranche selection) for DEAL scope reports when going backwards
    if (currentStep === 4 && reportScope === 'DEAL') {
      prevStepNum = 2; // Jump back to step 2 (deal selection)
    }
    
    if (prevStepNum >= 1) setCurrentStep(prevStepNum);
  };

  // Save or update report configuration
  const saveReportConfig = async () => {
    setLoading(true);
    
    try {
      // Transform frontend format to backend normalized schema format
      const transformedSelectedDeals = selectedDeals.map(dlNbr => ({
        dl_nbr: dlNbr,
        selected_tranches: (selectedTranches[dlNbr] || []).map(trId => ({
          dl_nbr: dlNbr,
          tr_id: trId
        }))
      }));      if (isEditMode && editingReport?.id) {
        // Update existing report
        const updateData = {
          name: reportName,
          description: reportDescription || undefined,
          scope: reportScope as 'DEAL' | 'TRANCHE',
          selected_deals: transformedSelectedDeals
        };

        await reportingApi.updateReport(editingReport.id, updateData);
        showToast('Report configuration updated successfully!', 'success');
      } else {
        // Create new report
        const reportConfig = {
          name: reportName,
          description: reportDescription || undefined,
          scope: reportScope as 'DEAL' | 'TRANCHE',
          created_by: 'current_user', // TODO: Get from auth context
          selected_deals: transformedSelectedDeals
        };

        await reportingApi.createReport(reportConfig);
        showToast('Report configuration saved successfully!', 'success');
      }
      
      onReportSaved();
        // Reset form only if creating new (not editing)
      if (!isEditMode) {
        setReportName('');
        setReportDescription('');
        setReportScope('');
        setSelectedDeals([]);
        setSelectedTranches({});
        setCurrentStep(1);
      }
      
    } catch (error: any) {
      console.error('Error saving report:', error);
      
      // Extract detailed error messages from the API response
      let errorMessage = `Error ${isEditMode ? 'updating' : 'saving'} report configuration`;
      
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        
        if (detail.errors && Array.isArray(detail.errors)) {
          // Handle the backend's errors array format
          const errorMessages = detail.errors.join(', ');
          errorMessage = `${errorMessage}: ${errorMessages}`;
        } else if (typeof detail === 'string') {
          // Handle simple string error messages
          errorMessage = `${errorMessage}: ${detail}`;
        } else if (typeof detail === 'object' && detail.message) {
          // Handle other object formats with a message property
          errorMessage = `${errorMessage}: ${detail.message}`;
        }
      } else if (error.response?.data?.message) {
        // Handle other API error formats
        errorMessage = `${errorMessage}: ${error.response.data.message}`;
      } else if (error.message) {
        // Handle network or other errors
        errorMessage = `${errorMessage}: ${error.message}`;
      }
      
      showToast(errorMessage, 'error');
    } finally {
      setLoading(false);
    }  };

  // Render wizard step content
  const renderWizardStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="row g-3">
            <div className="col-12">
              <h5 className="mb-3">Step 1: Report Configuration</h5>
              {isEditMode && (
                <div className="alert alert-info">
                  <i className="bi bi-pencil me-2"></i>
                  You are editing: <strong>{editingReport?.name}</strong>
                </div>
              )}
            </div>            <div className="col-md-6">
              <label htmlFor="reportName" className="form-label">Report Name</label>
              <input
                type="text"
                id="reportName"
                className="form-control"
                value={reportName}
                onChange={(e) => setReportName(e.target.value)}
                placeholder="Enter report name"
              />
            </div>
            <div className="col-md-6">
              <label htmlFor="reportScope" className="form-label">Report Scope</label>
              <select
                id="reportScope"
                className="form-select"
                value={reportScope}
                onChange={(e) => setReportScope(e.target.value as 'DEAL' | 'TRANCHE')}
              >
                <option value="">Select scope...</option>
                <option value="DEAL">Deal Level (One row per deal)</option>
                <option value="TRANCHE">Tranche Level (Multiple rows per deal)</option>
              </select>
            </div>
            <div className="col-12">
              <label htmlFor="reportDescription" className="form-label">Description (Optional)</label>
              <textarea
                id="reportDescription"
                className="form-control"
                rows={3}
                value={reportDescription}
                onChange={(e) => setReportDescription(e.target.value)}
                placeholder="Describe the purpose and use of this report..."
              />
              <div className="form-text">Provide a clear description of what this report contains and when it should be used.</div>
            </div>
            <div className="col-12">
              <div className="alert alert-info">
                <strong>Deal Level:</strong> Returns aggregated data with one row per deal.<br/>
                <strong>Tranche Level:</strong> Returns detailed data with one row per selected tranche.<br/>
                <small className="text-muted"><em>Note: Cycle selection happens when running the report, not during configuration.</em></small>
              </div>
            </div>
          </div>
        );

      case 2:
        return (          <DealSelector
            deals={deals}
            selectedDeals={selectedDeals}
            onDealToggle={handleDealToggle}
            onSelectAllDeals={handleSelectAllDeals}
            loading={dealsLoading}
          />
        );

      case 3:
        if (reportScope !== 'TRANCHE') {
          return (
            <div className="text-center p-5">
              <div className="alert alert-warning">
                <i className="bi bi-info-circle me-2"></i>
                Tranche selection is only available for TRANCHE scope reports.
              </div>
            </div>
          );
        }

        return (
          <TrancheSelector
            deals={deals}
            selectedDeals={selectedDeals}
            tranches={tranches}
            selectedTranches={selectedTranches}
            onTrancheToggle={handleTrancheToggle}
            onSelectAllTranches={handleSelectAllTranches}
            loading={tranchesLoading}
          />
        );

      case 4:
        return (
          <div className="row">
            <div className="col-12">
              <h5 className="mb-3">Step 4: Review Configuration</h5>
              <div className="card">
                <div className="card-body">                  <h6 className="card-title">Report Summary</h6>
                  <div className="row g-3">
                    <div className="col-md-4">
                      <strong>Name:</strong> {reportName}
                    </div>
                    <div className="col-md-4">
                      <strong>Scope:</strong> {reportScope}
                    </div>
                    <div className="col-md-4">
                      <strong>Selected Deals:</strong> {selectedDeals.length}
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
                  
                  {reportScope === 'TRANCHE' && (
                    <div className="mt-3">
                      <strong>Selected Tranches:</strong>
                      <ul className="list-unstyled mt-2">
                        {selectedDeals.map(dlNbr => {
                          const deal = deals.find(d => d.dl_nbr === dlNbr);
                          const trancheCount = selectedTranches[dlNbr]?.length || 0;
                          return (
                            <li key={dlNbr} className="mb-1">
                              <span className="badge bg-primary me-2">{dlNbr}</span>
                              {deal?.issr_cde} - {trancheCount} tranches selected
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  )}

                  {reportScope === 'DEAL' && (
                    <div className="mt-3">
                      <strong>Selected Deals:</strong>
                      <ul className="list-unstyled mt-2">
                        {selectedDeals.map(dlNbr => {
                          const deal = deals.find(d => d.dl_nbr === dlNbr);
                          return (
                            <li key={dlNbr} className="mb-1">
                              <span className="badge bg-primary me-2">{dlNbr}</span>
                              {deal?.issr_cde}
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        );

      default:
        return <div>Unknown step</div>;
    }
  };
  // Determine if user can proceed to next step
  const canProceed = () => {
    switch (currentStep) {
      case 1:
        return reportName.trim() !== '' && reportScope !== '';
      case 2:
        return selectedDeals.length > 0;
      case 3:
        // Step 3 should only be reached for TRANCHE scope reports
        if (reportScope === 'TRANCHE') {
          return Object.values(selectedTranches).some(tranches => tranches.length > 0);
        }
        return false; // Should never reach here for DEAL scope
      case 4:
        return true;
      default:
        return false;
    }
  };
  return (
    <div className="report-builder-wizard">
      {/* Progress Bar */}
      <div className="mb-4">
        <div className="d-flex justify-content-between align-items-center mb-2">
          <h4>{isEditMode ? 'Edit Report Configuration' : 'Create New Report'}</h4>
          <span className="badge bg-primary">
            Step {currentStep} of {reportScope === 'DEAL' ? '3' : '4'}
            {reportScope === 'DEAL' && currentStep === 4 && ' (3)'}
          </span>
        </div>
        <div className="progress">
          <div
            className="progress-bar"
            role="progressbar"
            style={{ 
              width: reportScope === 'DEAL' 
                ? `${currentStep === 4 ? 100 : (currentStep / 3) * 100}%`
                : `${(currentStep / 4) * 100}%`
            }}
            aria-valuenow={
              reportScope === 'DEAL' 
                ? (currentStep === 4 ? 100 : (currentStep / 3) * 100)
                : (currentStep / 4) * 100
            }
            aria-valuemin={0}
            aria-valuemax={100}
          ></div>
        </div>
      </div>

      {/* Step Content */}
      <div className="wizard-content mb-4">
        {renderWizardStep()}
      </div>

      {/* Navigation Buttons */}
      <div className="d-flex justify-content-between">
        <button
          type="button"
          className="btn btn-outline-secondary"
          onClick={prevStep}
          disabled={currentStep === 1}
        >
          <i className="bi bi-arrow-left me-2"></i>
          Previous
        </button>

        <div>
          {currentStep < 4 ? (
            <button
              type="button"
              className="btn btn-primary"
              onClick={nextStep}
              disabled={!canProceed()}
            >
              Next
              <i className="bi bi-arrow-right ms-2"></i>
            </button>
          ) : (
            <button
              type="button"
              className="btn btn-success"
              onClick={saveReportConfig}
              disabled={loading || !canProceed()}
            >
              {loading ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2" role="status"></span>
                  {isEditMode ? 'Updating...' : 'Saving...'}
                </>
              ) : (
                <>
                  <i className="bi bi-check-circle me-2"></i>
                  {isEditMode ? 'Update Report' : 'Save Report'}
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ReportBuilderWizard;
