import { useState, useEffect, useRef, useCallback } from 'react';

// Generic hook for managing API requests with built-in spam protection
export const useApiRequest = <T>(
  apiCall: () => Promise<{ data: T }>,
  dependencies: any[] = [],
  options: {
    immediate?: boolean;
    throttleMs?: number;
    maxRetries?: number;
    retryDelayMs?: number;
  } = {}
) => {
  const {
    immediate = true,
    throttleMs = 1000,
    maxRetries = 3,
    retryDelayMs = 1000
  } = options;

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState<number>(0);
  
  const lastRequestTime = useRef<number>(0);
  const isRequestInProgress = useRef<boolean>(false);
  const retryTimeoutRef = useRef<NodeJS.Timeout>();

  const makeRequest = useCallback(async (isRetry = false) => {
    // Prevent multiple simultaneous requests
    if (isRequestInProgress.current && !isRetry) {
      console.warn('Request already in progress, skipping...');
      return;
    }

    // Throttle requests
    const now = Date.now();
    if (!isRetry && (now - lastRequestTime.current) < throttleMs) {
      console.warn(`Request throttled, waiting ${throttleMs}ms between requests`);
      return;
    }

    isRequestInProgress.current = true;
    lastRequestTime.current = now;
    setLoading(true);
    setError(null);

    try {
      const response = await apiCall();
      setData(response.data);
      setRetryCount(0); // Reset retry count on success
    } catch (err: any) {
      console.error('API request failed:', err);
      const errorMessage = err.response?.data?.detail || err.message || 'Request failed';
      setError(errorMessage);
      
      // Implement exponential backoff retry
      if (retryCount < maxRetries) {
        const delay = retryDelayMs * Math.pow(2, retryCount);
        console.log(`Retrying in ${delay}ms... (attempt ${retryCount + 1}/${maxRetries})`);
        
        retryTimeoutRef.current = setTimeout(() => {
          setRetryCount(prev => prev + 1);
          makeRequest(true);
        }, delay);
      }
    } finally {
      setLoading(false);
      isRequestInProgress.current = false;
    }
  }, [apiCall, throttleMs, maxRetries, retryDelayMs, retryCount]);

  const refetch = useCallback(() => {
    setRetryCount(0);
    makeRequest();
  }, [makeRequest]);

  // Effect to trigger initial request
  useEffect(() => {
    if (immediate) {
      makeRequest();
    }
    
    // Cleanup retry timeout on unmount
    return () => {
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
    };
  }, dependencies); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    data,
    loading,
    error,
    refetch,
    retryCount
  };
};