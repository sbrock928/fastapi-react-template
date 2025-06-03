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
  DealSelectionStep,
  TrancheSelectionStep,
  FieldSelectionStep,
  ReviewConfigurationStep
} from './wizardSteps';
import WizardNavigation from './WizardNavigation';
import type { ReportConfig, Deal, TrancheReportSummary, AvailableField } from '@/types/reporting';

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
    selectedFields,
    setReportName,
    setReportDescription,
    setReportScope,
    setSelectedDeals,
    setSelectedTranches,
    setSelectedFields,
    resetForm
  } = useReportBuilderForm({ editingReport, isEditMode });

  // Data management
  const {
    deals,
    tranches,
    availableFields,
    dealsLoading,
    tranchesLoading,
    fieldsLoading
  } = useReportBuilderData({ reportScope, selectedDeals, isEditMode });

  // Validation management
  const formState = {
    reportName,
    reportDescription,
    reportScope,
    selectedDeals,
    selectedTranches,
    selectedFields
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
    reportScope,
    onValidationError: (message: string) => showToast(message, 'error'),
    validateStep: validateSpecificStep
  });

  // Update wizard step state when navigation changes
  React.useEffect(() => {
    setCurrentWizardStep(currentStep);
  }, [currentStep]);

  // Handle deal selection
  const handleDealToggle = (dlNbr: number) => {
    setSelectedDeals((prev: number[]) => {
      if (prev.includes(dlNbr)) {
        // Remove deal and its tranches
        const newSelected = prev.filter((id: number) => id !== dlNbr);
        setSelectedTranches((prevTranches: Record<number, string[]>) => {
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

  // Handle select all deals
  const handleSelectAllDeals = () => {
    const allDealNumbers = deals.map((deal: Deal) => deal.dl_nbr);
    setSelectedDeals(allDealNumbers);
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
    // Final validation before saving
    const finalValidation = validateSpecificStep(5);
    if (!finalValidation.isValid) {
      finalValidation.errors.forEach((error: any) => {
        showToast(error.message, 'error');
      });
      return;
    }

    setLoading(true);
    
    try {
      const transformedSelectedDeals = selectedDeals.map((dlNbr: number) => ({
        dl_nbr: dlNbr,
        selected_tranches: (selectedTranches[dlNbr] || []).map((trId: string) => ({
          dl_nbr: dlNbr,
          tr_id: trId
        }))
      }));

      if (isEditMode && editingReport?.id) {
        const updateData = {
          name: reportName,
          description: reportDescription || undefined,
          scope: reportScope as 'DEAL' | 'TRANCHE',
          selected_deals: transformedSelectedDeals,
          selected_fields: selectedFields
        };

        await reportingApi.updateReport(editingReport.id, updateData);
        showToast('Report configuration updated successfully!', 'success');
      } else {
        const reportConfig = {
          name: reportName,
          description: reportDescription || undefined,
          scope: reportScope as 'DEAL' | 'TRANCHE',
          created_by: 'current_user',
          selected_deals: transformedSelectedDeals,
          selected_fields: selectedFields
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

  // Auto-select default fields when fields are loaded (only for new reports)
  React.useEffect(() => {
    if (availableFields.length > 0 && !isEditMode && selectedFields.length === 0) {
      const defaultFields = availableFields
        .filter((field: AvailableField) => field.is_default)
        .map((field: AvailableField) => ({
          field_name: field.field_name,
          display_name: field.display_name,
          field_type: field.field_type,
          is_required: false
        }));
      setSelectedFields(defaultFields);
    }
  }, [availableFields, isEditMode, selectedFields.length, setSelectedFields]);

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
          <DealSelectionStep
            deals={deals}
            selectedDeals={selectedDeals}
            onDealToggle={handleDealToggle}
            onSelectAllDeals={handleSelectAllDeals}
            loading={dealsLoading}
          />
        );

      case 3:
        return (
          <TrancheSelectionStep
            reportScope={reportScope}
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
          <FieldSelectionStep
            reportScope={reportScope}
            availableFields={availableFields}
            selectedFields={selectedFields}
            onFieldsChange={setSelectedFields}
            loading={fieldsLoading}
          />
        );

      case 5:
        return (
          <ReviewConfigurationStep
            reportName={reportName}
            reportDescription={reportDescription}
            reportScope={reportScope}
            selectedDeals={selectedDeals}
            selectedTranches={selectedTranches}
            selectedFields={selectedFields}
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