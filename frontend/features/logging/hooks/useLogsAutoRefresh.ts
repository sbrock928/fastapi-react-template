// frontend/features/logging/hooks/useLogsAutoRefresh.ts
import { useState, useEffect } from 'react';

interface UseLogsAutoRefreshProps {
  onRefresh: () => void;
}

export const useLogsAutoRefresh = ({ onRefresh }: UseLogsAutoRefreshProps) => {
  const [autoRefresh, setAutoRefresh] = useState<boolean>(false);
  const [refreshInterval, setRefreshInterval] = useState<number>(30); // seconds
  const [refreshTimerId, setRefreshTimerId] = useState<number | null>(null);

  // Auto-refresh functionality
  useEffect(() => {
    if (autoRefresh) {
      const timerId = window.setInterval(() => {
        console.log('Auto-refreshing logs...');
        onRefresh();
      }, refreshInterval * 1000);
      
      setRefreshTimerId(timerId as unknown as number);
      
      return () => {
        if (refreshTimerId) {
          window.clearInterval(refreshTimerId);
        }
      };
    } else if (refreshTimerId) {
      window.clearInterval(refreshTimerId);
      setRefreshTimerId(null);
    }
  }, [autoRefresh, refreshInterval, onRefresh]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (refreshTimerId) {
        window.clearInterval(refreshTimerId);
      }
    };
  }, [refreshTimerId]);

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