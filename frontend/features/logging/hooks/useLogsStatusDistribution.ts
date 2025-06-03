// frontend/features/logging/hooks/useLogsStatusDistribution.ts
import { useState, useEffect } from 'react';
import { loggingApi } from '@/services/api';
import type { StatusDistribution } from '@/types/logging';

interface UseLogsStatusDistributionProps {
  timeRange: string;
}

export const useLogsStatusDistribution = ({ timeRange }: UseLogsStatusDistributionProps) => {
  const [statusDistribution, setStatusDistribution] = useState<StatusDistribution[]>([]);
  const [selectedStatusCategory, setSelectedStatusCategory] = useState<string | null>(null);
  const [loadingDistribution, setLoadingDistribution] = useState<boolean>(false);

  // Load status distribution when time range changes
  useEffect(() => {
    loadStatusDistribution();
  }, [timeRange]);

  const loadStatusDistribution = async () => {
    setLoadingDistribution(true);
    try {
      const response = await loggingApi.getStatusDistribution(timeRange);
      if (response.data && response.data.status_distribution) {
        setStatusDistribution(response.data.status_distribution);
      } else {
        console.error('Invalid response format:', response.data);
        setStatusDistribution([]);
      }
    } catch (error) {
      console.error('Error loading status distribution:', error);
      setStatusDistribution([]);
    } finally {
      setLoadingDistribution(false);
    }
  };

  const handleStatusCategoryClick = (statusCategory: string) => {
    if (selectedStatusCategory === statusCategory) {
      // If clicking the already selected category, clear the filter
      setSelectedStatusCategory(null);
    } else {
      setSelectedStatusCategory(statusCategory);
    }
  };

  const clearStatusFilter = () => {
    setSelectedStatusCategory(null);
  };

  return {
    // State
    statusDistribution,
    selectedStatusCategory,
    loadingDistribution,
    
    // Actions
    loadStatusDistribution,
    handleStatusCategoryClick,
    clearStatusFilter,
    setSelectedStatusCategory
  };
};