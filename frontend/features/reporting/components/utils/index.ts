export { 
  transformFormDataForApi, 
  convertAvailableCalculationsToReportCalculations, 
  findAvailableCalculationByReportCalculation, 
  parseCalculationIdLocal, 
  formatCalculationIdForDisplay, 
  validateCalculationCompatibility, 
  filterCalculationsByCompatibility, 
  updateColumnPreferencesWithNewCalculations, 
  generateFormattedPreview, 
  createReportConfigPayload, 
  createUpdateReportPayload, 
  parseApiError, 
  validateReportBeforeSave, 
  getSuccessMessage 
} from './reportBusinessLogic';

// Types that might be needed for external consumption
export type { 
  ColumnPreference, 
  ColumnFormat, 
  ReportColumnPreferences 
} from '@/types/reporting';