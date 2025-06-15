import { useState, useEffect, useCallback } from 'react';
import type { 
  ReportConfig, 
  ReportCalculation, 
  ReportColumnPreferences,
  ReportScope
} from '@/types/reporting';
import { ColumnFormat, getDefaultColumnPreferences } from '@/types/reporting';

interface UseReportBuilderFormProps {
  editingReport?: ReportConfig | null;
  isEditMode: boolean;
}

export const useReportBuilderForm = ({ editingReport, isEditMode }: UseReportBuilderFormProps) => {
  const [reportName, setReportName] = useState<string>('');
  const [reportDescription, setReportDescription] = useState<string>('');
  const [reportScope, setReportScope] = useState<ReportScope | ''>('');
  const [selectedDeals, setSelectedDeals] = useState<number[]>([]);
  const [selectedTranches, setSelectedTranches] = useState<Record<number, string[]>>({});
  const [selectedCalculations, setSelectedCalculations] = useState<ReportCalculation[]>([]);
  const [columnPreferences, setColumnPreferences] = useState<ReportColumnPreferences | undefined>();

  // Auto-generate column preferences when calculations or scope change
  const updateColumnPreferencesFromCalculations = useCallback((
    calculations: ReportCalculation[], 
    scope: ReportScope | '',
    preserveExisting: boolean = false
  ) => {
    if (calculations.length > 0 && scope && (scope === 'DEAL' || scope === 'TRANCHE')) {
      if (!preserveExisting || !columnPreferences) {
        const defaultPrefs = getDefaultColumnPreferences(calculations, scope as ReportScope, true);
        setColumnPreferences(defaultPrefs);
      } else {
        // Get current calculation IDs
        const currentCalculationIds = new Set(calculations.map(calc => calc.calculation_id));
        
        // Filter existing columns to only keep:
        // 1. Default columns (deal_number, tranche_id, cycle_code)
        // 2. Columns for calculations that are still selected
        const defaultColumnIds = ['deal_number', 'tranche_id', 'cycle_code'];
        const validExistingColumns = columnPreferences.columns.filter(col => 
          defaultColumnIds.includes(col.column_id) || currentCalculationIds.has(col.column_id)
        );
        
        // Find new calculations that need columns added
        const existingColumnIds = new Set(validExistingColumns.map(col => col.column_id));
        const newCalculations = calculations.filter(calc => 
          !existingColumnIds.has(calc.calculation_id)
        );
        
        // Add columns for new calculations
        const newColumns = newCalculations.map((calc, index) => ({
          column_id: calc.calculation_id,
          display_name: calc.display_name || `Calculation ${calc.calculation_id}`,
          is_visible: true,
          display_order: validExistingColumns.length + index,
          format_type: ColumnFormat.TEXT
        }));
        
        // Update display orders to be sequential
        const allColumns = [...validExistingColumns, ...newColumns];
        allColumns.forEach((col, index) => {
          col.display_order = index;
        });
        
        setColumnPreferences({
          ...columnPreferences,
          columns: allColumns
        });
      }
    } else if (calculations.length === 0 && scope && columnPreferences) {
      // If no calculations selected, only keep default columns
      const defaultColumnIds = ['deal_number', 'tranche_id', 'cycle_code'];
      const defaultColumns = columnPreferences.columns.filter(col => 
        defaultColumnIds.includes(col.column_id)
      );
      
      // Update display orders
      defaultColumns.forEach((col, index) => {
        col.display_order = index;
      });
      
      setColumnPreferences({
        ...columnPreferences,
        columns: defaultColumns
      });
    }
  }, [columnPreferences, setColumnPreferences]);

  // Update column preferences when calculations change
  useEffect(() => {
    // Always update column preferences when calculations change, regardless of edit mode
    updateColumnPreferencesFromCalculations(selectedCalculations, reportScope, true);
  }, [selectedCalculations, reportScope, updateColumnPreferencesFromCalculations]);

  // Initialize form when editing
  useEffect(() => {
    if (isEditMode && editingReport) {
      setReportName(editingReport.name || '');
      setReportDescription(editingReport.description || '');
      setReportScope(editingReport.scope || '');
      
      // Set selected deals
      const dealNumbers = editingReport.selected_deals?.map(deal => deal.dl_nbr) || [];
      setSelectedDeals(dealNumbers);
      
      // Set selected tranches
      const trancheMap: Record<number, string[]> = {};
      editingReport.selected_deals?.forEach(deal => {
        if (deal.selected_tranches) {
          trancheMap[deal.dl_nbr] = deal.selected_tranches.map(t => t.tr_id);
        }
      });
      setSelectedTranches(trancheMap);
      
      // Set selected calculations
      setSelectedCalculations(editingReport.selected_calculations || []);
      
      // Set column preferences or generate defaults
      if (editingReport.column_preferences) {
        setColumnPreferences(editingReport.column_preferences);
      } else if (editingReport.selected_calculations && editingReport.scope) {
        // Generate default preferences for existing report without column preferences
        const defaultPrefs = getDefaultColumnPreferences(
          editingReport.selected_calculations, 
          editingReport.scope, 
          true
        );
        setColumnPreferences(defaultPrefs);
      }
    }
  }, [isEditMode, editingReport]);

  const resetForm = () => {
    setReportName('');
    setReportDescription('');
    setReportScope('');
    setSelectedDeals([]);
    setSelectedTranches({});
    setSelectedCalculations([]);
    setColumnPreferences(undefined);
  };

  return {
    reportName,
    reportDescription,
    reportScope,
    selectedDeals,
    selectedTranches,
    selectedCalculations,
    columnPreferences,
    setReportName,
    setReportDescription,
    setReportScope,
    setSelectedDeals,
    setSelectedTranches,
    setSelectedCalculations,
    setColumnPreferences,
    resetForm
  };
};