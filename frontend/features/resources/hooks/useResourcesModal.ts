// frontend/features/resources/hooks/useResourcesModal.ts
import { useState } from 'react';
import { resourceConfig } from '@/config';
import type { ResourceItem } from '@/types';

interface UseResourcesModalProps {
  activeResource: string;
  onResourceSaved: () => void;
}

export const useResourcesModal = ({ activeResource, onResourceSaved }: UseResourcesModalProps) => {
  const [currentItem, setCurrentItem] = useState<ResourceItem | null>(null);
  const [showModal, setShowModal] = useState<boolean>(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');

  // Show create modal
  const showCreateModal = () => {
    if (!activeResource) return;
    
    const emptyItem: ResourceItem = {};
    
    // Initialize with empty values or defaults
    const config = resourceConfig[activeResource];
    config.columns.forEach((col: { type: string; field: string; options?: Array<{value: string | number}> }) => {
      if (col.type === 'checkbox') {
        emptyItem[col.field] = false;
      } else if (col.type === 'select' && col.options && col.options.length > 0) {
        emptyItem[col.field] = col.options[0].value;
      } else {
        emptyItem[col.field] = '';
      }
    });
    
    setCurrentItem(emptyItem);
    setModalMode('create');
    setShowModal(true);
  };

  // Show edit modal
  const showEditModal = (item: ResourceItem) => {
    setCurrentItem({...item});
    setModalMode('edit');
    setShowModal(true);
  };

  // Handle modal close
  const handleModalClose = () => {
    setShowModal(false);
    setCurrentItem(null);
  };

  // Handle resource saved
  const handleResourceSaved = () => {
    setShowModal(false);
    setCurrentItem(null);
    onResourceSaved();
  };

  // Get current resource config
  const getCurrentConfig = () => {
    return activeResource ? resourceConfig[activeResource] : null;
  };

  // Check if modal can be shown
  const canShowModal = () => {
    return !!activeResource && !!getCurrentConfig();
  };

  return {
    // State
    currentItem,
    showModal,
    modalMode,
    
    // Actions
    showCreateModal,
    showEditModal,
    handleModalClose,
    handleResourceSaved,
    
    // Helpers
    getCurrentConfig,
    canShowModal
  };
};