// frontend/features/reporting/components/hooks/useReportBuilderData.ts
// Updated to work with the new separated calculation system

import { useState, useCallback } from 'react';
import { calculationsApi } from '@/services/calculationsApi';
import type { AvailableCalculation } from '@/types/calculations';
import { useToast } from '@/context/ToastContext';

interface UseReportBuilderDataProps {
  reportScope: 'DEAL' | 'TRANCHE' | '';
}

export const useReportBuilderData = ({ reportScope }: UseReportBuilderDataProps) => {
  const { showToast } = useToast();
  
  // Local state
  const [availableCalculations, setAvailableCalculations] = useState<AvailableCalculation[]>([]);
  
  // Loading states
  const [calculationsLoading, setCalculationsLoading] = useState(false);

  // Load available calculations - UPDATED for new string format
  const loadAvailableCalculations = useCallback(async () => {
    if (!reportScope || (reportScope !== 'DEAL' && reportScope !== 'TRANCHE')) {
      setAvailableCalculations([]);
      return;
    }

    setCalculationsLoading(true);
    try {
      // The backend now returns calculations with the new string ID format
      const response = await calculationsApi.getAvailableCalculations(reportScope);
      setAvailableCalculations(response.data);
    } catch (error) {
      console.error('Error loading available calculations:', error);
      showToast('Error loading available calculations', 'error');
      setAvailableCalculations([]);
    } finally {
      setCalculationsLoading(false);
    }
  }, [reportScope, showToast]);

  return {
    // Data
    availableCalculations,
    
    // Loading states
    calculationsLoading,
    
    // Functions
    loadAvailableCalculations
  };
};