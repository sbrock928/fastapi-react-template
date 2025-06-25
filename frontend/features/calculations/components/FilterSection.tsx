import React from 'react';
import { FILTER_OPTIONS, SYSTEM_FILTER_OPTIONS } from '../constants/calculationConstants';

interface FilterSectionProps {
  selectedFilter: string;
  onFilterChange: (filter: string) => void;
  fieldsLoading: boolean;
  filterType?: 'user' | 'system'; // Add optional prop to determine which filter options to use
}

const FilterSection: React.FC<FilterSectionProps> = ({
  selectedFilter,
  onFilterChange,
  fieldsLoading,
  filterType = 'user'
}) => {
  // Choose filter options based on the filter type
  const filterOptions = filterType === 'system' ? SYSTEM_FILTER_OPTIONS : FILTER_OPTIONS;

  return (
    <div className="card mb-4">
      <div className="card-header bg-primary">
        <h5 className="card-title mb-0">Filter Calculations</h5>
      </div>
      <div className="card-body">
        <div className="row">
          <div className="col-md-4">
            <label className="form-label">
              {filterType === 'system' ? 'Filter Type' : 'Group Level'}
            </label>
            <select
              value={selectedFilter}
              onChange={(e) => onFilterChange(e.target.value)}
              className="form-select"
              disabled={fieldsLoading}
            >
              {filterOptions.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <div className="form-text">
              {filterType === 'system' 
                ? 'Filter calculations by type or group level' 
                : 'Filter calculations by their group level'
              }
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FilterSection;