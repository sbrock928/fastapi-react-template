import React, { useState, useEffect } from 'react';
import { reportingApi } from '@/services/api';
import { useToast } from '@/context/ToastContext';
import { 
  useReportBuilderForm, 
  useReportBuilderData, 
  useReportBuilderValidation, 
  useWizardNavigation 
} from './hooks';
import {
  ReportConfigurationStep,
  CombinedDealTrancheSelectionStep,
  CalculationSelectionStep,
  ReviewConfigurationStep
} from './wizardSteps';
import WizardNavigation from './WizardNavigation';
import { transformFormDataForApi } from './utils/reportBusinessLogic';
import type { ReportConfig, TrancheReportSummary } from '@/types/reporting';

interface ReportBuilderWizardProps {
  onReportSaved: () => void;
  editingReport?: ReportConfig | null;
  mode?: 'create' | 'edit';
}

const ReportBuilderWizard: React.FC<ReportBuilderWizardProps> = ({
  onReportSaved,
  editingReport = null,
  mode = 'create'
}) => {
  const { showToast } = useToast();
  const isEditMode = mode === 'edit' && editingReport !== null;

  // Component state
  const [loading, setLoading] = useState<boolean>(false);
  
  // NEW: Add tranche loading state
  const [tranches, setTranches] = useState<Record<number, TrancheReportSummary[]>>({});
  const [tranchesLoading, setTranchesLoading] = useState<boolean>(false);
  
  // Form state management
  const {
    reportName,
    reportDescription,
    reportScope,
    selectedDeals,
    selectedTranches,
    selectedCalculations,
    columnPreferences,
    setReportName,
    setReportDescription,
    setReportScope,
    setSelectedDeals,
    setSelectedTranches,
    setSelectedCalculations,
    setColumnPreferences,
    resetForm
  } = useReportBuilderForm({ editingReport, isEditMode });

  // Data management
  const {
    availableCalculations,
    calculationsLoading
  } = useReportBuilderData({ reportScope });

  // NEW: Load tranches for existing deals when editing
  useEffect(() => {
    if (isEditMode && editingReport && selectedDeals.length > 0) {
      const loadAllTranches = async () => {
        try {
          setTranchesLoading(true);
          
          // Only load tranches for deals that don't already have them loaded
          const dealsNeedingTranches = selectedDeals.filter(dlNbr => !tranches[dlNbr] || tranches[dlNbr].length === 0);
          
          if (dealsNeedingTranches.length === 0) {
            console.log('📋 All deals already have tranches loaded, skipping...');
            return;
          }
          
          console.log(`📋 Loading tranches for ${dealsNeedingTranches.length} deals in edit mode:`, dealsNeedingTranches);
          
          // Load tranches for deals that need them
          const tranchePromises = dealsNeedingTranches.map(async (dlNbr) => {
            try {
              const response = await reportingApi.getDealTranches(dlNbr);
              return { dlNbr, tranches: response.data };
            } catch (error) {
              console.error(`Error loading tranches for deal ${dlNbr}:`, error);
              return { dlNbr, tranches: [] };
            }
          });
          
          const results = await Promise.all(tranchePromises);
          
          // Update tranches state with all loaded data
          const newTranches: Record<number, TrancheReportSummary[]> = { ...tranches };
          results.forEach(({ dlNbr, tranches: dealTranches }) => {
            newTranches[dlNbr] = dealTranches;
          });
          
          setTranches(newTranches);
          console.log(`✅ Loaded tranches for ${results.length} deals in edit mode`);
          
        } catch (error) {
          console.error('Error loading tranches for editing:', error);
          showToast('Failed to load tranche data for editing', 'error');
        } finally {
          setTranchesLoading(false);
        }
      };
      
      loadAllTranches();
    }
  }, [isEditMode, editingReport, selectedDeals, showToast]); // Removed tranches from dependencies to prevent conflicts

  // Validation and navigation
  const formState = {
    reportName,
    reportDescription,
    reportScope,
    selectedDeals,
    selectedTranches,
    selectedCalculations,
    columnPreferences
  };

  const { canProceed, hasFieldError, getFieldErrorMessage, validateSpecificStep } = useReportBuilderValidation({ 
    formState, 
    currentStep: 1
  });

  const { currentStep, displayStep, totalSteps, nextStep, prevStep, resetToFirstStep } = useWizardNavigation({
    validateStep: (step: number) => ({ isValid: validateSpecificStep(step), errors: [] }),
    onValidationError: (message: string) => showToast(message, 'error')
  });

  // Handle deal addition - now loads tranches automatically
  const handleDealAdd = async (dlNbr: number) => {
    // Check if deal is already selected
    if (selectedDeals.includes(dlNbr)) {
      return;
    }

    console.log(`🎯 Adding deal ${dlNbr} to selected deals...`);
    
    try {
      // Load tranches FIRST, then update state all at once to prevent race conditions
      console.log(`🔄 Loading tranches for deal ${dlNbr} before adding to state...`);
      setTranchesLoading(true);
      const response = await reportingApi.getDealTranches(dlNbr);
      const dealTranches = response.data;
      
      console.log(`✅ Loaded ${dealTranches.length} tranches for deal ${dlNbr}:`, dealTranches.map(t => t.tr_id));
      
      // Update all state in a single batch to prevent race conditions
      setSelectedDeals((prev: number[]) => {
        const newSelected = [...prev, dlNbr];
        console.log(`📝 Updated selectedDeals:`, newSelected);
        return newSelected;
      });
      
      setTranches(prev => {
        const updated = {
          ...prev,
          [dlNbr]: dealTranches
        };
        console.log(`📊 Updated tranches state:`, updated);
        return updated;
      });
      
      // Auto-select all tranches by default (only for new deals, not when editing)
      if (!isEditMode && dealTranches.length > 0) {
        const allTrancheIds = dealTranches.map(t => t.tr_id);
        console.log(`🎯 Auto-selecting ${allTrancheIds.length} tranches for deal ${dlNbr}:`, allTrancheIds);
        setSelectedTranches(prev => ({
          ...prev,
          [dlNbr]: allTrancheIds
        }));
      }
      
      console.log(`✅ Finished adding deal ${dlNbr}`);
      
    } catch (error: any) {
      console.error('❌ Error adding deal:', dlNbr, error);
      showToast(`Failed to load tranches for deal ${dlNbr}`, 'error');
    } finally {
      setTranchesLoading(false);
    }
  };

  // Handle deal removal
  const handleDealRemove = (dlNbr: number) => {
    setSelectedDeals((prev: number[]) => {
      const newSelected = prev.filter((id: number) => id !== dlNbr);
      
      // Remove tranches for this deal
      setSelectedTranches((prevTranches: Record<number, string[]>) => {
        const newTranches = { ...prevTranches };
        delete newTranches[dlNbr];
        return newTranches;
      });
      
      // Remove tranche data for this deal
      setTranches((prevTranches: Record<number, TrancheReportSummary[]>) => {
        const newTranches = { ...prevTranches };
        delete newTranches[dlNbr];
        return newTranches;
      });
      
      return newSelected;
    });
  };

  // Handle select all tranches for a deal
  const handleSelectAllTranches = (dlNbr: number) => {
    const dealTranches = tranches[dlNbr] || [];
    const allTrancheIds = dealTranches.map(t => t.tr_id);
    
    setSelectedTranches((prev: Record<number, string[]>) => ({
      ...prev,
      [dlNbr]: allTrancheIds
    }));
  };

  // Handle deselect all tranches for a deal
  const handleDeselectAllTranches = (dlNbr: number) => {
    setSelectedTranches((prev: Record<number, string[]>) => ({
      ...prev,
      [dlNbr]: []
    }));
  };

  // Handle tranche selection toggle
  const handleTrancheToggle = (dlNbr: number, trId: string) => {
    setSelectedTranches((prev: Record<number, string[]>) => {
      const dealTranches = prev[dlNbr] || [];
      const newDealTranches = dealTranches.includes(trId)
        ? dealTranches.filter((id: string) => id !== trId)
        : [...dealTranches, trId];
      
      return {
        ...prev,
        [dlNbr]: newDealTranches
      };
    });
  };

  // Save or update report configuration
  const saveReportConfig = async (): Promise<void> => {
    if (loading) return;
  
    try {
      setLoading(true);
      
      // Transform form data including column preferences
      const reportData = transformFormDataForApi({
        reportName,
        reportDescription,
        reportScope,
        selectedDeals,
        selectedTranches,
        selectedCalculations,
        columnPreferences
      });
  
      if (isEditMode && editingReport?.id) {
        // Update existing report
        await reportingApi.updateReport(editingReport.id, reportData);
        showToast('Report updated successfully!', 'success');
      } else {
        // Create new report
        await reportingApi.createReport(reportData);
        showToast('Report created successfully!', 'success');
      }
  
      // Reset form and notify parent
      resetForm();
      resetToFirstStep();
      onReportSaved();
  
    } catch (error: any) {
      console.error('Error saving report:', error);
      
      let errorMessage = isEditMode ? 'Failed to update report' : 'Failed to create report';
      
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;
        
        if (detail.errors && Array.isArray(detail.errors)) {
          const errorMessages = detail.errors.join(', ');
          errorMessage = `${errorMessage}: ${errorMessages}`;
        } else if (typeof detail === 'string') {
          errorMessage = `${errorMessage}: ${detail}`;
        } else if (typeof detail === 'object' && detail.message) {
          errorMessage = `${errorMessage}: ${detail.message}`;
        }
      } else if (error.response?.data?.message) {
        errorMessage = `${errorMessage}: ${error.response.data.message}`;
      } else if (error.message) {
        errorMessage = `${errorMessage}: ${error.message}`;
      }
      
      showToast(errorMessage, 'error');
    } finally {
      setLoading(false);
    }
  };
  

  // Auto-select tranches based on report scope (simplified for now)
  React.useEffect(() => {
    // TODO: This logic would need to be restored when deal/tranche data loading is implemented
    // For now, this is a placeholder
  }, [selectedDeals, reportScope]);

  // Render wizard step content
  const renderWizardStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <ReportConfigurationStep
            reportName={reportName}
            reportDescription={reportDescription}
            reportScope={reportScope}
            onReportNameChange={setReportName}
            onReportDescriptionChange={setReportDescription}
            onReportScopeChange={setReportScope}
            editingReport={editingReport}
            isEditMode={isEditMode}
            hasFieldError={hasFieldError}
            getFieldErrorMessage={getFieldErrorMessage}
          />
        );
  
      case 2:
        return (
          <CombinedDealTrancheSelectionStep
            reportScope={reportScope}
            selectedDeals={selectedDeals}
            selectedTranches={selectedTranches}
            tranches={tranches}
            onDealAdd={handleDealAdd}
            onDealRemove={handleDealRemove}
            onTrancheToggle={handleTrancheToggle}
            onSelectAllTranches={handleSelectAllTranches}
            onDeselectAllTranches={handleDeselectAllTranches}
            loading={tranchesLoading}
          />
        );
  
      case 3:
        return (
          <CalculationSelectionStep
            reportScope={reportScope}
            availableCalculations={availableCalculations}
            selectedCalculations={selectedCalculations}
            onCalculationsChange={setSelectedCalculations}
            loading={calculationsLoading}
          />
        );
  
      case 4:
        return (
          <ReviewConfigurationStep
            reportName={reportName}
            reportDescription={reportDescription}
            reportScope={reportScope}
            selectedDeals={selectedDeals}
            selectedTranches={selectedTranches}
            selectedCalculations={selectedCalculations}
            columnPreferences={columnPreferences}
            onColumnPreferencesChange={setColumnPreferences}
            deals={[]} // TODO: Provide actual deal data when available
          />
        );
  
      default:
        return <div>Unknown step</div>;
    }
  };

  return (
    <div className="report-builder-wizard">
      {/* Wizard Navigation */}
      <WizardNavigation
        currentStep={displayStep}
        totalSteps={totalSteps}
        canProceed={canProceed}
        isLoading={loading}
        isEditMode={isEditMode}
        onPreviousStep={prevStep}
        onNextStep={nextStep}
        onSave={saveReportConfig}
        title={isEditMode ? 'Edit Report Configuration' : 'Create New Report'}
      />

      {/* Step Content */}
      <div className="wizard-content mb-4">
        {renderWizardStep()}
      </div>
    </div>
  );
};

export default ReportBuilderWizard;