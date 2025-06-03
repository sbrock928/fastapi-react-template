// frontend/features/logging/hooks/useLogsFiltering.ts
import { useState } from 'react';

interface UseLogsFilteringProps {
  onOffsetChange: (offset: number) => void;
  onStatusCategoryChange: (category: string | null) => void;
}

export const useLogsFiltering = ({ 
  onOffsetChange, 
  onStatusCategoryChange 
}: UseLogsFilteringProps) => {
  const [timeRange, setTimeRange] = useState<string>('24');
  const [filterText, setFilterText] = useState<string>('');
  const [currentOffset, setCurrentOffset] = useState<number>(0);

  const handleTimeRangeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setTimeRange(e.target.value);
    resetPagination();
  };

  const handleFilterChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newFilterText = e.target.value;
    setFilterText(newFilterText);
    resetPagination();
  };

  const clearFilter = () => {
    setFilterText('');
    resetPagination();
  };

  const resetPagination = () => {
    setCurrentOffset(0);
    onOffsetChange(0);
  };

  const handleStatusCategoryClick = (statusCategory: string) => {
    resetPagination();
    onStatusCategoryChange(statusCategory);
  };

  const updateOffset = (newOffset: number) => {
    setCurrentOffset(newOffset);
    onOffsetChange(newOffset);
  };

  const handleRefresh = () => {
    resetPagination();
  };

  return {
    // State
    timeRange,
    filterText,
    currentOffset,
    
    // Actions
    setTimeRange,
    setFilterText,
    handleTimeRangeChange,
    handleFilterChange,
    clearFilter,
    resetPagination,
    handleStatusCategoryClick,
    updateOffset,
    handleRefresh
  };
};