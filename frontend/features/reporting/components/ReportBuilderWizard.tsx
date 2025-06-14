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
  CombinedDealTrancheSelectionStep,
  CalculationSelectionStep,
  ReviewConfigurationStep
} from './wizardSteps';
import WizardNavigation from './WizardNavigation';
import { transformFormDataForApi } from './utils/reportBusinessLogic';
import type { ReportConfig } from '@/types/reporting';

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
    selectedCalculations,
    columnPreferences, // NEW: Add column preferences
    setReportName,
    setReportDescription,
    setReportScope,
    setSelectedDeals,
    setSelectedTranches,
    setSelectedCalculations,
    setColumnPreferences, // NEW: Add setter
    resetForm
  } = useReportBuilderForm({ editingReport, isEditMode });

  // Data management
  const {
    availableCalculations,
    calculationsLoading
  } = useReportBuilderData({ reportScope });

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
    currentStep: 1 // Initialize with step 1
  });

  const { currentStep, displayStep, totalSteps, nextStep, prevStep, resetToFirstStep } = useWizardNavigation({
    validateStep: (step: number) => ({ isValid: validateSpecificStep(step), errors: [] }),
    onValidationError: (message: string) => showToast(message, 'error')
  });

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
  const handleSelectAllTranches = () => {
    // TODO: This would need to be implemented when tranche data is available
    // For now, just keep the existing selections
    console.warn('Select all tranches not implemented yet - need tranche data');
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
            tranches={{}} // TODO: Provide actual tranche data when available
            onDealAdd={handleDealAdd}
            onDealRemove={handleDealRemove}
            onTrancheToggle={handleTrancheToggle}
            onSelectAllTranches={handleSelectAllTranches}
            onDeselectAllTranches={handleDeselectAllTranches}
            loading={false} // TODO: Use actual loading state when deal/tranche loading is implemented
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