import React from 'react';
import { FILTER_OPTIONS } from '../constants/calculationConstants';

interface FilterSectionProps {
  selectedFilter: string;
  onFilterChange: (filter: string) => void;
  fieldsLoading: boolean;
}

const FilterSection: React.FC<FilterSectionProps> = ({
  selectedFilter,
  onFilterChange,
  fieldsLoading
}) => {
  return (
    <div className="card mb-4">
      <div className="card-header bg-primary">
        <h5 className="card-title mb-0">Filter Calculations</h5>
      </div>
      <div className="card-body">
        <div className="row">
          <div className="col-md-4">
            <label className="form-label">Group Level</label>
            <select
              value={selectedFilter}
              onChange={(e) => onFilterChange(e.target.value)}
              className="form-select"
              disabled={fieldsLoading}
            >
              {FILTER_OPTIONS.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <div className="form-text">Filter calculations by their group level</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FilterSection;