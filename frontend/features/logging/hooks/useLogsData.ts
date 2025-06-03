// frontend/features/logging/hooks/useLogsData.ts
import { useState, useEffect } from 'react';
import { loggingApi } from '@/services/api';
import { getUrlParamAsInt } from '@/utils';
import type { Log } from '@/types/logging';

interface UseLogsDataProps {
  timeRange: string;
  currentOffset: number;
  selectedStatusCategory: string | null;
  filterText: string;
}

export const useLogsData = ({ 
  timeRange, 
  currentOffset, 
  selectedStatusCategory, 
  filterText 
}: UseLogsDataProps) => {
  const [filteredLogs, setFilteredLogs] = useState<Log[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [serverFilterActive, setServerFilterActive] = useState<boolean>(false);
  
  const limit = 50;

  // Load logs when dependencies change
  useEffect(() => {
    loadLogs();
  }, [timeRange, currentOffset, selectedStatusCategory, filterText]);

  const loadLogs = async () => {
    setIsLoading(true);
    try {
      // Build the URL with status filter if present
      const params: Record<string, string | number> = {
        limit,
        offset: currentOffset,
        hours: timeRange
      };
      
      // Add status code filter based on selected category
      if (selectedStatusCategory) {
        if (selectedStatusCategory === "Success") {
          params.status_min = 200;
          params.status_max = 299;
        } else if (selectedStatusCategory === "Redirection") {
          params.status_min = 300;
          params.status_max = 399;
        } else if (selectedStatusCategory === "Client Error") {
          params.status_min = 400;
          params.status_max = 499;
        } else if (selectedStatusCategory === "Server Error") {
          params.status_min = 500;
          params.status_max = 599;
        }
      }
      
      // Add text filter parameter if filterText is present
      if (filterText.trim()) {
        params.search = filterText.trim();
        setServerFilterActive(true);
      } else {
        setServerFilterActive(false);
      }
      
      const response = await loggingApi.getLogs(params);
      
      // Get total count from headers or response data
      const totalCount = getUrlParamAsInt('x-total-count', 0) || parseInt(response.headers['x-total-count'] || '0');
      if (totalCount > 0) {
        setTotalCount(totalCount);
      }
      
      // Assign status category to each log
      const logsWithCategory = response.data.map((log: Log) => {
        const status = log.status_code;
        let statusCategory: string;
        
        if (status >= 500) statusCategory = "Server Error";
        else if (status >= 400) statusCategory = "Client Error";
        else if (status >= 300) statusCategory = "Redirection";
        else if (status >= 200) statusCategory = "Success";
        else statusCategory = "Unknown";
        
        return {...log, status_category: statusCategory};
      });
      
      setFilteredLogs(logsWithCategory);
    } catch (error) {
      console.error('Error loading logs:', error);
      setFilteredLogs([]);
    } finally {
      setIsLoading(false);
    }
  };

  const refreshLogs = () => {
    loadLogs();
  };

  return {
    // State
    filteredLogs,
    isLoading,
    totalCount,
    serverFilterActive,
    limit,
    
    // Actions
    loadLogs,
    refreshLogs
  };
};