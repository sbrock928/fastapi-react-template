// This file re-exports APIs from feature-specific files
// It provides a centralized access point for API services while maintaining the feature-based architecture

import apiClient from './apiClient';
import loggingApi from './loggingApi';
import documentationApi from './documentationApi';
import reportingApi from './reportingApi';
import { calculationsApi } from './calculationsApi';

// Re-export the feature-specific APIs
export { 
  loggingApi,
  documentationApi,
  reportingApi,
  calculationsApi
};

// Export the base apiClient as the default export
export default apiClient;