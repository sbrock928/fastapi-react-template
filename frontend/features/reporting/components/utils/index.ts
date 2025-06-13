export { 
  transformFormDataForApi, 
  validateColumnPreferences, 
  mergeColumnPreferences,
  generateFormattedPreview 
} from './reportBusinessLogic';

// Types that might be needed for external consumption
export type { 
  ColumnPreference, 
  ColumnFormat, 
  ReportColumnPreferences 
} from '@/types/reporting';