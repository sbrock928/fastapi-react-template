// frontend/features/calculations/constants/calculationConstants.ts
// Updated constants for the enhanced calculation system

import type { CalculationForm } from '@/types/calculations';

// Form initialization - updated for user-defined calculations
export const INITIAL_CALCULATION_FORM: CalculationForm = {
  name: '',
  function_type: 'SUM', // Default to SUM for user-defined calculations
  source: '',
  source_field: '',
  level: 'deal',
  weight_field: '',
  description: ''
};

// System field calculation form
export const INITIAL_SYSTEM_FIELD_FORM: CalculationForm = {
  name: '',
  function_type: 'SYSTEM_FIELD',
  source: '',
  source_field: '',
  level: 'deal',
  weight_field: '', // Will store field_type
  description: ''
};

// System SQL calculation form
export const INITIAL_SYSTEM_SQL_FORM: CalculationForm = {
  name: '',
  function_type: 'SYSTEM_SQL',
  source: '', // Not used for SQL calculations
  source_field: '', // Will store the SQL text
  level: 'deal',
  weight_field: '', // Will store result_column_name
  description: ''
};

// Preview parameters for SQL generation
export const SAMPLE_PREVIEW_PARAMS = {
  aggregation_level: 'deal',
  sample_deals: '101,102,103',
  sample_tranches: 'A,B',
  sample_cycle: '202404'
};

// Filter options for the UI - enhanced for system calculations
export const FILTER_OPTIONS = [
  { value: 'all', label: 'All' },
  { value: 'deal', label: 'Deal Level' },
  { value: 'tranche', label: 'Tranche Level' }
];

// Enhanced filter options for system calculations tab
export const SYSTEM_FILTER_OPTIONS = [
  { value: 'all', label: 'All System Calculations' },
  { value: 'deal', label: 'Deal Level' },
  { value: 'tranche', label: 'Tranche Level' },
  { value: 'system-field', label: 'Field Calculations Only' },
  { value: 'system-sql', label: 'SQL Calculations Only' }
];

// Calculation type options for UI
export const CALCULATION_TYPE_OPTIONS = [
  {
    value: 'user-defined',
    label: 'User Defined',
    description: 'Create aggregated calculations (SUM, AVG, COUNT, etc.)',
    icon: 'bi-person-gear',
    color: 'primary'
  },
  {
    value: 'system-field',
    label: 'System Field',
    description: 'Expose raw model fields for reports',
    icon: 'bi-database',
    color: 'success'
  },
  {
    value: 'system-sql',
    label: 'System SQL',
    description: 'Advanced custom calculations using SQL',
    icon: 'bi-code-square',
    color: 'warning'
  }
];

// SQL templates for different group levels
export const SQL_TEMPLATES = {
  deal: `-- Deal-level calculation template
SELECT 
    deal.dl_nbr,
    CASE 
        WHEN deal.issr_cde LIKE '%FHLMC%' THEN 'GSE'
        WHEN deal.issr_cde LIKE '%GNMA%' THEN 'Government'
        ELSE 'Private'
    END AS result_column
FROM deal
WHERE deal.dl_nbr IN (101, 102, 103)`,

  tranche: `-- Tranche-level calculation template
SELECT 
    deal.dl_nbr,
    tranche.tr_id,
    CASE 
        WHEN tranchebal.tr_end_bal_amt >= 25000000 THEN 'Large'
        WHEN tranchebal.tr_end_bal_amt >= 10000000 THEN 'Medium'
        ELSE 'Small'
    END AS result_column
FROM deal
JOIN tranche ON deal.dl_nbr = tranche.dl_nbr
JOIN tranchebal ON tranche.dl_nbr = tranchebal.dl_nbr 
    AND tranche.tr_id = tranchebal.tr_id
WHERE deal.dl_nbr IN (101, 102, 103)
    AND tranche.tr_id IN ('A', 'B')
    AND tranchebal.cycle_cde = 202404`
};

// Configuration loading messages
export const CONFIG_MESSAGES = {
  LOADING: 'Loading calculation configuration from server...',
  ERROR: 'Failed to load calculation configuration. Please check your connection and try again.',
  RETRY: 'Click "Retry" to reload the configuration from the server.',
  REQUIRED: 'Configuration must be loaded before creating calculations'
} as const;

// SQL validation messages
export const SQL_VALIDATION_MESSAGES = {
  REQUIRED_FIELDS_DEAL: 'SQL must include deal.dl_nbr in SELECT clause for deal-level calculations',
  REQUIRED_FIELDS_TRANCHE: 'SQL must include both deal.dl_nbr and tranche.tr_id in SELECT clause for tranche-level calculations',
  SELECT_REQUIRED: 'SQL must be a SELECT statement',
  FROM_REQUIRED: 'SQL must include a FROM clause',
  DANGEROUS_OPERATION: 'SQL contains dangerous operations (DROP, DELETE, UPDATE, etc.)',
  MULTIPLE_STATEMENTS: 'Only single SELECT statements are allowed',
  RESULT_COLUMN_REQUIRED: 'Result column name is required and must be a valid SQL identifier'
} as const;

// Common field types for system field calculations
export const FIELD_TYPES = [
  { value: 'string', label: 'Text/String', icon: 'bi-type' },
  { value: 'number', label: 'Number', icon: 'bi-123' },
  { value: 'currency', label: 'Currency/Amount', icon: 'bi-currency-dollar' },
  { value: 'percentage', label: 'Percentage/Rate', icon: 'bi-percent' },
  { value: 'date', label: 'Date', icon: 'bi-calendar' },
  { value: 'boolean', label: 'True/False', icon: 'bi-toggle-on' }
];

// Help text for different calculation types
export const HELP_TEXT = {
  USER_DEFINED: 'User-defined calculations aggregate data using functions like SUM, AVG, COUNT, etc. These are the traditional calculations you create for reporting.',
  SYSTEM_FIELD: 'System field calculations expose raw model fields (like deal.dl_nbr or tranche.tr_id) for use in reports and as building blocks for other calculations.',
  SYSTEM_SQL: 'System SQL calculations use custom SQL queries for advanced logic. The SQL is validated for security and must include proper join fields for the selected group level.'
};

// Examples for different calculation types
export const CALCULATION_EXAMPLES = {
  USER_DEFINED: [
    {
      name: 'Total Ending Balance',
      description: 'Sum of all tranche ending balance amounts',
      function_type: 'SUM',
      source: 'TrancheBal',
      source_field: 'tr_end_bal_amt',
      level: 'deal'
    },
    {
      name: 'Average Pass Through Rate',
      description: 'Weighted average pass through rate',
      function_type: 'WEIGHTED_AVG',
      source: 'TrancheBal',
      source_field: 'tr_pass_thru_rte',
      weight_field: 'tr_end_bal_amt',
      level: 'deal'
    }
  ],
  SYSTEM_FIELD: [
    {
      name: 'Deal Number',
      description: 'Unique deal identifier',
      source: 'Deal',
      source_field: 'dl_nbr',
      field_type: 'number',
      level: 'deal'
    },
    {
      name: 'Tranche ID',
      description: 'Tranche identifier within the deal',
      source: 'Tranche',
      source_field: 'tr_id',
      field_type: 'string',
      level: 'tranche'
    }
  ],
  SYSTEM_SQL: [
    {
      name: 'Issuer Type Classification',
      description: 'Categorizes deals by issuer type',
      level: 'deal',
      sql: SQL_TEMPLATES.deal,
      result_column: 'issuer_type'
    },
    {
      name: 'Tranche Size Category',
      description: 'Size categorization of tranches',
      level: 'tranche',
      sql: SQL_TEMPLATES.tranche,
      result_column: 'size_category'
    }
  ]
};