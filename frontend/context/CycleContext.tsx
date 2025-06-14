import { createContext, useState, useContext, useEffect, ReactNode } from 'react';
import { reportingApi } from '@/services/api';
import type { CycleOption } from '@/types/reporting';

interface CycleContextType {
  cycleCodes: CycleOption[];
  selectedCycle: CycleOption | null;
  setSelectedCycle: (cycle: CycleOption | null) => void;
  loading: boolean;
  error: string | null;
}

const CycleContext = createContext<CycleContextType | undefined>(undefined);

export const useCycleContext = (): CycleContextType => {
  const context = useContext(CycleContext);
  if (!context) {
    throw new Error('useCycleContext must be used within a CycleProvider');
  }
  return context;
};

interface CycleProviderProps {
  children: ReactNode;
}

export const CycleProvider: React.FC<CycleProviderProps> = ({ children }) => {
  const [cycleCodes, setCycleCodes] = useState<CycleOption[]>([]);
  const [selectedCycle, setSelectedCycle] = useState<CycleOption | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [initialized, setInitialized] = useState<boolean>(false);

  useEffect(() => {
    const fetchCycleCodes = async () => {
      if (initialized) return;

      setLoading(true);
      setError(null);
      
      try {
        const response = await reportingApi.getAvailableCycles();

        // Handle both possible response formats:
        // 1. Direct array: [{ label: string, value: number }]
        // 2. Wrapped response: { data: [{ label: string, value: number }] }
        const cycleData = Array.isArray(response.data) 
          ? response.data 
          : Array.isArray(response) 
            ? response 
            : response.data && Array.isArray(response.data) 
              ? response.data 
              : [];

        const options = [
          { value: 0, label: 'Select a Cycle' },
          ...cycleData.map((item: { label: string; value: string | number }) => ({
            value: typeof item.value === 'string' ? parseInt(item.value, 10) : item.value,
            label: item.label
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
    <CycleContext.Provider value={{ cycleCodes, selectedCycle, setSelectedCycle, loading, error }}>
      {children}
    </CycleContext.Provider>
  );
};

export default CycleContext;
