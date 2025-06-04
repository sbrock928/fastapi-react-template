import { useState, useEffect } from 'react';
import { reportingApi } from '@/services/api';
import { useToast } from '@/context/ToastContext';
import type { Deal, TrancheReportSummary, AvailableCalculation } from '@/types/reporting';

interface UseReportBuilderDataProps {
  reportScope: 'DEAL' | 'TRANCHE' | '';
  selectedDeals: number[];
  isEditMode: boolean;
}

export const useReportBuilderData = ({ reportScope, selectedDeals, isEditMode }: UseReportBuilderDataProps) => {
  const { showToast } = useToast();
  
  // Data state
  const [deals, setDeals] = useState<Deal[]>([]);
  const [tranches, setTranches] = useState<Record<string, TrancheReportSummary[]>>({});
  const [availableCalculations, setAvailableCalculations] = useState<AvailableCalculation[]>([]);
  
  // Loading states
  const [dealsLoading, setDealsLoading] = useState<boolean>(false);
  const [tranchesLoading, setTranchesLoading] = useState<boolean>(false);
  const [calculationsLoading, setCalculationsLoading] = useState<boolean>(false);

  // Load deals when hook initializes
  useEffect(() => {
    loadDeals();
  }, []);

  // Load available calculations when scope changes
  useEffect(() => {
    if (reportScope === 'DEAL' || reportScope === 'TRANCHE') {
      loadAvailableCalculations(reportScope);
    }
  }, [reportScope, isEditMode]);

  // Load tranches when deals are selected for both DEAL and TRANCHE scope
  useEffect(() => {
    const loadTranches = async () => {
      if (selectedDeals.length > 0 && (reportScope === 'TRANCHE' || reportScope === 'DEAL')) {
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
  }, [selectedDeals, reportScope, showToast]);

  // Load available deals
  const loadDeals = async () => {
    setDealsLoading(true);
    try {
      const response = await reportingApi.getDeals();
      setDeals(response.data);
    } catch (error) {
      console.error('Error loading deals:', error);
      showToast('Error loading deals', 'error');
    } finally {
      setDealsLoading(false);
    }
  };

  // Load available calculations based on scope
  const loadAvailableCalculations = async (scope: 'DEAL' | 'TRANCHE') => {
    setCalculationsLoading(true);
    try {
      const response = await reportingApi.getAvailableCalculations(scope);
      setAvailableCalculations(response.data);
    } catch (error) {
      console.error('Error loading available calculations:', error);
      showToast('Error loading available calculations', 'error');
    } finally {
      setCalculationsLoading(false);
    }
  };

  return {
    // Data
    deals,
    tranches,
    availableCalculations, // Changed from availableFields
    
    // Loading states
    dealsLoading,
    tranchesLoading,
    calculationsLoading, // Changed from fieldsLoading
    
    // Functions
    loadDeals,
    loadAvailableCalculations // Changed from loadAvailableFields
  };
};