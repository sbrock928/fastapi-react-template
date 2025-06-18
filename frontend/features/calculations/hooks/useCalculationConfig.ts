// frontend/features/calculations/hooks/useCalculationConfig.ts
// Updated to work with the new separated calculation system

import { useState } from 'react';
import { useToast } from '@/context/ToastContext';
import { calculationsApi } from '@/services/calculationsApi';
import type { 
  UserCalculation,
  CalculationField, 
  AggregationFunctionInfo, 
  SourceModelInfo, 
  GroupLevelInfo, 
  CalculationForm,
  CalculationConfig,
  UserCalculationCreateRequest,
  UserCalculationUpdateRequest
} from '@/types/calculations';
import { INITIAL_CALCULATION_FORM } from '@/types/calculations';

export const useCalculationConfig = () => {
  const { showToast } = useToast();
  const [allAvailableFields, setAllAvailableFields] = useState<Record<string, CalculationField[]>>({});
  const [aggregationFunctions, setAggregationFunctions] = useState<AggregationFunctionInfo[]>([]);
  const [sourceModels, setSourceModels] = useState<SourceModelInfo[]>([]);
  const [groupLevels, setGroupLevels] = useState<GroupLevelInfo[]>([]);
  const [fieldsLoading, setFieldsLoading] = useState<boolean>(false);
  const [configError, setConfigError] = useState<string | null>(null);
  const [hasLoadedConfig, setHasLoadedConfig] = useState<boolean>(false);

  const fetchCalculationConfig = async (): Promise<void> => {
    setFieldsLoading(true);
    setConfigError(null);
    
    try {
      const response = await calculationsApi.getCalculationConfig();
      const data: CalculationConfig = response.data.data || response.data;
      
      // Process static_fields into allAvailableFields format
      const fieldsMap: Record<string, CalculationField[]> = {};
      
      if (data.static_fields) {
        data.static_fields.forEach(field => {
          const [modelName, fieldName] = field.field_path.split('.');
          
          // Map the lowercase model names to the exact Source Model values from API
          let modelKey: string;
          switch (modelName.toLowerCase()) {
            case 'deal':
              modelKey = 'deal'; // Keep lowercase to match source model values
              break;
            case 'tranche':
              modelKey = 'tranche'; // Keep lowercase to match source model values
              break;
            case 'tranchebal':
              modelKey = 'tranchebal'; // Keep lowercase to match source model values
              break;
            default:
              modelKey = modelName.toLowerCase();
          }
          
          if (!fieldsMap[modelKey]) {
            fieldsMap[modelKey] = [];
          }
          
          fieldsMap[modelKey].push({
            value: fieldName,
            label: field.name,
            type: field.type as any,
            description: field.description,
            nullable: field.nullable
          });
        });
      }
      
      // Set all configuration data from API
      setAllAvailableFields(fieldsMap);
      setAggregationFunctions(data.aggregation_functions || []);
      setSourceModels(data.source_models || []);
      setGroupLevels(data.group_levels || []);
      setHasLoadedConfig(true);
      
      console.log('✅ Loaded calculation configuration from API:', {
        staticFields: data.static_fields?.length || 0,
        aggregationFunctions: data.aggregation_functions?.length || 0,
        sourceModels: data.source_models?.length || 0,
        groupLevels: data.group_levels?.length || 0,
        fieldsMap: Object.keys(fieldsMap).map(key => `${key}: ${fieldsMap[key].length} fields`)
      });
    } catch (error: any) {
      console.error('❌ Error fetching calculation configuration:', error);
      
      const errorMessage = error.response?.data?.detail || error.message || 'Unknown error occurred';
      setConfigError(`Failed to load calculation configuration: ${errorMessage}`);
      
      showToast(
        'Unable to load calculation configuration from server. Please check your connection and try again.',
        'error'
      );
      
      // Clear all config data on error
      setAllAvailableFields({});
      setAggregationFunctions([]);
      setSourceModels([]);
      setGroupLevels([]);
    } finally {
      setFieldsLoading(false);
    }
  };

  const retryLoadConfig = async (): Promise<void> => {
    await fetchCalculationConfig();
  };

  const isConfigAvailable = (): boolean => {
    return hasLoadedConfig && 
           aggregationFunctions.length > 0 && 
           sourceModels.length > 0 && 
           groupLevels.length > 0;
  };

  return {
    // Configuration data
    allAvailableFields,
    aggregationFunctions,
    sourceModels,
    groupLevels,
    
    // Loading and error states
    fieldsLoading,
    configError,
    hasLoadedConfig,
    
    // Helper functions
    fetchCalculationConfig,
    retryLoadConfig,
    isConfigAvailable
  };
};

export const useCalculationForm = (editingCalculation: UserCalculation | null) => {
  const { showToast } = useToast();
  const [calculation, setCalculation] = useState<CalculationForm>(INITIAL_CALCULATION_FORM);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState<boolean>(false);

  const initializeForm = (calc: UserCalculation | null) => {
    if (calc) {
      // Edit mode - map calculation to form
      if (calc.calculation_type === 'user_aggregation') {
        setCalculation({
          name: calc.name,
          description: calc.description || '',
          function_type: calc.aggregation_function,
          source: calc.source_model,
          source_field: calc.source_field,
          level: calc.group_level,
          weight_field: calc.weight_field || ''
        });
      }
    } else {
      // Create mode
      setCalculation(INITIAL_CALCULATION_FORM);
    }
    setError(null);
  };

  const updateCalculation = (updates: Partial<CalculationForm>) => {
    setCalculation(prev => ({ ...prev, ...updates }));
  };

  const saveCalculation = async (onSuccess?: () => void): Promise<boolean> => {
    if (!calculation.name || !calculation.function_type || !calculation.level) {
      setError('Please fill in all required fields (Name, Function Type, and Group Level)');
      return false;
    }

    // Additional validation for user-defined calculations
    if (calculation.function_type !== 'SYSTEM_FIELD' && calculation.function_type !== 'SYSTEM_SQL') {
      if (!calculation.source || !calculation.source_field) {
        setError('Please fill in all required fields (Source Model and Source Field)');
        return false;
      }

      if (calculation.function_type === 'WEIGHTED_AVG' && !calculation.weight_field) {
        setError('Weight field is required for weighted average calculations');
        return false;
      }
    }

    setIsSaving(true);
    try {
      // Map frontend field names to backend expected field names
      const payload: UserCalculationCreateRequest | UserCalculationUpdateRequest = {
        name: calculation.name,
        description: calculation.description,
        aggregation_function: calculation.function_type as any,
        source_model: calculation.source as any,
        source_field: calculation.source_field,
        group_level: calculation.level as any,
        weight_field: calculation.weight_field || undefined
      };

      let savedCalculation: UserCalculation;
      if (editingCalculation) {
        const response = await calculationsApi.updateCalculation(editingCalculation.id, payload as UserCalculationUpdateRequest);
        savedCalculation = response.data;
      } else {
        const response = await calculationsApi.createCalculation(payload as UserCalculationCreateRequest);
        savedCalculation = response.data;
      }
      
      showToast(`Calculation "${savedCalculation.name}" ${editingCalculation ? 'updated' : 'saved'} successfully!`, 'success');
      
      // Reset form and call success callback
      setCalculation(INITIAL_CALCULATION_FORM);
      setError(null);
      onSuccess?.();
      return true;
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
      return false;
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