// frontend/features/logging/hooks/useLogsAutoRefresh.ts
import { useState, useEffect, useRef } from 'react';

interface UseLogsAutoRefreshProps {
  onRefresh: () => void;
}

export const useLogsAutoRefresh = ({ onRefresh }: UseLogsAutoRefreshProps) => {
  const [autoRefresh, setAutoRefresh] = useState<boolean>(false);
  const [refreshInterval, setRefreshInterval] = useState<number>(30); // seconds
  const refreshTimerId = useRef<number | null>(null);
  const onRefreshRef = useRef(onRefresh);

  // Keep the callback reference up to date
  useEffect(() => {
    onRefreshRef.current = onRefresh;
  }, [onRefresh]);

  // Auto-refresh functionality
  useEffect(() => {
    // Clear any existing timer first
    if (refreshTimerId.current) {
      window.clearInterval(refreshTimerId.current);
      refreshTimerId.current = null;
    }

    if (autoRefresh) {
      const timerId = window.setInterval(() => {
        console.log('Auto-refreshing logs...');
        onRefreshRef.current();
      }, refreshInterval * 1000);
      
      refreshTimerId.current = timerId;
      
      return () => {
        window.clearInterval(timerId);
      };
    }
  }, [autoRefresh, refreshInterval]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (refreshTimerId.current) {
        window.clearInterval(refreshTimerId.current);
      }
    };
  }, []);

  const handleAutoRefreshChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setAutoRefresh(e.target.checked);
  };

  const handleRefreshIntervalChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setRefreshInterval(parseInt(e.target.value));
  };

  return {
    // State
    autoRefresh,
    refreshInterval,
    
    // Actions
    setAutoRefresh,
    setRefreshInterval,
    handleAutoRefreshChange,
    handleRefreshIntervalChange
  };
};