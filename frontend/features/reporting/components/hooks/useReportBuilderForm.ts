import { useState, useEffect } from 'react';
import type { ReportConfig, ReportField } from '@/types/reporting';

export interface ReportBuilderFormState {
  reportName: string;
  reportDescription: string;
  reportScope: 'DEAL' | 'TRANCHE' | '';
  selectedDeals: number[];
  selectedTranches: Record<number, string[]>;
  selectedFields: ReportField[];
}

interface UseReportBuilderFormProps {
  editingReport?: ReportConfig | null;
  isEditMode: boolean;
}

export const useReportBuilderForm = ({ editingReport, isEditMode }: UseReportBuilderFormProps) => {
  const [formState, setFormState] = useState<ReportBuilderFormState>({
    reportName: '',
    reportDescription: '',
    reportScope: '',
    selectedDeals: [],
    selectedTranches: {},
    selectedFields: []
  });

  // Initialize form with editing data if in edit mode
  useEffect(() => {
    if (isEditMode && editingReport) {
      setFormState({
        reportName: editingReport.name,
        reportDescription: editingReport.description || '',
        reportScope: editingReport.scope,
        selectedDeals: editingReport.selected_deals?.map(deal => deal.dl_nbr) || [],
        selectedTranches: editingReport.selected_deals?.reduce((acc, deal) => {
          if (deal.selected_tranches && deal.selected_tranches.length > 0) {
            acc[deal.dl_nbr] = deal.selected_tranches.map(tranche => tranche.tr_id);
          }
          return acc;
        }, {} as Record<number, string[]>) || {},
        selectedFields: editingReport.selected_fields || []
      });
    } else {
      // Reset form for new report
      setFormState({
        reportName: '',
        reportDescription: '',
        reportScope: '',
        selectedDeals: [],
        selectedTranches: {},
        selectedFields: []
      });
    }
  }, [isEditMode, editingReport]);

  // Individual state setters for backward compatibility
  const setReportName = (name: string) => {
    setFormState(prev => ({ ...prev, reportName: name }));
  };

  const setReportDescription = (description: string) => {
    setFormState(prev => ({ ...prev, reportDescription: description }));
  };

  const setReportScope = (scope: 'DEAL' | 'TRANCHE' | '') => {
    setFormState(prev => ({ ...prev, reportScope: scope }));
  };

  const setSelectedDeals = (deals: number[] | ((prev: number[]) => number[])) => {
    if (typeof deals === 'function') {
      setFormState(prev => ({ ...prev, selectedDeals: deals(prev.selectedDeals) }));
    } else {
      setFormState(prev => ({ ...prev, selectedDeals: deals }));
    }
  };

  const setSelectedTranches = (tranches: Record<number, string[]> | ((prev: Record<number, string[]>) => Record<number, string[]>)) => {
    if (typeof tranches === 'function') {
      setFormState(prev => ({ ...prev, selectedTranches: tranches(prev.selectedTranches) }));
    } else {
      setFormState(prev => ({ ...prev, selectedTranches: tranches }));
    }
  };

  const setSelectedFields = (fields: ReportField[]) => {
    setFormState(prev => ({ ...prev, selectedFields: fields }));
  };

  // Reset form
  const resetForm = () => {
    setFormState({
      reportName: '',
      reportDescription: '',
      reportScope: '',
      selectedDeals: [],
      selectedTranches: {},
      selectedFields: []
    });
  };

  return {
    // State values
    reportName: formState.reportName,
    reportDescription: formState.reportDescription,
    reportScope: formState.reportScope,
    selectedDeals: formState.selectedDeals,
    selectedTranches: formState.selectedTranches,
    selectedFields: formState.selectedFields,
    
    // State setters
    setReportName,
    setReportDescription,
    setReportScope,
    setSelectedDeals,
    setSelectedTranches,
    setSelectedFields,
    
    // Utility functions
    resetForm
  };
};