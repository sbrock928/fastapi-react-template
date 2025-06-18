// frontend/features/calculations/hooks/useSystemCalculations.ts
import { useState, useEffect } from 'react';
import { useToast } from '@/context/ToastContext';
import { calculationsApi } from '@/services/calculationsApi';
import type { SystemCalculation, CalculationForm } from '@/types/calculations';

export const useSystemCalculations = () => {
  const { showToast } = useToast();
  const [systemCalculations, setSystemCalculations] = useState<SystemCalculation[]>([]);
  const [filteredSystemCalculations, setFilteredSystemCalculations] = useState<SystemCalculation[]>([]);
  const [selectedFilter, setSelectedFilter] = useState<string>('all');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const fetchSystemCalculations = async (): Promise<void> => {
    setIsLoading(true);
    try {
      // Use the unified endpoint and extract system calculations
      const response = await calculationsApi.getAllCalculations();
      setSystemCalculations(response.data.system_calculations);
    } catch (error) {
      console.error('Error fetching system calculations:', error);
      showToast('Error loading system calculations. Please refresh the page.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const createSystemSqlCalculation = async (
    formState: CalculationForm,
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
        group_level: formState.level as "deal" | "tranche",
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
        group_level: formState.level as "deal" | "tranche",
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
      // All system calculations are system-sql type now
      filtered = systemCalculations;
    }
    
    setFilteredSystemCalculations(filtered);
  };

  useEffect(() => {
    fetchSystemCalculations();
  }, []);

  useEffect(() => {
    filterCalculations();
  }, [systemCalculations, selectedFilter]);

  return {
    systemCalculations,
    filteredSystemCalculations,
    selectedFilter,
    setSelectedFilter,
    isLoading,
    fetchSystemCalculations,
    createSystemSqlCalculation
  };
};