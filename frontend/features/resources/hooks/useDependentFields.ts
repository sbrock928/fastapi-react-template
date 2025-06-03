// frontend/features/resources/hooks/useDependentFields.ts
import { useState } from 'react';
import axios from 'axios';
import { useToast } from '@/context/ToastContext';
import type { ResourceConfig } from '@/types/resources';

interface UseDependentFieldsProps {
  resourceConfig: ResourceConfig;
  updateField: (name: string, value: any) => void;
}

export const useDependentFields = ({ resourceConfig, updateField }: UseDependentFieldsProps) => {
  const [dynamicOptions, setDynamicOptions] = useState<Record<string, any[]>>({});
  const [loadingFields, setLoadingFields] = useState<Record<string, boolean>>({});
  const { showToast } = useToast();

  // Fetch dependent options based on parent field value
  const fetchDependentOptions = async (parentField: string, parentValue: string) => {
    // Find all fields that depend on this parent
    const dependentFields = resourceConfig.columns.filter((column: any) => 
      column.dependsOn === parentField
    );

    for (const column of dependentFields) {
      try {
        // Set loading state for this field
        setLoadingFields(prev => ({ ...prev, [column.field]: true }));
        
        // Clear previous options
        setDynamicOptions(prev => ({ 
          ...prev, 
          [column.field]: [] 
        }));
        
        // Clear the field value
        updateField(column.field, '');

        // Different endpoints based on dependency type
        let endpoint = '';
        if (parentField === 'department' && column.field === 'position') {
          endpoint = `/api/departments/${encodeURIComponent(parentValue)}/positions`;
        }
        // Add more conditions for other dependent fields as needed

        if (endpoint) {
          const response = await axios.get(endpoint);
          if (response.data) {
            setDynamicOptions(prev => ({
              ...prev,
              [column.field]: response.data
            }));
          }
        }
      } catch (error) {
        console.error(`Error fetching dependent options for ${column.field}:`, error);
        showToast(`Failed to load options for ${column.header}`, 'error');
      } finally {
        setLoadingFields(prev => ({ ...prev, [column.field]: false }));
      }
    }
  };

  // Check if a field has dependents
  const hasDependendFields = (fieldName: string): boolean => {
    return resourceConfig.columns.some((column: any) => column.hasDependents && column.field === fieldName);
  };

  // Check if a field depends on another
  const isDependentField = (fieldName: string): boolean => {
    return resourceConfig.columns.some((column: any) => column.dependsOn && column.field === fieldName);
  };

  // Get the parent field for a dependent field
  const getParentField = (fieldName: string): string | null => {
    const column = resourceConfig.columns.find((col: any) => col.field === fieldName);
    return column?.dependsOn || null;
  };

  // Handle field change with dependency checking
  const handleFieldChangeWithDependencies = (fieldName: string, value: any) => {
    updateField(fieldName, value);
    
    // Check if this field has dependencies
    if (hasDependendFields(fieldName) && value) {
      fetchDependentOptions(fieldName, value);
    }
  };

  return {
    // State
    dynamicOptions,
    loadingFields,
    
    // Actions
    fetchDependentOptions,
    handleFieldChangeWithDependencies,
    
    // Helpers
    hasDependendFields,
    isDependentField,
    getParentField
  };
};