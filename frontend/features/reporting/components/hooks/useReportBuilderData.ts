import { useState, useEffect } from 'react';
import { reportingApi } from '@/services/api';
import { useToast } from '@/context/ToastContext';
import { useReportContext } from '@/context/ReportContext'; // Added import for context
import type { TrancheReportSummary, AvailableCalculation } from '@/types/reporting';

interface UseReportBuilderDataProps {
  reportScope: 'DEAL' | 'TRANCHE' | '';
  selectedDeals: number[];
  isEditMode: boolean;
}

export const useReportBuilderData = ({ reportScope, selectedDeals, isEditMode }: UseReportBuilderDataProps) => {
  const { showToast } = useToast();
  const { deals, dealsLoading, loadDealsOnce } = useReportContext(); // Use context for deals
  
  // Data state (removed deals state since it comes from context)
  const [tranches, setTranches] = useState<Record<string, TrancheReportSummary[]>>({});
  const [availableCalculations, setAvailableCalculations] = useState<AvailableCalculation[]>([]);
  
  // Loading states (removed dealsLoading since it comes from context)
  const [tranchesLoading, setTranchesLoading] = useState<boolean>(false);
  const [calculationsLoading, setCalculationsLoading] = useState<boolean>(false);

  // Load deals once when hook initializes (only if not already loaded)
  useEffect(() => {
    loadDealsOnce();
  }, [loadDealsOnce]);

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
    // Data (deals now comes from context)
    deals,
    tranches,
    availableCalculations,
    
    // Loading states (dealsLoading now comes from context)
    dealsLoading,
    tranchesLoading,
    calculationsLoading,
    
    // Functions (removed loadDeals since it's handled by context)
    loadAvailableCalculations
  };
};