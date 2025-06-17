// frontend/context/ModalContext.tsx
// Global modal context for managing top-level modals

import React, { createContext, useContext, useState, ReactNode } from 'react';
import type { CDIVariableResponse } from '@/types/cdi';

interface ModalContextType {
  // CDI Variable Modal
  showCDIModal: boolean;
  editingCDIVariable: CDIVariableResponse | null;
  cdiModalMode: 'create' | 'edit';
  openCDIModal: (variable?: CDIVariableResponse) => void;
  closeCDIModal: () => void;
  onCDIVariableSaved?: () => void;
  setOnCDIVariableSaved: (callback: () => void) => void;
  
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
  // CDI Variable Modal State
  const [showCDIModal, setShowCDIModal] = useState(false);
  const [editingCDIVariable, setEditingCDIVariable] = useState<CDIVariableResponse | null>(null);
  const [cdiModalMode, setCDIModalMode] = useState<'create' | 'edit'>('create');
  const [onCDIVariableSaved, setOnCDIVariableSaved] = useState<(() => void) | undefined>();

  // Execution Logs Modal State
  const [showExecutionLogsModal, setShowExecutionLogsModal] = useState(false);
  const [executionLogsReportId, setExecutionLogsReportId] = useState<number | null>(null);
  const [executionLogsReportName, setExecutionLogsReportName] = useState<string>('');

  const openCDIModal = (variable?: CDIVariableResponse) => {
    if (variable) {
      setEditingCDIVariable(variable);
      setCDIModalMode('edit');
    } else {
      setEditingCDIVariable(null);
      setCDIModalMode('create');
    }
    setShowCDIModal(true);
  };

  const closeCDIModal = () => {
    setShowCDIModal(false);
    setEditingCDIVariable(null);
    setCDIModalMode('create');
  };

  const handleSetOnCDIVariableSaved = (callback: () => void) => {
    setOnCDIVariableSaved(() => callback);
  };

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
    showCDIModal,
    editingCDIVariable,
    cdiModalMode,
    openCDIModal,
    closeCDIModal,
    onCDIVariableSaved,
    setOnCDIVariableSaved: handleSetOnCDIVariableSaved,
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