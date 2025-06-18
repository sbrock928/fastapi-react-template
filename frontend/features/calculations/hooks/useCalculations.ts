// frontend/features/calculations/hooks/useCalculations.ts
// Updated to work with the new separated calculation system

import { useState, useEffect } from 'react';
import { useToast } from '@/context/ToastContext';
import { calculationsApi } from '@/services/calculationsApi';
import type { UserCalculation, SystemCalculation } from '@/types/calculations';

export const useCalculations = () => {
  const { showToast } = useToast();
  const [calculations, setCalculations] = useState<UserCalculation[]>([]);
  const [filteredCalculations, setFilteredCalculations] = useState<UserCalculation[]>([]);
  const [selectedFilter, setSelectedFilter] = useState<string>('all');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [calculationUsage, setCalculationUsage] = useState<Record<number, any>>({});

  const fetchCalculations = async (): Promise<void> => {
    setIsLoading(true);
    try {
      // Fetch all calculations using the unified endpoint
      const response = await calculationsApi.getAllCalculations();
      setCalculations(response.data.user_calculations);
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
    fetchCalculationUsage, // Expose this so components can refresh usage data
    deleteCalculation
  };
};

// New hook for system calculations
export const useSystemCalculations = () => {
  const { showToast } = useToast();
  const [systemCalculations, setSystemCalculations] = useState<SystemCalculation[]>([]);
  const [filteredSystemCalculations, setFilteredSystemCalculations] = useState<SystemCalculation[]>([]);
  const [selectedFilter, setSelectedFilter] = useState<string>('all');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [systemUsage, setSystemUsage] = useState<Record<number, any>>({});

  const fetchSystemCalculations = async (): Promise<void> => {
    setIsLoading(true);
    try {
      // Use the unified endpoint instead of the deprecated method
      const response = await calculationsApi.getAllCalculations();
      setSystemCalculations(response.data.system_calculations);
    } catch (error) {
      console.error('Error fetching system calculations:', error);
      showToast('Error loading system calculations. Please refresh the page.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchSystemCalculationUsage = async () => {
    const usageMap: Record<number, any> = {};
    
    for (const calc of systemCalculations) {
      try {
        const response = await calculationsApi.getCalculationUsage(calc.id);
        usageMap[calc.id] = response.data;
      } catch (error) {
        console.error(`Error fetching usage for system calculation ${calc.id}:`, error);
        usageMap[calc.id] = { is_in_use: false, report_count: 0, reports: [] };
      }
    }
    
    setSystemUsage(usageMap);
  };

  const createSystemSqlCalculation = async (
    formState: any,
    onSuccess?: () => void
  ): Promise<boolean> => {
    if (!formState.name || !formState.source_field || !formState.weight_field || !formState.level) {
      showToast('Please fill in all required fields for system SQL calculation', 'error');
      return false;
    }

    setIsLoading(true);
    try {
      // First validate the SQL
      const validationResponse = await calculationsApi.validateSystemSql({
        sql_text: formState.source_field, // SQL stored in source_field
        group_level: formState.level,
        result_column_name: formState.weight_field // Result column stored in weight_field
      });

      if (!validationResponse.data.validation_result.is_valid) {
        const errors = validationResponse.data.validation_result.errors.join(', ');
        showToast(`SQL validation failed: ${errors}`, 'error');
        return false;
      }

      // Create the system SQL calculation
      const payload = {
        name: formState.name,
        description: formState.description || undefined,
        group_level: formState.level,
        raw_sql: formState.source_field, // SQL stored in source_field
        result_column_name: formState.weight_field // Result column stored in weight_field
      };

      const response = await calculationsApi.createSystemSqlCalculation(payload);
      showToast(`System SQL calculation "${response.data.name}" created successfully!`, 'success');
      
      onSuccess?.();
      return true;
    } catch (error: any) {
      console.error('Error creating system SQL calculation:', error);
      
      let errorMessage = 'Error creating system SQL calculation';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      
      showToast(errorMessage, 'error');
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const filterCalculations = (): void => {
    let filtered = systemCalculations;
    
    if (selectedFilter === 'deal') {
      filtered = systemCalculations.filter(calc => calc.group_level === 'deal');
    } else if (selectedFilter === 'tranche') {
      filtered = systemCalculations.filter(calc => calc.group_level === 'tranche');
    } else if (selectedFilter === 'system-sql') {
      filtered = systemCalculations.filter(calc => calc.calculation_type === 'system_sql');
    }
    
    setFilteredSystemCalculations(filtered);
  };

  useEffect(() => {
    fetchSystemCalculations();
  }, []);

  useEffect(() => {
    if (systemCalculations.length > 0) {
      fetchSystemCalculationUsage();
    }
  }, [systemCalculations]);

  useEffect(() => {
    filterCalculations();
  }, [systemCalculations, selectedFilter]);

  return {
    systemCalculations,
    filteredSystemCalculations,
    selectedFilter,
    setSelectedFilter,
    isLoading,
    systemUsage,
    fetchSystemCalculations,
    createSystemSqlCalculation
  };
};