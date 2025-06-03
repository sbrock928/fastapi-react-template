// frontend/features/resources/hooks/useResourcesData.ts
import { useState, useEffect } from 'react';
import { resourcesApi } from '@/services/api';
import { useToast } from '@/context';
import { resourceConfig } from '@/config';
import type { ResourceItem, ResourceConfig } from '@/types';

interface UseResourcesDataProps {
  activeResource: string;
}

export const useResourcesData = ({ activeResource }: UseResourcesDataProps) => {
  const [items, setItems] = useState<ResourceItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const { showToast } = useToast();

  // Load resources when resource type changes
  useEffect(() => {
    if (activeResource) {
      loadResources();
    } else {
      setItems([]);
    }
  }, [activeResource]);

  // Load resources from API
  const loadResources = async () => {
    if (!activeResource) return;

    setIsLoading(true);
    try {
      const config = resourceConfig[activeResource];
      const response = await resourcesApi.getAll(config.apiEndpoint);
      setItems(response.data);
    } catch (error) {
      console.error('Error loading resources:', error);
      showToast('Error loading resources', 'error');
      setItems([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Delete resource
  const deleteResource = async (item: ResourceItem): Promise<boolean> => {
    if (!activeResource) return false;
    
    const config = resourceConfig[activeResource];
    
    if (!confirm(`Are you sure you want to delete this ${config.displayName}?`)) {
      return false;
    }
    
    setIsLoading(true);
    
    try {
      const itemId = item[config.idField] || item.id;
      await resourcesApi.delete(config.apiEndpoint, itemId);
      
      // Show success toast notification
      showToast(`Successfully deleted ${config.displayName}`, 'success');
      
      // Reload resources
      await loadResources();
      return true;
    } catch (error) {
      console.error('Error deleting resource:', error);
      showToast(`Error deleting ${config.displayName}`, 'error');
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  // Get current resource config
  const getCurrentConfig = (): ResourceConfig | null => {
    return activeResource ? resourceConfig[activeResource] : null;
  };

  // Get visible columns (not hidden)
  const getVisibleColumns = () => {
    const config = getCurrentConfig();
    return config ? config.columns.filter((col: { type: string }) => col.type !== 'hidden') : [];
  };

  return {
    // State
    items,
    isLoading,
    
    // Actions
    loadResources,
    deleteResource,
    
    // Helpers
    getCurrentConfig,
    getVisibleColumns
  };
};