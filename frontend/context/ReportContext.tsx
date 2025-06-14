import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback, useRef } from 'react';
import { reportingApi } from '@/services/api';
import type { ReportSummary, Deal } from '@/types';

interface ReportContextType {
  savedReports: ReportSummary[];
  deals: Deal[];
  loading: boolean;
  dealsLoading: boolean;
  error: string | null;
  refreshReports: (force?: boolean) => Promise<void>;
  loadDealsOnce: () => Promise<void>;
}

const ReportContext = createContext<ReportContextType | undefined>(undefined);

interface ReportProviderProps {
  children: ReactNode;
}

export const ReportProvider: React.FC<ReportProviderProps> = ({ children }) => {
  const [savedReports, setSavedReports] = useState<ReportSummary[]>([]);
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [dealsLoading, setDealsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  // Use refs to track loading states to avoid circular dependencies
  const reportsLoadedRef = useRef<boolean>(false);
  const dealsLoadedRef = useRef<boolean>(false);
  const isLoadingReportsRef = useRef<boolean>(false);
  const isLoadingDealsRef = useRef<boolean>(false);

  const refreshReports = useCallback(async (force: boolean = false) => {
    // Prevent multiple simultaneous requests
    if (!force && (isLoadingReportsRef.current || reportsLoadedRef.current)) {
      console.log('Reports already loaded or loading, skipping API call');
      return;
    }
    
    if (force) {
      console.log('Force refreshing reports...');
    } else {
      console.log('Loading reports for the first time...');
    }
    
    isLoadingReportsRef.current = true;
    setLoading(true);
    setError(null);
    
    try {
      const response = await reportingApi.getReportsSummary();
      setSavedReports(response.data);
      reportsLoadedRef.current = true;
      console.log(`✅ Loaded ${response.data.length} reports ${force ? '(force refresh)' : '(cached for session)'}`);
    } catch (err) {
      console.error('Error loading saved reports:', err);
      setError('Failed to load saved reports');
    } finally {
      setLoading(false);
      isLoadingReportsRef.current = false;
    }
  }, []); // Remove dependencies to avoid circular dependency

  const loadDealsOnce = useCallback(async () => {
    // Prevent multiple simultaneous requests
    if (isLoadingDealsRef.current || dealsLoadedRef.current) {
      console.log('Deals already loaded or loading, skipping API call');
      return;
    }
    
    console.log('Loading deals for the first time...');
    isLoadingDealsRef.current = true;
    setDealsLoading(true);
    setError(null);
    
    try {
      const response = await reportingApi.getDeals();
      setDeals(response.data);
      dealsLoadedRef.current = true;
      console.log(`✅ Loaded ${response.data.length} deals (cached for session)`);
    } catch (err) {
      console.error('Error loading deals:', err);
      setError('Failed to load deals');
    } finally {
      setDealsLoading(false);
      isLoadingDealsRef.current = false;
    }
  }, []); // Remove dependencies to avoid circular dependency

  // Load reports on mount - only run once
  useEffect(() => {
    refreshReports();
  }, []); // Empty dependency array - only run on mount

  const value: ReportContextType = {
    savedReports,
    deals,
    loading,
    dealsLoading,
    error,
    refreshReports,
    loadDealsOnce
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