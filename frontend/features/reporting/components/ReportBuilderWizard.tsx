import React, { useState } from 'react';
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
  CombinedDealTrancheSelectionStep, // New combined component
  CalculationSelectionStep,
  ReviewConfigurationStep
} from './wizardSteps';
import WizardNavigation from './WizardNavigation';
import { transformFormDataForApi } from './utils/reportBusinessLogic'; // Import the new function
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
  
  // Form state management
  const {
    reportName,
    reportDescription,
    reportScope,
    selectedDeals,
    selectedTranches,
    selectedCalculations, // Changed from selectedFields
    setReportName,
    setReportDescription,
    setReportScope,
    setSelectedDeals,
    setSelectedTranches,
    setSelectedCalculations, // Changed from setSelectedFields
    resetForm
  } = useReportBuilderForm({ editingReport, isEditMode });

  // Data management
  const {
    deals,
    tranches,
    availableCalculations, // Changed from availableFields
    dealsLoading,
    tranchesLoading,
    calculationsLoading // Changed from fieldsLoading
  } = useReportBuilderData({ reportScope, selectedDeals, isEditMode });

  // Validation management
  const formState = {
    reportName,
    reportDescription,
    reportScope,
    selectedDeals,
    selectedTranches,
    selectedCalculations // Changed from selectedFields
  };

  // Start with step 1, will be updated by wizard navigation
  const [currentWizardStep, setCurrentWizardStep] = useState<number>(1);
  
  const {
    canProceed,
    hasFieldError,
    getFieldErrorMessage,
    validateSpecificStep
  } = useReportBuilderValidation({ formState, currentStep: currentWizardStep });

  // Wizard navigation management
  const {
    currentStep,
    totalSteps,
    displayStep,
    nextStep,
    prevStep,
    resetToFirstStep
  } = useWizardNavigation({
    onValidationError: (message: string) => showToast(message, 'error'),
    validateStep: validateSpecificStep
  });

  // Update wizard step state when navigation changes
  React.useEffect(() => {
    setCurrentWizardStep(currentStep);
  }, [currentStep]);

  // Handle deal addition (new method for combined component)
  const handleDealAdd = (dlNbr: number) => {
    setSelectedDeals((prev: number[]) => {
      if (!prev.includes(dlNbr)) {
        return [...prev, dlNbr];
      }
      return prev;
    });
  };

  // Handle deal removal (new method for combined component)  
  const handleDealRemove = (dlNbr: number) => {
    setSelectedDeals((prev: number[]) => {
      const newSelected = prev.filter((id: number) => id !== dlNbr);
      // Also remove tranches for this deal
      setSelectedTranches((prevTranches: Record<number, string[]>) => {
        const newTranches = { ...prevTranches };
        delete newTranches[dlNbr];
        return newTranches;
      });
      return newSelected;
    });
  };

  // Handle deselect all tranches for a deal (new method)
  const handleDeselectAllTranches = (dlNbr: number) => {
    setSelectedTranches((prev: Record<number, string[]>) => ({
      ...prev,
      [dlNbr]: []
    }));
  };

  // Handle tranche selection
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

  // Handle select all tranches for a deal
  const handleSelectAllTranches = (dlNbr: number) => {
    const allTrancheIds = (tranches[dlNbr] || []).map((t: TrancheReportSummary) => t.tr_id);
    setSelectedTranches((prev: Record<number, string[]>) => ({
      ...prev,
      [dlNbr]: allTrancheIds
    }));
  };

  // Save or update report configuration
  const saveReportConfig = async () => {
    // Final validation before saving - now step 4 instead of step 5
    const finalValidation = validateSpecificStep(4);
    if (!finalValidation.isValid) {
      finalValidation.errors.forEach((error: any) => {
        showToast(error.message, 'error');
      });
      return;
    }

    setLoading(true);
    
    try {
      // Use the smart business logic function that only includes tranches when explicitly needed
      const transformedData = transformFormDataForApi(formState, tranches);

      if (isEditMode && editingReport?.id) {
        await reportingApi.updateReport(editingReport.id, transformedData);
        showToast('Report configuration updated successfully!', 'success');
      } else {
        const reportConfig = {
          ...transformedData,
          created_by: 'current_user'
        };

        await reportingApi.createReport(reportConfig);
        showToast('Report configuration saved successfully!', 'success');
      }
      
      onReportSaved();
      
      if (!isEditMode) {
        resetForm();
        resetToFirstStep();
      }
      
    } catch (error: any) {
      console.error('Error saving report:', error);
      
      let errorMessage = `Error ${isEditMode ? 'updating' : 'saving'} report configuration`;
      
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

  // Auto-select tranches based on report scope (updated logic for smart defaults)
  React.useEffect(() => {
    // Only auto-select for new reports, not when editing
    if (!isEditMode && Object.keys(tranches).length > 0) {
      setSelectedTranches((prev: Record<number, string[]>) => {
        const newSelectedTranches: Record<number, string[]> = {};
        let hasChanges = false;
        
        Object.entries(tranches).forEach(([dealId, dealTranches]) => {
          const dlNbr = parseInt(dealId);
          if (selectedDeals.includes(dlNbr)) {
            // Only auto-select if this deal has no existing tranche selections
            if (!prev[dlNbr] || prev[dlNbr].length === 0) {
              // For BOTH scopes: Auto-select ALL tranches by default
              // This enables the smart exclusionary behavior for both report types
              newSelectedTranches[dlNbr] = dealTranches.map((t: TrancheReportSummary) => t.tr_id);
              hasChanges = true;
            } else {
              // Keep existing selections
              newSelectedTranches[dlNbr] = prev[dlNbr];
            }
          }
        });
        
        // Only update if there are actual changes
        if (hasChanges) {
          return { ...prev, ...newSelectedTranches };
        }
        return prev;
      });
    }
  }, [tranches, isEditMode, selectedDeals, reportScope]);

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
            loading={dealsLoading || tranchesLoading}
          />
        );

      case 3:
        return (
          <CalculationSelectionStep
            reportScope={reportScope}
            availableCalculations={availableCalculations} // Changed from availableFields
            selectedCalculations={selectedCalculations} // Changed from selectedFields
            onCalculationsChange={setSelectedCalculations} // Changed from onFieldsChange
            loading={calculationsLoading} // Changed from fieldsLoading
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
            selectedCalculations={selectedCalculations} // Changed from selectedFields
            deals={deals}
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