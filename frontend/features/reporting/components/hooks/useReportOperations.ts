import { useState } from 'react';
import { reportingApi } from '@/services/api';
import { useToast } from '@/context/ToastContext';
import {
  createReportConfigPayload,
  createUpdateReportPayload,
  parseApiError,
  validateReportBeforeSave,
  getSuccessMessage
} from '../utils/reportBusinessLogic';
import type { ReportBuilderFormState } from './useReportBuilderForm';
import type { ReportConfig } from '@/types/reporting';

interface UseReportOperationsProps {
  onSuccess: () => void;
  onFormReset?: () => void;
  onNavigationReset?: () => void;
}

export const useReportOperations = ({ 
  onSuccess, 
  onFormReset, 
  onNavigationReset 
}: UseReportOperationsProps) => {
  const [loading, setLoading] = useState<boolean>(false);
  const { showToast } = useToast();

  /**
   * Save a new report configuration
   */
  const saveNewReport = async (formState: ReportBuilderFormState): Promise<boolean> => {
    // Pre-save validation
    const validation = validateReportBeforeSave(formState);
    if (!validation.isValid) {
      validation.errors.forEach(error => {
        showToast(error, 'error');
      });
      return false;
    }

    setLoading(true);
    
    try {
      const reportConfig = createReportConfigPayload(formState);
      await reportingApi.createReport(reportConfig);
      
      showToast(getSuccessMessage('create'), 'success');
      
      // Call success callbacks
      onSuccess();
      onFormReset?.();
      onNavigationReset?.();
      
      return true;
    } catch (error: any) {
      console.error('Error saving report:', error);
      const errorMessage = parseApiError(error, 'saving');
      showToast(errorMessage, 'error');
      return false;
    } finally {
      setLoading(false);
    }
  };

  /**
   * Update an existing report configuration
   */
  const updateExistingReport = async (
    reportId: number, // Changed from string to number
    formState: ReportBuilderFormState
  ): Promise<boolean> => {
    // Pre-update validation
    const validation = validateReportBeforeSave(formState);
    if (!validation.isValid) {
      validation.errors.forEach(error => {
        showToast(error, 'error');
      });
      return false;
    }

    setLoading(true);
    
    try {
      const updateData = createUpdateReportPayload(formState);
      await reportingApi.updateReport(reportId, updateData);
      
      showToast(getSuccessMessage('update'), 'success');
      
      // Call success callback
      onSuccess();
      
      return true;
    } catch (error: any) {
      console.error('Error updating report:', error);
      const errorMessage = parseApiError(error, 'updating');
      showToast(errorMessage, 'error');
      return false;
    } finally {
      setLoading(false);
    }
  };

  /**
   * Save or update report based on mode
   */
  const saveOrUpdateReport = async (
    formState: ReportBuilderFormState,
    editingReport?: ReportConfig | null,
    isEditMode: boolean = false
  ): Promise<boolean> => {
    if (isEditMode && editingReport?.id) {
      return await updateExistingReport(editingReport.id, formState);
    } else {
      return await saveNewReport(formState);
    }
  };

  return {
    loading,
    saveNewReport,
    updateExistingReport,
    saveOrUpdateReport
  };
};