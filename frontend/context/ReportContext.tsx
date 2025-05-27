import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { reportingApi } from '@/services/api';
import type { ReportSummary } from '@/types';

interface ReportContextType {
  savedReports: ReportSummary[];
  loading: boolean;
  error: string | null;
  refreshReports: () => Promise<void>;
}

const ReportContext = createContext<ReportContextType | undefined>(undefined);

interface ReportProviderProps {
  children: ReactNode;
}

export const ReportProvider: React.FC<ReportProviderProps> = ({ children }) => {
  const [savedReports, setSavedReports] = useState<ReportSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const refreshReports = async () => {
    if (loading) return; // Prevent concurrent calls
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await reportingApi.getReportsSummary();
      setSavedReports(response.data);
    } catch (err) {
      console.error('Error loading saved reports:', err);
      setError('Failed to load saved reports');
    } finally {
      setLoading(false);
    }
  };

  // Load reports on mount
  useEffect(() => {
    refreshReports();
  }, []);

  const value: ReportContextType = {
    savedReports,
    loading,
    error,
    refreshReports
  };

  return (
    <ReportContext.Provider value={value}>
      {children}
    </ReportContext.Provider>
  );
};

export const useReportContext = () => {
  const context = useContext(ReportContext);
  if (context === undefined) {
    throw new Error('useReportContext must be used within a ReportProvider');
  }
  return context;
};