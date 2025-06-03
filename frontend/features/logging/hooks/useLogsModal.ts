// frontend/features/logging/hooks/useLogsModal.ts
import { useState } from 'react';
import { loggingApi } from '@/services/api';
import type { Log } from '@/types/logging';

export const useLogsModal = () => {
  const [selectedLog, setSelectedLog] = useState<Log | null>(null);
  const [showModal, setShowModal] = useState<boolean>(false);

  const showLogDetails = async (logId: number) => {
    try {
      const response = await loggingApi.getLogDetail(logId);
      if (response.data.length > 0) {
        setSelectedLog(response.data[0]);
        setShowModal(true);
      }
    } catch (error) {
      console.error('Error fetching log details:', error);
    }
  };

  const handleModalClose = () => {
    setShowModal(false);
    // Add a small delay before clearing the selectedLog to prevent UI issues
    setTimeout(() => {
      setSelectedLog(null);
    }, 100);
  };

  const openModal = (log: Log) => {
    setSelectedLog(log);
    setShowModal(true);
  };

  const closeModal = () => {
    handleModalClose();
  };

  return {
    // State
    selectedLog,
    showModal,
    
    // Actions
    showLogDetails,
    handleModalClose,
    openModal,
    closeModal
  };
};