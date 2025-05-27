import axios from 'axios';

// Create axios instance with common configuration
const apiClient = axios.create({
  baseURL: '',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for smart API path handling that works in all environments
apiClient.interceptors.request.use(
  (config) => {
    // Skip external URLs
    if (config.url && config.url.startsWith('http')) {
      return config;
    }

    // Handle API prefixing consistently across environments
    if (config.url) {
      // First, normalize the path by removing any existing /api prefix
      let url = config.url;
      while (url.startsWith('/api/')) {
        url = url.substring(4); // Remove /api/
      }
      
      // Ensure the path starts with a slash
      if (!url.startsWith('/')) {
        url = '/' + url;
      }
      
      // In all environments, we want a single /api prefix
      config.url = '/api' + url;
    }
    
    return config;
  },
  (error) => Promise.reject(error)
);

// Add response interceptor for global error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response || error);
    return Promise.reject(error);
  }
);

export default apiClient;