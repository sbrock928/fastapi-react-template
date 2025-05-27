// This file re-exports APIs from feature-specific files
// It provides a centralized access point for API services while maintaining the feature-based architecture

import apiClient from './apiClient';
import resourcesApi from './resourcesApi';
import loggingApi from './loggingApi';
import documentationApi from './documentationApi';
import reportingApi from './reportingApi';

// Re-export the feature-specific APIs
export { 
  resourcesApi,
  loggingApi,
  documentationApi,
  reportingApi
};

// Export the base apiClient as the default export
export default apiClient;