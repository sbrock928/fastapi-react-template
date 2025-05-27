// This file re-exports APIs from feature-specific files
// It provides backward compatibility while supporting the feature-based architecture

import apiClient from './apiClient';
import resourcesApi from './resourcesApi';
import loggingApi from './loggingApi';
import documentationApi from './documentationApi';
import reportingApi from './reportingApi';

// Re-export the feature-specific APIs
export { 
  resourcesApi,
  loggingApi as logsApi, // Maintain backward compatibility with the old name
  documentationApi,
  reportingApi as reportsApi // Maintain backward compatibility with the old name
};

// Export the base apiClient as the default export
export default apiClient;