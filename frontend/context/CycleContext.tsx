import { createContext, useState, useContext, useEffect, ReactNode } from 'react';
import { reportsApi } from '@/services/api';

type CycleOption = {
  value: string;
  label: string;
};

interface CycleContextType {
  cycleCodes: CycleOption[];
  loading: boolean;
  error: string | null;
}

const defaultContextValue: CycleContextType = {
  cycleCodes: [{ value: '', label: 'All Cycles' }],
  loading: false,
  error: null
};

const CycleContext = createContext<CycleContextType>(defaultContextValue);

export const useCycleContext = () => useContext(CycleContext);

interface CycleProviderProps {
  children: ReactNode;
}

export const CycleProvider = ({ children }: CycleProviderProps) => {
  const [cycleCodes, setCycleCodes] = useState<CycleOption[]>([{ value: '', label: 'All Cycles' }]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [initialized, setInitialized] = useState<boolean>(false);

  useEffect(() => {
    const fetchCycleCodes = async () => {
      // Only fetch once
      if (initialized) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const response = await reportsApi.getCycleCodes();
        
        // Prepare options with 'All Cycles' as the first option
        const options = [
          { value: '', label: 'All Cycles' },
          ...response.data.map((item: { code: string }) => ({
            value: item.code,
            label: item.code
          }))
        ];
        
        setCycleCodes(options);
        setInitialized(true);
      } catch (error) {
        console.error('Error fetching cycle codes:', error);
        setError('Failed to load cycle codes');
      } finally {
        setLoading(false);
      }
    };
    
    fetchCycleCodes();
  }, [initialized]);

  return (
    <CycleContext.Provider value={{ cycleCodes, loading, error }}>
      {children}
    </CycleContext.Provider>
  );
};

export default CycleContext;