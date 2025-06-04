import React, { useState, useMemo } from 'react';
import { AvailableCalculation, ReportCalculation } from '../../../types/reporting';

interface CalculationSelectorProps {
  scope: 'DEAL' | 'TRANCHE';
  availableCalculations: AvailableCalculation[];
  selectedCalculations: ReportCalculation[];
  onCalculationsChange: (calculations: ReportCalculation[]) => void;
  loading?: boolean;
}

const CalculationSelector: React.FC<CalculationSelectorProps> = ({
  scope,
  availableCalculations,
  selectedCalculations,
  onCalculationsChange,
  loading = false
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  // Group calculations by category
  const calculationsByCategory = useMemo(() => {
    const grouped: Record<string, AvailableCalculation[]> = {};
    availableCalculations.forEach(calc => {
      if (!grouped[calc.category]) {
        grouped[calc.category] = [];
      }
      grouped[calc.category].push(calc);
    });
    return grouped;
  }, [availableCalculations]);

  const categories = useMemo(() => {
    return Object.keys(calculationsByCategory).sort();
  }, [calculationsByCategory]);

  // Filter calculations based on search and category
  const filteredCalculations = useMemo(() => {
    let calculations = availableCalculations;

    // Filter by category
    if (selectedCategory !== 'all') {
      calculations = calculations.filter(calc => calc.category === selectedCategory);
    }

    // Filter by search term
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      calculations = calculations.filter(calc => 
        calc.name.toLowerCase().includes(search) ||
        calc.description?.toLowerCase().includes(search) ||
        calc.aggregation_function.toLowerCase().includes(search) ||
        calc.source_field.toLowerCase().includes(search)
      );
    }

    return calculations;
  }, [availableCalculations, selectedCategory, searchTerm]);

  // Check if a calculation is selected
  const isCalculationSelected = (calcId: number): boolean => {
    return selectedCalculations.some(calc => calc.calculation_id === calcId);
  };

  // Handle calculation toggle
  const handleCalculationToggle = (availableCalc: AvailableCalculation) => {
    const isSelected = isCalculationSelected(availableCalc.id);

    if (isSelected) {
      // Remove calculation
      const updatedCalculations = selectedCalculations.filter(
        calc => calc.calculation_id !== availableCalc.id
      );
      onCalculationsChange(updatedCalculations);
    } else {
      // Add calculation
      const newCalculation: ReportCalculation = {
        calculation_id: availableCalc.id,
        display_order: selectedCalculations.length,
        display_name: undefined // Use default name
      };
      onCalculationsChange([...selectedCalculations, newCalculation]);
    }
  };

  // Handle select all defaults
  const handleSelectDefaults = () => {
    const defaultCalculations = availableCalculations
      .filter(calc => calc.is_default)
      .map((calc, index) => ({
        calculation_id: calc.id,
        display_order: index,
        display_name: undefined
      }));
    onCalculationsChange(defaultCalculations);
  };

  // Handle select all
  const handleSelectAll = () => {
    const allCalculations = availableCalculations.map((calc, index) => ({
      calculation_id: calc.id,
      display_order: index,
      display_name: undefined
    }));
    onCalculationsChange(allCalculations);
  };

  // Handle clear all
  const handleClearAll = () => {
    onCalculationsChange([]);
  };

  if (loading) {
    return (
      <div className="text-center p-4">
        <div className="spinner-border" role="status">
          <span className="visually-hidden">Loading calculations...</span>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header and Controls */}
      <div className="row mb-3">
        <div className="col-md-6">
          <h5>Select Calculations for {scope} Report</h5>
          <p className="text-muted">
            Choose which calculations to include in your report. Default calculations are pre-selected.
          </p>
        </div>
        <div className="col-md-6">
          <div className="d-flex gap-2 justify-content-end">
            <button
              className="btn btn-outline-primary btn-sm"
              onClick={handleSelectDefaults}
              disabled={availableCalculations.length === 0}
            >
              <i className="bi bi-star"></i> Select Defaults
            </button>
            <button
              className="btn btn-outline-secondary btn-sm"
              onClick={handleSelectAll}
              disabled={availableCalculations.length === 0}
            >
              Select All
            </button>
            <button
              className="btn btn-outline-danger btn-sm"
              onClick={handleClearAll}
              disabled={selectedCalculations.length === 0}
            >
              Clear All
            </button>
          </div>
        </div>
      </div>

      {/* Search and Filter Controls */}
      <div className="row mb-3">
        <div className="col-md-6">
          <input
            type="text"
            className="form-control"
            placeholder="Search calculations..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="col-md-6">
          <select
            className="form-select"
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
          >
            <option value="all">All Categories</option>
            {categories.map(category => (
              <option key={category} value={category}>{category}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Selected Calculations Summary */}
      {selectedCalculations.length > 0 && (
        <div className="alert alert-info mb-3">
          <strong>Selected Calculations ({selectedCalculations.length}):</strong>
          <div className="mt-2">
            {selectedCalculations.map(calc => {
              const availableCalc = availableCalculations.find(ac => ac.id === calc.calculation_id);
              const displayName = calc.display_name || availableCalc?.name || `Calculation ${calc.calculation_id}`;
              return (
                <span key={calc.calculation_id} className="badge bg-primary me-1 mb-1">
                  {displayName}
                  <button
                    type="button"
                    className="btn-close btn-close-white ms-1"
                    style={{ fontSize: '0.7em' }}
                    onClick={() => {
                      const availableCalc = availableCalculations.find(ac => ac.id === calc.calculation_id);
                      if (availableCalc) handleCalculationToggle(availableCalc);
                    }}
                  ></button>
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* Available Calculations List */}
      <div className="row">
        {filteredCalculations.length === 0 ? (
          <div className="col-12">
            <div className="text-center text-muted p-4">
              {searchTerm || selectedCategory !== 'all' 
                ? 'No calculations match your search criteria.' 
                : 'No calculations available.'}
            </div>
          </div>
        ) : (
          filteredCalculations.map(calc => {
            const isSelected = isCalculationSelected(calc.id);
            return (
              <div key={calc.id} className="col-md-6 col-lg-4 mb-3">
                <div 
                  className={`card h-100 ${isSelected ? 'border-primary bg-light' : ''}`}
                  style={{ cursor: 'pointer' }}
                  onClick={() => handleCalculationToggle(calc)}
                >
                  <div className="card-body">
                    <div className="d-flex justify-content-between align-items-start mb-2">
                      <h6 className="card-title mb-0">
                        {calc.name}
                        {calc.is_default && (
                          <span className="badge bg-warning text-dark ms-1" title="Default calculation">
                            <i className="bi bi-star-fill"></i>
                          </span>
                        )}
                      </h6>
                      <input
                        type="checkbox"
                        className="form-check-input"
                        checked={isSelected}
                        onChange={() => handleCalculationToggle(calc)}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </div>
                    <div className="text-muted small mb-2">
                      <span className="badge bg-secondary me-1">{calc.category}</span>
                      <span className="badge bg-info">{calc.aggregation_function}</span>
                    </div>
                    <p className="card-text small text-muted">
                      <strong>Source:</strong> {calc.source_model}.{calc.source_field}
                    </p>
                    {calc.description && (
                      <p className="card-text small">
                        {calc.description}
                      </p>
                    )}
                    {calc.weight_field && (
                      <p className="card-text small text-muted">
                        <strong>Weight Field:</strong> {calc.weight_field}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Footer Info */}
      <div className="row mt-3">
        <div className="col-12">
          <small className="text-muted">
            Showing {filteredCalculations.length} of {availableCalculations.length} available calculations. 
            {selectedCalculations.length > 0 && ` ${selectedCalculations.length} selected.`}
          </small>
        </div>
      </div>
    </div>
  );
};

export default CalculationSelector;