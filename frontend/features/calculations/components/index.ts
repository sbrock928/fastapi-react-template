// frontend/features/calculations/components/index.ts
// Export all calculation components - updated for system calculations

export { default as CalculationCard } from './CalculationCard';
export { default as CalculationModal } from './CalculationModal';
export { default as FilterSection } from './FilterSection';
export { default as SqlPreviewModal } from './SqlPreviewModal';
export { default as UsageModal } from './UsageModal';

// New system calculation components
export { default as SystemCalculationsTab } from './SystemCalculationsTab';
export { default as SqlEditor } from './SqlEditor';

// Type definitions for component props
export interface CalculationCardProps {
  calculation: any;
  usage: any;
  onEdit: (calc: any) => void;
  onDelete: (id: number, name: string) => void;
  onPreviewSQL: (id: number) => void;
  onShowUsage: (id: number, name: string) => void;
}

export interface CalculationModalProps {
  isOpen: boolean;
  modalType: 'user-defined' | 'system-field' | 'system-sql';
  editingCalculation: any;
  calculation: any;
  error: string | null;
  isSaving: boolean;
  fieldsLoading: boolean;
  allAvailableFields: any;
  aggregationFunctions: any[];
  sourceModels: any[];
  groupLevels: any[];
  onClose: () => void;
  onSave: () => void;
  onUpdateCalculation: (updates: any) => void;
  hasUnsavedChanges: boolean;
}