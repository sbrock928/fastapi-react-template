import { useState, useEffect } from 'react';
import { useToast } from '@/context/ToastContext';
import { calculationsApi } from '@/services/calculationsApi';
import type { UserCalculation } from '@/types/calculations';

export const useUserCalculations = () => {
  const { showToast } = useToast();
  const [userCalculations, setUserCalculations] = useState<UserCalculation[]>([]);
  const [filteredUserCalculations, setFilteredUserCalculations] = useState<UserCalculation[]>([]);
  const [selectedFilter, setSelectedFilter] = useState<string>('all');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const fetchUserCalculations = async (): Promise<void> => {
    setIsLoading(true);
    try {
      // Use the unified endpoint and extract user calculations
      const response = await calculationsApi.getAllCalculations();
      setUserCalculations(response.data.user_calculations);
      setFilteredUserCalculations(response.data.user_calculations); // Also update filtered calculations
    } catch (error) {
      console.error('Error fetching user calculations:', error);
      showToast('Error loading user calculations. Please refresh the page.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // Filter calculations based on selected filter
  const filterCalculations = (): void => {
    let filtered = userCalculations;
    
    if (selectedFilter === 'deal') {
      filtered = userCalculations.filter(calc => calc.group_level === 'deal');
    } else if (selectedFilter === 'tranche') {
      filtered = userCalculations.filter(calc => calc.group_level === 'tranche');
    }
    
    setFilteredUserCalculations(filtered);
  };

  useEffect(() => {
    fetchUserCalculations();
  }, []);

  useEffect(() => {
    filterCalculations();
  }, [userCalculations, selectedFilter]);

  return {
    userCalculations,
    filteredUserCalculations,
    selectedFilter,
    isLoading,
    setSelectedFilter,
    fetchUserCalculations,
  };
};