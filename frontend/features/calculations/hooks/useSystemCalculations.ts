// frontend/features/calculations/hooks/useSystemCalculations.ts
import { useState, useEffect } from 'react';
import { useToast } from '@/context/ToastContext';
import { calculationsApi } from '@/services/calculationsApi';
import type { Calculation, CalculationForm } from '@/types/calculations';

export const useSystemCalculations = () => {
  const { showToast } = useToast();
  const [systemCalculations, setSystemCalculations] = useState<Calculation[]>([]);
  const [filteredSystemCalculations, setFilteredSystemCalculations] = useState<Calculation[]>([]);
  const [selectedFilter, setSelectedFilter] = useState<string>('all');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [systemUsage, setSystemUsage] = useState<Record<number, any>>({});

  const fetchSystemCalculations = async (): Promise<void> => {
    setIsLoading(true);
    try {
      // Fetch system calculations (both SYSTEM_FIELD and SYSTEM_SQL)
      const systemFieldResponse = await calculationsApi.getSystemCalculations();
      setSystemCalculations(systemFieldResponse.data);
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

  const createSystemFieldCalculation = async (
    formState: CalculationForm,
    onSuccess?: () => void
  ): Promise<boolean> => {
    if (!formState.name || !formState.source || !formState.source_field || !formState.level) {
      showToast('Please fill in all required fields for system field calculation', 'error');
      return false;
    }

    setIsLoading(true);
    try {
      // Map to backend API format for system field calculations
      const payload = {
        name: formState.name,
        description: formState.description || undefined,
        source_model: formState.source,
        field_name: formState.source_field,
        field_type: 'string', // Default, could be enhanced to detect from field
        group_level: formState.level
      };

      const response = await calculationsApi.createSystemFieldCalculation(payload);
      showToast(`System field calculation "${response.data.name}" created successfully!`, 'success');
      
      onSuccess?.();
      return true;
    } catch (error: any) {
      console.error('Error creating system field calculation:', error);
      
      let errorMessage = 'Error creating system field calculation';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      
      showToast(errorMessage, 'error');
      return false;
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
    } else if (selectedFilter === 'system-field') {
      filtered = systemCalculations.filter(calc => calc.calculation_type === 'SYSTEM_FIELD');
    } else if (selectedFilter === 'system-sql') {
      filtered = systemCalculations.filter(calc => calc.calculation_type === 'SYSTEM_SQL');
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
    createSystemFieldCalculation,
    createSystemSqlCalculation
  };
};