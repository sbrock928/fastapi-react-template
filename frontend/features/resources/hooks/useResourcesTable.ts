// frontend/features/resources/hooks/useResourcesTable.ts
import { useMemo } from 'react';
import type { ResourceItem } from '@/types';

interface UseResourcesTableProps {
  filteredItems: ResourceItem[];
  isLoading: boolean;
  filterText: string;
}

export const useResourcesTable = ({ 
  filteredItems, 
  isLoading, 
  filterText 
}: UseResourcesTableProps) => {
  
  // Format cell content based on column type
  const formatCellContent = (item: ResourceItem, column: any) => {
    let cellContent = item[column.field];
    
    // Format cell content based on type
    if (column.type === 'checkbox') {
      cellContent = cellContent ? '✅' : '❌';
    } else if (column.type === 'select' && column.options) {
      const option = column.options.find((opt: {value: string | number; text: string}) => opt.value === cellContent);
      cellContent = option ? option.text : cellContent;
    }
    
    return cellContent !== undefined && cellContent !== null
      ? String(cellContent)
      : '-';
  };

  // Check if table should show empty state
  const showEmptyState = useMemo(() => {
    return !isLoading && filteredItems.length === 0;
  }, [isLoading, filteredItems.length]);

  // Get empty state message
  const getEmptyStateMessage = () => {
    if (filterText) {
      return 'No resources match your search criteria.';
    }
    return 'No resources available. Click "Add New" to create one.';
  };

  // Check if table should show loading state
  const showLoadingState = useMemo(() => {
    return isLoading;
  }, [isLoading]);

  // Check if table should show data
  const showTableData = useMemo(() => {
    return !isLoading && filteredItems.length > 0;
  }, [isLoading, filteredItems.length]);

  return {
    // Formatting helpers
    formatCellContent,
    
    // State checkers
    showEmptyState,
    showLoadingState,
    showTableData,
    
    // Content helpers
    getEmptyStateMessage
  };
};