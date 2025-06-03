// frontend/features/resources/hooks/useResourcesFiltering.ts
import { useState, useEffect, useMemo } from 'react';
import { resourceConfig } from '@/config';
import type { ResourceItem } from '@/types';

interface UseResourcesFilteringProps {
  items: ResourceItem[];
  activeResource: string;
}

export const useResourcesFiltering = ({ items, activeResource }: UseResourcesFilteringProps) => {
  const [filterText, setFilterText] = useState<string>('');
  const [filteredItems, setFilteredItems] = useState<ResourceItem[]>([]);

  // Get searchable columns for current resource
  const searchableColumns = useMemo(() => {
    if (!activeResource) return [];
    
    const config = resourceConfig[activeResource];
    return config.columns.filter((col: { type: string; searchable?: boolean }) => 
      col.type !== 'hidden' && col.type !== 'password'
    );
  }, [activeResource]);

  // Filter items when filter text or items change
  useEffect(() => {
    filterItems();
  }, [filterText, items, activeResource, searchableColumns]);

  // Filter items based on search input
  const filterItems = () => {
    if (!activeResource || !items.length) {
      setFilteredItems([]);
      return;
    }

    if (!filterText.trim()) {
      setFilteredItems(items);
      return;
    }

    const filtered = items.filter(item => {
      return searchableColumns.some((column: { field: string }) => {
        const value = item[column.field];
        if (value !== undefined && value !== null) {
          return String(value).toLowerCase().includes(filterText.toLowerCase());
        }
        return false;
      });
    });

    setFilteredItems(filtered);
  };

  // Clear filter
  const clearFilter = () => {
    setFilterText('');
  };

  // Get filter summary text
  const getFilterSummary = () => {
    if (!filterText) return '';
    
    const totalItems = items.length;
    const filteredCount = filteredItems.length;
    
    if (filteredCount === totalItems) {
      return '';
    }
    
    return `(filtered from ${totalItems} total)`;
  };

  // Check if filter is active
  const isFilterActive = () => {
    return filterText.trim().length > 0;
  };

  return {
    // State
    filterText,
    filteredItems,
    
    // Actions
    setFilterText,
    clearFilter,
    
    // Helpers
    getFilterSummary,
    isFilterActive,
    searchableColumns
  };
};