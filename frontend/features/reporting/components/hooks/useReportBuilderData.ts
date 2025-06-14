// frontend/features/reporting/components/hooks/useReportBuilderData.ts
// Updated to work with the new separated calculation system

import { useState, useCallback, useEffect } from 'react';
import reportingApi from '@/services/reportingApi';
import type { AvailableCalculation } from '@/types/reporting';
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

  // Load available calculations - FIXED to use reportingApi instead of calculationsApi
  const loadAvailableCalculations = useCallback(async () => {
    if (!reportScope || (reportScope !== 'DEAL' && reportScope !== 'TRANCHE')) {
      setAvailableCalculations([]);
      return;
    }

    setCalculationsLoading(true);
    try {
      // Use reportingApi.getAvailableCalculations instead of calculationsApi
      const response = await reportingApi.getAvailableCalculations(reportScope);
      setAvailableCalculations(response.data);
    } catch (error) {
      console.error('Error loading available calculations:', error);
      showToast('Error loading available calculations', 'error');
      setAvailableCalculations([]);
    } finally {
      setCalculationsLoading(false);
    }
  }, [reportScope, showToast]);

  // Automatically load calculations when reportScope changes
  useEffect(() => {
    loadAvailableCalculations();
  }, [loadAvailableCalculations]);

  return {
    // Data
    availableCalculations,
    
    // Loading states
    calculationsLoading,
    
    // Functions
    loadAvailableCalculations
  };
};