import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { reportingApi } from '@/services/api';
import type { ReportSummary, Deal } from '@/types'; // Added Deal import

interface ReportContextType {
  savedReports: ReportSummary[];
  deals: Deal[]; // Added deals to context
  loading: boolean;
  dealsLoading: boolean; // Added separate loading state for deals
  error: string | null;
  refreshReports: (force?: boolean) => Promise<void>; // Updated to accept force parameter
  loadDealsOnce: () => Promise<void>; // Added function to load deals once
}

const ReportContext = createContext<ReportContextType | undefined>(undefined);

interface ReportProviderProps {
  children: ReactNode;
}

export const ReportProvider: React.FC<ReportProviderProps> = ({ children }) => {
  const [savedReports, setSavedReports] = useState<ReportSummary[]>([]);
  const [deals, setDeals] = useState<Deal[]>([]); // Added deals state
  const [loading, setLoading] = useState<boolean>(false);
  const [dealsLoading, setDealsLoading] = useState<boolean>(false); // Added deals loading state
  const [error, setError] = useState<string | null>(null);
  const [dealsLoaded, setDealsLoaded] = useState<boolean>(false); // Track if deals have been loaded
  const [reportsLoaded, setReportsLoaded] = useState<boolean>(false); // Track if reports have been loaded

  const refreshReports = useCallback(async (force: boolean = false) => {
    if (!force && (loading || reportsLoaded)) {
      console.log('Reports already loaded or loading, skipping API call');
      return; // Prevent loading if already loaded or loading
    }
    
    if (force) {
      console.log('Force refreshing reports...');
    } else {
      console.log('Loading reports for the first time...');
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await reportingApi.getReportsSummary();
      setSavedReports(response.data);
      setReportsLoaded(true);
      console.log(`✅ Loaded ${response.data.length} reports ${force ? '(force refresh)' : '(cached for session)'}`);
    } catch (err) {
      console.error('Error loading saved reports:', err);
      setError('Failed to load saved reports');
    } finally {
      setLoading(false);
    }
  }, [loading, reportsLoaded]); // Memoize based on loading states

  // Load deals only once per session
  const loadDealsOnce = useCallback(async () => {
    if (dealsLoaded || dealsLoading) {
      console.log('Deals already loaded or loading, skipping API call');
      return; // Prevent loading if already loaded or loading
    }
    
    console.log('Loading deals for the first time...');
    setDealsLoading(true);
    setError(null);
    
    try {
      const response = await reportingApi.getDeals();
      setDeals(response.data);
      setDealsLoaded(true);
      console.log(`✅ Loaded ${response.data.length} deals (cached for session)`);
    } catch (err) {
      console.error('Error loading deals:', err);
      setError('Failed to load deals');
    } finally {
      setDealsLoading(false);
    }
  }, [dealsLoaded, dealsLoading]); // Memoize based on loading states

  // Load reports on mount
  useEffect(() => {
    refreshReports();
  }, [refreshReports]);

  const value: ReportContextType = {
    savedReports,
    deals, // Added deals to context value
    loading,
    dealsLoading, // Added deals loading to context value
    error,
    refreshReports,
    loadDealsOnce // Added deals loading function to context value
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