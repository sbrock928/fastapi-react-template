import { useState } from 'react';
import { useToast } from '@/context/ToastContext';
import { calculationsApi } from '@/services/calculationsApi';
import type { 
  Calculation, 
  CalculationField, 
  AggregationFunction, 
  SourceModel, 
  GroupLevel, 
  CalculationForm, 
  CalculationConfig 
} from '@/types/calculations';
import { 
  DEFAULT_FIELD_MAPPINGS, 
  DEFAULT_AGGREGATION_FUNCTIONS, 
  DEFAULT_SOURCE_MODELS, 
  DEFAULT_GROUP_LEVELS, 
  INITIAL_CALCULATION_FORM 
} from '../constants/calculationConstants';

export const useCalculationConfig = () => {
  const { showToast } = useToast();
  const [allAvailableFields, setAllAvailableFields] = useState<Record<string, CalculationField[]>>({});
  const [aggregationFunctions, setAggregationFunctions] = useState<AggregationFunction[]>([]);
  const [sourceModels, setSourceModels] = useState<SourceModel[]>([]);
  const [groupLevels, setGroupLevels] = useState<GroupLevel[]>([]);
  const [fieldsLoading, setFieldsLoading] = useState<boolean>(false);

  const fetchCalculationConfig = async (): Promise<void> => {
    setFieldsLoading(true);
    try {
      const response = await calculationsApi.getCalculationConfig();
      const data: CalculationConfig = response.data.data || {};
      
      // Set all configuration data from API
      setAllAvailableFields(data.field_mappings || {});
      setAggregationFunctions(data.aggregation_functions || []);
      setSourceModels(data.source_models || []);
      setGroupLevels(data.group_levels || []);
    } catch (error) {
      console.error('Error fetching calculation configuration:', error);
      showToast('Error loading calculation configuration. Using default settings.', 'error');
      
      // Fallback to default configuration if API fails
      setAllAvailableFields(DEFAULT_FIELD_MAPPINGS);
      setAggregationFunctions(DEFAULT_AGGREGATION_FUNCTIONS);
      setSourceModels(DEFAULT_SOURCE_MODELS);
      setGroupLevels(DEFAULT_GROUP_LEVELS);
    } finally {
      setFieldsLoading(false);
    }
  };

  return {
    allAvailableFields,
    aggregationFunctions,
    sourceModels,
    groupLevels,
    fieldsLoading,
    fetchCalculationConfig
  };
};

export const useCalculationForm = (editingCalculation: Calculation | null) => {
  const { showToast } = useToast();
  const [calculation, setCalculation] = useState<CalculationForm>(INITIAL_CALCULATION_FORM);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState<boolean>(false);

  const initializeForm = (calc: Calculation | null) => {
    if (calc) {
      // Edit mode
      setCalculation({
        name: calc.name,
        description: calc.description || '',
        function_type: calc.aggregation_function,
        source: calc.source_model,
        source_field: calc.source_field,
        level: calc.group_level,
        weight_field: calc.weight_field || ''
      });
    } else {
      // Create mode
      setCalculation(INITIAL_CALCULATION_FORM);
    }
    setError(null);
  };

  const updateCalculation = (updates: Partial<CalculationForm>) => {
    setCalculation(prev => ({ ...prev, ...updates }));
  };

  const saveCalculation = async (onSuccess?: () => void): Promise<void> => {
    if (!calculation.name || !calculation.function_type || !calculation.source || !calculation.source_field) {
      setError('Please fill in all required fields (Name, Function Type, Source, and Source Field)');
      return;
    }

    if (calculation.function_type === 'WEIGHTED_AVG' && !calculation.weight_field) {
      setError('Weight field is required for weighted average calculations');
      return;
    }

    setIsSaving(true);
    try {
      // Map frontend field names to backend expected field names
      const payload = {
        name: calculation.name,
        description: calculation.description,
        aggregation_function: calculation.function_type,
        source_model: calculation.source,
        source_field: calculation.source_field,
        group_level: calculation.level,
        weight_field: calculation.weight_field || null
      };

      let savedCalculation: Calculation;
      if (editingCalculation) {
        const response = await calculationsApi.updateCalculation(editingCalculation.id, { ...payload, id: editingCalculation.id });
        savedCalculation = response.data;
      } else {
        const response = await calculationsApi.createCalculation(payload);
        savedCalculation = response.data;
      }
      
      showToast(`Calculation "${savedCalculation.name}" ${editingCalculation ? 'updated' : 'saved'} successfully!`, 'success');
      
      // Reset form and call success callback
      setCalculation(INITIAL_CALCULATION_FORM);
      setError(null);
      onSuccess?.();
    } catch (error: any) {
      console.error('Error saving calculation:', error);
      
      // Extract detailed error message from API response
      let errorMessage = 'Error saving calculation';
      
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      setError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  const resetForm = () => {
    setCalculation(INITIAL_CALCULATION_FORM);
    setError(null);
  };

  return {
    calculation,
    error,
    isSaving,
    setError,
    updateCalculation,
    saveCalculation,
    resetForm,
    initializeForm
  };
};