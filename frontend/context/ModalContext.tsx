// frontend/context/ModalContext.tsx
// Global modal context for managing top-level modals

import React, { createContext, useContext, useState, ReactNode } from 'react';

interface ModalContextType {
  // Execution Logs Modal
  showExecutionLogsModal: boolean;
  executionLogsReportId: number | null;
  executionLogsReportName: string;
  openExecutionLogsModal: (reportId: number, reportName: string) => void;
  closeExecutionLogsModal: () => void;
}

const ModalContext = createContext<ModalContextType | undefined>(undefined);

export const useModal = () => {
  const context = useContext(ModalContext);
  if (context === undefined) {
    throw new Error('useModal must be used within a ModalProvider');
  }
  return context;
};

interface ModalProviderProps {
  children: ReactNode;
}

export const ModalProvider: React.FC<ModalProviderProps> = ({ children }) => {
  // Execution Logs Modal State
  const [showExecutionLogsModal, setShowExecutionLogsModal] = useState(false);
  const [executionLogsReportId, setExecutionLogsReportId] = useState<number | null>(null);
  const [executionLogsReportName, setExecutionLogsReportName] = useState<string>('');

  const openExecutionLogsModal = (reportId: number, reportName: string) => {
    setExecutionLogsReportId(reportId);
    setExecutionLogsReportName(reportName);
    setShowExecutionLogsModal(true);
  };

  const closeExecutionLogsModal = () => {
    setShowExecutionLogsModal(false);
    setExecutionLogsReportId(null);
    setExecutionLogsReportName('');
  };

  const value: ModalContextType = {
    showExecutionLogsModal,
    executionLogsReportId,
    executionLogsReportName,
    openExecutionLogsModal,
    closeExecutionLogsModal,
  };

  return (
    <ModalContext.Provider value={value}>
      {children}
    </ModalContext.Provider>
  );
};

export default ModalProvider;