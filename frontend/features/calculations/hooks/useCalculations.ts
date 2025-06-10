// frontend/features/calculations/hooks/useCalculations.ts
import { useState, useEffect } from 'react';
import { useToast } from '@/context/ToastContext';
import { calculationsApi } from '@/services/calculationsApi';
import type { Calculation } from '@/types/calculations';

export const useCalculations = () => {
  const { showToast } = useToast();
  const [calculations, setCalculations] = useState<Calculation[]>([]);
  const [filteredCalculations, setFilteredCalculations] = useState<Calculation[]>([]);
  const [selectedFilter, setSelectedFilter] = useState<string>('all');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [calculationUsage, setCalculationUsage] = useState<Record<number, any>>({});

  const fetchCalculations = async (): Promise<void> => {
    setIsLoading(true);
    try {
      // Fetch only user-defined calculations
      const response = await calculationsApi.getUserDefinedCalculations();
      setCalculations(response.data);
    } catch (error) {
      console.error('Error fetching user calculations:', error);
      showToast('Error loading user calculations. Please refresh the page.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchCalculationUsage = async () => {
    const usageMap: Record<number, any> = {};
    
    for (const calc of calculations) {
      try {
        const response = await calculationsApi.getCalculationUsage(calc.id);
        usageMap[calc.id] = response.data;
      } catch (error) {
        console.error(`Error fetching usage for calculation ${calc.id}:`, error);
        usageMap[calc.id] = { is_in_use: false, report_count: 0, reports: [] };
      }
    }
    
    setCalculationUsage(usageMap);
  };

  const deleteCalculation = async (id: number, name: string): Promise<void> => {
    // Check if calculation is in use
    const usage = calculationUsage[id];
    if (usage?.is_in_use) {
      const reportNames = usage.reports.map((r: any) => r.report_name).join(', ');
      showToast(
        `Cannot delete calculation "${name}" because it is currently being used in the following report templates: ${reportNames}. Please remove the calculation from these reports before deleting it.`,
        'error'
      );
      return;
    }

    if (!window.confirm(`Are you sure you want to delete "${name}"?`)) {
      return;
    }

    try {
      await calculationsApi.deleteCalculation(id);
      showToast(`Calculation "${name}" deleted successfully!`, 'success');
      fetchCalculations();
    } catch (error: any) {
      console.error('Error deleting calculation:', error);
      
      // Extract detailed error message from API response
      let errorMessage = `Error deleting calculation: ${error.message}`;
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      
      showToast(errorMessage, 'error');
    }
  };

  const filterCalculations = (): void => {
    let filtered = calculations;
    
    if (selectedFilter === 'deal') {
      filtered = calculations.filter(calc => calc.group_level === 'deal');
    } else if (selectedFilter === 'tranche') {
      filtered = calculations.filter(calc => calc.group_level === 'tranche');
    }
    
    setFilteredCalculations(filtered);
  };

  useEffect(() => {
    fetchCalculations();
  }, []);

  useEffect(() => {
    if (calculations.length > 0) {
      fetchCalculationUsage();
    }
  }, [calculations]);

  useEffect(() => {
    filterCalculations();
  }, [calculations, selectedFilter]);

  return {
    calculations,
    filteredCalculations,
    selectedFilter,
    setSelectedFilter,
    isLoading,
    calculationUsage,
    fetchCalculations,
    deleteCalculation
  };
};