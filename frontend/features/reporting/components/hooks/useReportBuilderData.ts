// frontend/features/reporting/components/hooks/useReportBuilderData.ts
// Updated to work with the new separated calculation system

import { useState, useEffect } from 'react';
import { reportingApi } from '@/services/api';
import { calculationsApi } from '@/services/calculationsApi';
import { useToast } from '@/context/ToastContext';
import { useReportContext } from '@/context/ReportContext';
import type { TrancheReportSummary, AvailableCalculation } from '@/types/reporting';

interface UseReportBuilderDataProps {
  reportScope: 'DEAL' | 'TRANCHE' | '';
  selectedDeals: number[];
  isEditMode: boolean;
}

export const useReportBuilderData = ({ reportScope, selectedDeals, isEditMode }: UseReportBuilderDataProps) => {
  const { showToast } = useToast();
  const { deals, dealsLoading, loadDealsOnce } = useReportContext();
  
  // Data state (removed deals state since it comes from context)
  const [tranches, setTranches] = useState<Record<string, TrancheReportSummary[]>>({});
  const [availableCalculations, setAvailableCalculations] = useState<AvailableCalculation[]>([]);
  
  // Loading states (removed dealsLoading since it comes from context)
  const [tranchesLoading, setTranchesLoading] = useState<boolean>(false);
  const [calculationsLoading, setCalculationsLoading] = useState<boolean>(false);

  // Load deals once when hook initializes (only if not already loaded)
  useEffect(() => {
    loadDealsOnce();
  }, [loadDealsOnce]);

  // Load available calculations when scope changes
  useEffect(() => {
    if (reportScope === 'DEAL' || reportScope === 'TRANCHE') {
      loadAvailableCalculations(reportScope);
    }
  }, [reportScope, isEditMode]);

  // Load tranches when deals are selected for both DEAL and TRANCHE scope
  useEffect(() => {
    const loadTranches = async () => {
      if (selectedDeals.length > 0 && (reportScope === 'TRANCHE' || reportScope === 'DEAL')) {
        setTranchesLoading(true);
        try {
          const response = await reportingApi.getTranches(selectedDeals);
          setTranches(response.data);
        } catch (error) {
          console.error('Error loading tranches:', error);
          showToast('Error loading tranches', 'error');
        } finally {
          setTranchesLoading(false);
        }
      }
    };

    loadTranches();
  }, [selectedDeals, reportScope, showToast]);

  // Load available calculations based on scope using the new API
  const loadAvailableCalculations = async (scope: 'DEAL' | 'TRANCHE') => {
    setCalculationsLoading(true);
    try {
      // Use the new compatibility method that combines all calculation types
      const response = await calculationsApi.getAvailableCalculations(scope);
      setAvailableCalculations(response.data);
    } catch (error) {
      console.error('Error loading available calculations:', error);
      showToast('Error loading available calculations', 'error');
      
      // Fallback: try to load individual calculation types
      try {
        const [userCalcs, systemCalcs, staticFields] = await Promise.all([
          calculationsApi.getUserDefinedCalculations(scope.toLowerCase()),
          calculationsApi.getSystemCalculations(scope.toLowerCase(), true),
          calculationsApi.getStaticFields()
        ]);

        // Combine the results manually
        const combined: AvailableCalculation[] = [];

        // Add user calculations
        userCalcs.data.forEach(calc => {
          combined.push({
            id: calc.id,
            name: calc.name,
            description: calc.description,
            aggregation_function: calc.aggregation_function,
            source_model: calc.source_model,
            source_field: calc.source_field,
            group_level: calc.group_level,
            weight_field: calc.weight_field,
            scope: scope,
            category: categorizeUserCalculation(calc),
            is_default: isDefaultCalculation(calc.name),
            calculation_type: 'USER_DEFINED'
          });
        });

        // Add approved system calculations
        systemCalcs.data.forEach(calc => {
          if (calc.approved_by) {
            combined.push({
              id: calc.id,
              name: calc.name,
              description: calc.description,
              aggregation_function: undefined,
              source_model: undefined,
              source_field: undefined,
              group_level: calc.group_level,
              weight_field: undefined,
              scope: scope,
              category: 'Custom SQL Calculations',
              is_default: false,
              calculation_type: 'SYSTEM_SQL'
            });
          }
        });

        // Add compatible static fields
        staticFields.data.forEach(field => {
          const fieldGroupLevel = field.field_path.startsWith('tranche.') || field.field_path.startsWith('tranchebal.') ? 'tranche' : 'deal';
          const isCompatible = scope === 'TRANCHE' || fieldGroupLevel === 'deal';
          
          if (isCompatible) {
            combined.push({
              id: `static_${field.field_path}`,
              name: field.name,
              description: field.description,
              aggregation_function: 'RAW',
              source_model: undefined,
              source_field: field.field_path,
              group_level: fieldGroupLevel,
              weight_field: undefined,
              scope: scope,
              category: categorizeStaticField(field),
              is_default: isDefaultField(field.name),
              calculation_type: 'STATIC_FIELD'
            });
          }
        });

        setAvailableCalculations(combined);
      } catch (fallbackError) {
        console.error('Fallback calculation loading also failed:', fallbackError);
        showToast('Unable to load calculations. Please refresh the page.', 'error');
      }
    } finally {
      setCalculationsLoading(false);
    }
  };

  return {
    // Data (deals now comes from context)
    deals,
    tranches,
    availableCalculations,
    
    // Loading states (dealsLoading now comes from context)
    dealsLoading,
    tranchesLoading,
    calculationsLoading,
    
    // Functions (removed loadDeals since it's handled by context)
    loadAvailableCalculations
  };
};

// Helper functions for categorizing calculations
function categorizeUserCalculation(calc: any): string {
  const sourceModel = calc.source_model;
  const sourceField = calc.source_field || "";

  if (sourceModel === "Deal") {
    return "Deal Information";
  } else if (sourceModel === "Tranche") {
    return "Tranche Structure";
  } else if (sourceModel === "TrancheBal") {
    if ("bal" in sourceField.toLowerCase() || "amt" in sourceField.toLowerCase()) {
      return "Balance & Amount Calculations";
    } else if ("rte" in sourceField.toLowerCase()) {
      return "Rate Calculations";
    } else if ("dstrb" in sourceField.toLowerCase()) {
      return "Distribution Calculations";
    } else {
      return "Performance Calculations";
    }
  }
  return "Other";
}

function categorizeStaticField(field: any): string {
  if (field.field_path.startsWith("deal.")) {
    return "Deal Information";
  } else if (field.field_path.startsWith("tranche.")) {
    return "Tranche Structure";
  } else if (field.field_path.startsWith("tranchebal.")) {
    return "Balance & Performance Data";
  }
  return "Other";
}

function isDefaultCalculation(name: string): boolean {
  return ["Total Ending Balance", "Average Pass Through Rate"].includes(name);
}

function isDefaultField(name: string): boolean {
  return ["Deal Number", "Tranche ID"].includes(name);
}