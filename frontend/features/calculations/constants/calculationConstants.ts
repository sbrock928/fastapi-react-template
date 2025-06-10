// frontend/features/calculations/constants/calculationConstants.ts
// Essential constants for calculation functionality (no API fallbacks)

import type { CalculationForm } from '@/types/calculations';

// Form initialization
export const INITIAL_CALCULATION_FORM: CalculationForm = {
  name: '',
  function_type: 'SUM',
  source: '',
  source_field: '',
  level: 'deal',
  weight_field: '',
  description: ''
};

// Preview parameters for SQL generation
export const SAMPLE_PREVIEW_PARAMS = {
  group_level: 'deal',
  sample_deals: '101,102,103',
  sample_tranches: 'A,B',
  sample_cycle: '202404'
};

// Filter options for the UI
export const FILTER_OPTIONS = [
  { value: 'all', label: 'All' },
  { value: 'deal', label: 'Deal Level' },
  { value: 'tranche', label: 'Tranche Level' }
];

// Configuration loading messages
export const CONFIG_MESSAGES = {
  LOADING: 'Loading calculation configuration from server...',
  ERROR: 'Failed to load calculation configuration. Please check your connection and try again.',
  RETRY: 'Click "Retry" to reload the configuration from the server.',
  REQUIRED: 'Configuration must be loaded before creating calculations'
} as const;