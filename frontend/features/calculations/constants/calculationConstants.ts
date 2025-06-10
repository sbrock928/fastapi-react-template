import type { CalculationField, AggregationFunction, SourceModel, GroupLevel } from '@/types/calculations';

// Fallback configuration if API fails
export const DEFAULT_FIELD_MAPPINGS: Record<string, CalculationField[]> = {
  'Deal': [
    { value: 'dl_nbr', label: 'Deal Number', type: 'number' }
  ],
  'Tranche': [
    { value: 'tr_id', label: 'Tranche ID', type: 'string' },
    { value: 'dl_nbr', label: 'Deal Number', type: 'number' }
  ],
  'TrancheBal': [
    { value: 'tr_end_bal_amt', label: 'Ending Balance Amount', type: 'currency' },
    { value: 'tr_pass_thru_rte', label: 'Pass Through Rate', type: 'percentage' },
    { value: 'tr_accrl_days', label: 'Accrual Days', type: 'number' },
    { value: 'tr_int_dstrb_amt', label: 'Interest Distribution Amount', type: 'currency' },
    { value: 'tr_prin_dstrb_amt', label: 'Principal Distribution Amount', type: 'currency' },
    { value: 'tr_int_accrl_amt', label: 'Interest Accrual Amount', type: 'currency' },
    { value: 'tr_int_shtfl_amt', label: 'Interest Shortfall Amount', type: 'currency' },
    { value: 'cycle_cde', label: 'Cycle Code', type: 'number' }
  ]
};

export const DEFAULT_AGGREGATION_FUNCTIONS: AggregationFunction[] = [
  { value: 'SUM', label: 'SUM - Total amount', description: 'Add all values together', category: 'aggregated' },
  { value: 'AVG', label: 'AVG - Average', description: 'Calculate average value', category: 'aggregated' },
  { value: 'COUNT', label: 'COUNT - Count records', description: 'Count number of records', category: 'aggregated' },
  { value: 'MIN', label: 'MIN - Minimum value', description: 'Find minimum value', category: 'aggregated' },
  { value: 'MAX', label: 'MAX - Maximum value', description: 'Find maximum value', category: 'aggregated' },
  { value: 'WEIGHTED_AVG', label: 'WEIGHTED_AVG - Weighted average', description: 'Calculate weighted average using specified weight field', category: 'aggregated' },
];

export const DEFAULT_SOURCE_MODELS: SourceModel[] = [
  { value: 'Deal', label: 'Deal', description: 'Base deal information' },
  { value: 'Tranche', label: 'Tranche', description: 'Tranche structure data' },
  { value: 'TrancheBal', label: 'TrancheBal', description: 'Tranche balance and performance data' }
];

export const DEFAULT_GROUP_LEVELS: GroupLevel[] = [
  { value: 'deal', label: 'Deal Level', description: 'Aggregate to deal level' },
  { value: 'tranche', label: 'Tranche Level', description: 'Aggregate to tranche level' }
];

export const INITIAL_CALCULATION_FORM = {
  name: '',
  function_type: 'SUM',
  source: '',
  source_field: '',
  level: 'deal',
  weight_field: '',
  description: ''
};

export const SAMPLE_PREVIEW_PARAMS = {
  group_level: 'deal',
  sample_deals: '101,102,103',
  sample_tranches: 'A,B',
  sample_cycle: '202404'
};

export const FILTER_OPTIONS = [
  { value: 'all', label: 'All' },
  { value: 'deal', label: 'Deal Level' },
  { value: 'tranche', label: 'Tranche Level' }
];