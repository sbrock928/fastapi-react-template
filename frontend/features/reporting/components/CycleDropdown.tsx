import React from 'react';
import { useCycleContext } from '@/context/CycleContext';

const CycleDropdown: React.FC = () => {
  const { cycleCodes, selectedCycle, setSelectedCycle, loading, error } = useCycleContext();
  
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedValue = parseInt(e.target.value, 10);
    const selected = cycleCodes.find(c => c.value === selectedValue);
    setSelectedCycle(selected || null);
  };

  if (error) {
    return (
      <div className="form-group">
        <label htmlFor="cycleCode" className="form-label">Cycle Code</label>
        <div className="text-danger">Error loading cycle codes</div>
      </div>
    );
  }

  return (
    <div className="form-group">
      <label htmlFor="cycleCode" className="form-label">Cycle Code</label>
      <select
        id="cycleCode"
        name="cycle_code"
        className="form-select"
        value={selectedCycle?.value || 0 }
        onChange={handleChange}
        disabled={loading}
      >
        {loading ? (
          <option value={0}>Loading...</option>
        ) : (
          cycleCodes.map(option => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))
        )}
      </select>
    </div>
  );
};

export default CycleDropdown;
