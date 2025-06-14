import axios from 'axios';

// Request throttling map to prevent spam
const requestThrottleMap = new Map<string, number>();
const THROTTLE_DELAY = 200; // Increased to 200ms to better handle StrictMode double-renders

// Create axios instance with common configuration
const apiClient = axios.create({
  baseURL: '',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
});

// Add request interceptor for smart API path handling and throttling
apiClient.interceptors.request.use(
  (config) => {
    // Skip external URLs
    if (config.url && config.url.startsWith('http')) {
      return config;
    }

    // Create a throttle key for this request
    const throttleKey = `${config.method?.toUpperCase()}_${config.url}_${JSON.stringify(config.params || {})}`;
    const now = Date.now();
    const lastRequest = requestThrottleMap.get(throttleKey);
    
    // Throttle identical requests - but handle it more gracefully
    if (lastRequest && (now - lastRequest) < THROTTLE_DELAY) {
      // In development mode (React.StrictMode), don't log warnings for throttled requests
      // as they're expected due to double-rendering
      if (process.env.NODE_ENV === 'development') {
        // Silently throttle by returning a resolved promise with empty data
        // This prevents error messages while still preventing spam
        return Promise.resolve({
          ...config,
          adapter: () => Promise.resolve({
            data: { data: [] }, // Return empty data structure
            status: 200,
            statusText: 'OK (Throttled)',
            headers: {},
            config
          })
        });
      } else {
        console.warn(`Throttling duplicate request: ${throttleKey}`);
        return Promise.reject(new Error('Request throttled - too many identical requests'));
      }
    }
    
    requestThrottleMap.set(throttleKey, now);

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
    // Only log actual API errors, not throttling
    if (!error.message?.includes('Request throttled')) {
      console.error('API Error:', error.response || error);
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;