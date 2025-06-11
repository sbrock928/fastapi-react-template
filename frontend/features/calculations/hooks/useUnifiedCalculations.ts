// frontend/features/calculations/hooks/useUnifiedCalculations.ts
import { useState, useEffect } from 'react';
import { useToast } from '@/context/ToastContext';
import { calculationsApi } from '@/services/calculationsApi';
import type { UserCalculation, SystemCalculation } from '@/types/calculations';

interface UnifiedCalculationsData {
  user_calculations: UserCalculation[];
  system_calculations: SystemCalculation[];
  summary: {
    total_calculations: number;
    user_calculation_count: number;
    system_calculation_count: number;
    user_in_use_count: number;
    system_in_use_count: number;
    total_in_use: number;
    group_level_filter?: string;
  };
}

export const useUnifiedCalculations = (groupLevel?: string) => {
  const { showToast } = useToast();
  const [data, setData] = useState<UnifiedCalculationsData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAllCalculations = async (): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await calculationsApi.getAllCalculations(groupLevel);
      setData(response.data);
    } catch (error) {
      console.error('Error fetching calculations:', error);
      const errorMessage = 'Error loading calculations. Please refresh the page.';
      setError(errorMessage);
      showToast(errorMessage, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAllCalculations();
  }, [groupLevel]);

  return {
    userCalculations: data?.user_calculations || [],
    systemCalculations: data?.system_calculations || [],
    summary: data?.summary || {
      total_calculations: 0,
      user_calculation_count: 0,
      system_calculation_count: 0,
      user_in_use_count: 0,
      system_in_use_count: 0,
      total_in_use: 0
    },
    isLoading,
    error,
    refetch: fetchAllCalculations
  };
};