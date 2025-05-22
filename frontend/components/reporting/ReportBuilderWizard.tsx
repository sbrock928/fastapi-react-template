import React, { useState, useEffect } from 'react';
import { reportsApi } from '@/services/api';
import { useToast } from '@/context/ToastContext';
import DealSelector from './DealSelector';
import TrancheSelector from './TrancheSelector';
import ColumnSelector from './ColumnSelector';
import type { Deal, Tranche, ReportConfig } from '@/types';

interface ReportBuilderWizardProps {
  onReportSaved: () => void;
  onCancel: () => void;
  editingReport?: ReportConfig | null; // New prop for editing mode
  mode?: 'create' | 'edit'; // New prop to track mode
}

const ReportBuilderWizard: React.FC<ReportBuilderWizardProps> = ({
  onReportSaved,
  onCancel,
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
  const [reportScope, setReportScope] = useState<'DEAL' | 'TRANCHE' | ''>('');
  const [selectedDeals, setSelectedDeals] = useState<number[]>([]);
  const [selectedTranches, setSelectedTranches] = useState<Record<number, number[]>>({});
  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);

  // Data state
  const [deals, setDeals] = useState<Deal[]>([]);
  const [tranches, setTranches] = useState<Record<number, Tranche[]>>({});
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
      setReportScope(editingReport.scope);
      setSelectedDeals(editingReport.selected_deals);
      setSelectedTranches(editingReport.selected_tranches);
      setSelectedColumns(editingReport.selected_columns || []);
    }
  }, [isEditMode, editingReport]);

  // Load tranches when deals are selected
  useEffect(() => {
    const loadTranches = async () => {
      if (selectedDeals.length > 0 && reportScope === 'TRANCHE') {
        setTranchesLoading(true);
        try {
          const response = await reportsApi.getTranches(selectedDeals);
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

  // Load default columns when scope changes
  useEffect(() => {
    const loadDefaultColumns = async () => {
      if (reportScope && !isEditMode) {
        try {
          const response = await fetch(`/api/reports/columns/${reportScope.toLowerCase()}/defaults`);
          const defaultColumns = await response.json();
          setSelectedColumns(defaultColumns);
        } catch (error) {
          console.error('Error loading default columns:', error);
          // Use fallback defaults
          const fallbackColumns = reportScope === 'DEAL' 
            ? ['deal_name', 'originator', 'deal_type', 'total_principal', 'credit_rating']
            : ['deal_name', 'tranche_name', 'class_name', 'principal_amount', 'interest_rate'];
          setSelectedColumns(fallbackColumns);
        }
      }
    };

    loadDefaultColumns();
  }, [reportScope, isEditMode]);

  // Load available deals (no cycle filtering during configuration)
  const loadDeals = async () => {
    setDealsLoading(true);
    try {
      const response = await reportsApi.getDeals(); // No cycle parameter
      setDeals(response.data);
    } catch (error) {
      console.error('Error loading deals:', error);
      showToast('Error loading deals', 'error');
    } finally {
      setDealsLoading(false);
    }
  };

  // Handle deal selection
  const handleDealToggle = (dealId: number) => {
    setSelectedDeals(prev => {
      if (prev.includes(dealId)) {
        // Remove deal and its tranches
        const newSelected = prev.filter(id => id !== dealId);
        setSelectedTranches(prevTranches => {
          const newTranches = { ...prevTranches };
          delete newTranches[dealId];
          return newTranches;
        });
        return newSelected;
      } else {
        return [...prev, dealId];
      }
    });
  };

  // Handle tranche selection
  const handleTrancheToggle = (dealId: number, trancheId: number) => {
    setSelectedTranches(prev => {
      const dealTranches = prev[dealId] || [];
      const newDealTranches = dealTranches.includes(trancheId)
        ? dealTranches.filter(id => id !== trancheId)
        : [...dealTranches, trancheId];
      
      return {
        ...prev,
        [dealId]: newDealTranches
      };
    });
  };

  // Handle select all tranches for a deal
  const handleSelectAllTranches = (dealId: number) => {
    const allTrancheIds = (tranches[dealId] || []).map(t => t.id);
    setSelectedTranches(prev => ({
      ...prev,
      [dealId]: allTrancheIds
    }));
  };

  // Handle column selection
  const handleColumnToggle = (columnKey: string) => {
    setSelectedColumns(prev => {
      if (prev.includes(columnKey)) {
        return prev.filter(key => key !== columnKey);
      } else {
        return [...prev, columnKey];
      }
    });
  };

  const handleSelectDefaultColumns = async () => {
    if (!reportScope) return;
    
    try {
      const response = await fetch(`/api/reports/columns/${reportScope.toLowerCase()}/defaults`);
      const defaultColumns = await response.json();
      setSelectedColumns(defaultColumns);
    } catch (error) {
      console.error('Error loading default columns:', error);
      showToast('Error loading default columns', 'error');
    }
  };

  const handleSelectAllColumns = async () => {
    if (!reportScope) return;
    
    try {
      const response = await fetch(`/api/reports/columns/${reportScope.toLowerCase()}`);
      const categories = await response.json();
      const allColumns = Object.values(categories).flat().map((col: any) => col.key);
      setSelectedColumns(allColumns);
    } catch (error) {
      console.error('Error loading all columns:', error);
      showToast('Error loading columns', 'error');
    }
  };

  const handleSelectNoColumns = () => {
    setSelectedColumns([]);
  };

  // Wizard navigation
  const nextStep = () => {
    if (currentStep < 5) setCurrentStep(currentStep + 1);
  };

  const prevStep = () => {
    if (currentStep > 1) setCurrentStep(currentStep - 1);
  };

  // Save or update report configuration
  const saveReportConfig = async () => {
    setLoading(true);
    
    try {
      if (isEditMode && editingReport?.id) {
        // Update existing report
        const updateData: Partial<ReportConfig> = {
          name: reportName,
          scope: reportScope as 'DEAL' | 'TRANCHE',
          selected_deals: selectedDeals,
          selected_tranches: selectedTranches,
          selected_columns: selectedColumns
        };

        await reportsApi.updateReport(editingReport.id, updateData);
        showToast('Report configuration updated successfully!', 'success');
      } else {
        // Create new report
        const reportConfig: Omit<ReportConfig, 'id' | 'created_date' | 'updated_date'> = {
          name: reportName,
          scope: reportScope as 'DEAL' | 'TRANCHE',
          created_by: 'current_user', // TODO: Get from auth context
          selected_deals: selectedDeals,
          selected_tranches: selectedTranches,
          selected_columns: selectedColumns
        };

        await reportsApi.createReport(reportConfig);
        showToast('Report configuration saved successfully!', 'success');
      }
      
      onReportSaved();
      
      // Reset form only if creating new (not editing)
      if (!isEditMode) {
        setReportName('');
        setReportScope('');
        setSelectedDeals([]);
        setSelectedTranches({});
        setSelectedColumns([]);
        setCurrentStep(1);
      }
      
    } catch (error) {
      console.error('Error saving report:', error);
      showToast(`Error ${isEditMode ? 'updating' : 'saving'} report configuration`, 'error');
    } finally {
      setLoading(false);
    }
  };

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
            </div>
            <div className="col-md-6">
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
              <div className="alert alert-info">
                <strong>Deal Level:</strong> Returns aggregated data with one row per deal.<br/>
                <strong>Tranche Level:</strong> Returns detailed data with one row per selected tranche.<br/>
                <small className="text-muted"><em>Note: Cycle selection happens when running the report, not during configuration.</em></small>
              </div>
            </div>
          </div>
        );

      case 2:
        return (
          <DealSelector
            deals={deals}
            selectedDeals={selectedDeals}
            onDealToggle={handleDealToggle}
            loading={dealsLoading}
          />
        );

      case 3:
        if (reportScope !== 'TRANCHE') {
          return (
            <div>
              <h5 className="mb-3">Step 3: Deal-Level Configuration</h5>
              <div className="alert alert-success">
                <i className="bi bi-check-circle me-2"></i>
                Your deal-level report is configured! You've selected {selectedDeals.length} deal{selectedDeals.length !== 1 ? 's' : ''} 
                and will get one row per deal with aggregated data.
              </div>
              <div className="card">
                <div className="card-header">
                  <h6 className="mb-0">Selected Deals Summary</h6>
                </div>
                <div className="card-body">
                  {selectedDeals.map(dealId => {
                    const deal = deals.find(d => d.id === dealId);
                    if (!deal) return null;
                    return (
                      <div key={dealId} className="d-flex justify-content-between align-items-center py-2 border-bottom">
                        <div>
                          <strong>{deal.name}: {deal.deal_name}</strong>
                          <div className="small text-muted">{deal.deal_number}</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
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
          <ColumnSelector
            reportScope={reportScope as 'DEAL' | 'TRANCHE'}
            selectedColumns={selectedColumns}
            onColumnToggle={handleColumnToggle}
            onSelectDefaults={handleSelectDefaultColumns}
            onSelectAll={handleSelectAllColumns}
            onSelectNone={handleSelectNoColumns}
          />
        );

      case 5:
        return (
          <div>
            <h5 className="mb-3">Step 4: Review & Save</h5>
            <div className="card">
              <div className="card-header">
                <h6 className="mb-0">Report Configuration Summary</h6>
              </div>
              <div className="card-body">
                <dl className="row">
                  <dt className="col-sm-3">Report Name:</dt>
                  <dd className="col-sm-9">{reportName}</dd>
                  
                  <dt className="col-sm-3">Report Scope:</dt>
                  <dd className="col-sm-9">
                    <span className={`badge ${reportScope === 'DEAL' ? 'bg-primary' : 'bg-info'}`}>
                      {reportScope} Level
                    </span>
                  </dd>
                  
                  <dt className="col-sm-3">Selected Deals:</dt>
                  <dd className="col-sm-9">{selectedDeals.length} deal{selectedDeals.length !== 1 ? 's' : ''}</dd>
                  
                  {reportScope === 'TRANCHE' && (
                    <>
                      <dt className="col-sm-3">Selected Tranches:</dt>
                      <dd className="col-sm-9">{Object.values(selectedTranches).flat().length} tranche{Object.values(selectedTranches).flat().length !== 1 ? 's' : ''}</dd>
                    </>
                  )}
                  
                  <dt className="col-sm-3">Selected Columns:</dt>
                  <dd className="col-sm-9">{selectedColumns.length} column{selectedColumns.length !== 1 ? 's' : ''}</dd>
                  
                  <dt className="col-sm-3">Expected Output:</dt>
                  <dd className="col-sm-9">
                    {reportScope === 'DEAL' 
                      ? `${selectedDeals.length} row${selectedDeals.length !== 1 ? 's' : ''} (one per deal)`
                      : `${Object.values(selectedTranches).flat().length} row${Object.values(selectedTranches).flat().length !== 1 ? 's' : ''} (one per tranche)`
                    }
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  // Validate current step
  const isCurrentStepValid = () => {
    switch (currentStep) {
      case 1:
        return reportName.trim() !== '' && reportScope !== '';
      case 2:
        return selectedDeals.length > 0;
      case 3:
        return reportScope === 'DEAL' || Object.values(selectedTranches).flat().length > 0;
      case 4:
        return selectedColumns.length > 0;
      case 5:
        return true;
      default:
        return false;
    }
  };

  return (
    <>
      {/* Progress indicator */}
      <div className="progress mb-4" style={{ height: '8px' }}>
        <div 
          className="progress-bar" 
          role="progressbar" 
          style={{ width: `${(currentStep / 5) * 100}%` }}
          aria-valuenow={currentStep} 
          aria-valuemin={0} 
          aria-valuemax={5}
        ></div>
      </div>
      
      {/* Step indicators */}
      <div className="d-flex justify-content-between mb-4">
        {[1, 2, 3, 4, 5].map(step => (
          <div key={step} className={`text-center ${currentStep >= step ? 'text-primary' : 'text-muted'}`}>
            <div className={`rounded-circle d-inline-flex align-items-center justify-content-center ${
              currentStep >= step ? 'bg-primary text-white' : 'bg-light'
            }`} style={{ width: '32px', height: '32px', fontSize: '14px' }}>
              {currentStep > step ? <i className="bi bi-check"></i> : step}
            </div>
            <div className="small mt-1">
              {step === 1 && 'Setup'}
              {step === 2 && 'Deals'}
              {step === 3 && (reportScope === 'TRANCHE' ? 'Tranches' : 'Skip')}
              {step === 4 && 'Columns'}
              {step === 5 && 'Save'}
            </div>
          </div>
        ))}
      </div>

      {/* Step content */}
      {renderWizardStep()}

      {/* Navigation buttons */}
      <div className="d-flex justify-content-between mt-4">
        <button
          type="button"
          className="btn btn-outline-secondary"
          onClick={prevStep}
          disabled={currentStep === 1}
        >
          <i className="bi bi-arrow-left"></i> Previous
        </button>
        
        <div>
          {currentStep < 5 ? (
            <button
              type="button"
              className="btn btn-primary"
              onClick={nextStep}
              disabled={!isCurrentStepValid()}
            >
              Next <i className="bi bi-arrow-right"></i>
            </button>
          ) : (
            <button
              type="button"
              className="btn btn-success"
              onClick={saveReportConfig}
              disabled={loading || !isCurrentStepValid()}
            >
              {loading ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2"></span>
                  {isEditMode ? 'Updating...' : 'Saving...'}
                </>
              ) : (
                <>
                  <i className={`bi ${isEditMode ? 'bi-check-lg' : 'bi-save'}`}></i> 
                  {isEditMode ? 'Update Report Configuration' : 'Save Report Configuration'}
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </>
  );
};

export default ReportBuilderWizard;