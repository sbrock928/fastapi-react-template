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
  const [calculationType, setCalculationType] = useState<'all' | 'raw' | 'aggregated'>('all');

  // Validation logic to check if a calculation is compatible with the current scope
  const isCalculationCompatible = (calc: AvailableCalculation): boolean => {
    if (scope === 'TRANCHE') {
      // Tranche-level reports should only include:
      // 1. Tranche-level calculations (group_level === 'tranche')
      // 2. RAW fields from Deal, Tranche, or TrancheBal models
      // 3. Aggregated calculations that are designed for tranche-level aggregation
      
      if (calc.group_level === 'tranche') {
        return true; // Tranche-level calculations are OK for tranche reports
      }
      
      if (calc.aggregation_function === 'RAW') {
        // RAW fields: allow fields from any model in tranche-level reports
        return true;
      }
      
      // For aggregated calculations, only allow those designed for tranche-level
      if (calc.aggregation_function !== 'RAW' && calc.group_level === 'tranche') {
        return true;
      }
      
      // Don't allow deal-level calculations in tranche reports
      return false;
    }
    
    if (scope === 'DEAL') {
      // Deal-level reports should only include:
      // 1. Deal-level calculations
      // 2. Aggregated TrancheBal calculations (these get aggregated to deal level)
      // 3. RAW fields from Deal model only
      
      if (calc.group_level === 'deal') {
        return true; // Deal-level calculations are always OK
      }
      
      if (calc.aggregation_function === 'RAW') {
        // RAW fields: only allow Deal model fields in deal-level reports
        return calc.source_model === 'Deal';
      }
      
      if (calc.aggregation_function !== 'RAW') {
        // Aggregated calculations: check if they're designed for deal-level aggregation
        return calc.group_level === 'deal';
      }
    }
    
    return true;
  };

  // Get incompatible calculations for warnings
  const getIncompatibilityReason = (calc: AvailableCalculation): string | null => {
    if (isCalculationCompatible(calc)) return null;
    
    if (scope === 'DEAL') {
      if (calc.aggregation_function === 'RAW' && calc.source_model !== 'Deal') {
        return `Raw ${calc.source_model} fields would create multiple rows per deal. Use aggregated calculations instead.`;
      }
      
      if (calc.group_level === 'tranche') {
        return `This tranche-level calculation would create multiple rows per deal.`;
      }
    }
    
    if (scope === 'TRANCHE') {
      if (calc.group_level === 'deal') {
        return `This deal-level calculation is designed for deal-level aggregation and not appropriate for tranche-level reports.`;
      }
      
      if (calc.aggregation_function !== 'RAW' && calc.group_level !== 'tranche') {
        return `This aggregated calculation is not designed for tranche-level reporting.`;
      }
    }
    
    return 'This calculation is not compatible with the selected report scope.';
  };

  // Group calculations by category and type
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

  // Separate raw fields from aggregated calculations
  const { rawFields, aggregatedCalculations } = useMemo(() => {
    const raw = availableCalculations.filter(calc => calc.aggregation_function === 'RAW');
    const aggregated = availableCalculations.filter(calc => calc.aggregation_function !== 'RAW');
    return { rawFields: raw, aggregatedCalculations: aggregated };
  }, [availableCalculations]);

  // Filter and separate compatible/incompatible calculations
  const { compatibleCalculations, incompatibleCalculations } = useMemo(() => {
    let calculations = availableCalculations;

    // Filter by calculation type
    if (calculationType === 'raw') {
      calculations = calculations.filter(calc => calc.aggregation_function === 'RAW');
    } else if (calculationType === 'aggregated') {
      calculations = calculations.filter(calc => calc.aggregation_function !== 'RAW');
    }

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

    // Separate compatible and incompatible
    const compatible = calculations.filter(isCalculationCompatible);
    const incompatible = calculations.filter(calc => !isCalculationCompatible(calc));

    return { compatibleCalculations: compatible, incompatibleCalculations: incompatible };
  }, [availableCalculations, selectedCategory, searchTerm, calculationType, scope]);

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
      // Check compatibility before adding
      if (!isCalculationCompatible(availableCalc)) {
        // Show warning but don't prevent selection - let user understand the issue
        return; // Could show a toast message here
      }
      
      // Add calculation
      const newCalculation: ReportCalculation = {
        calculation_id: availableCalc.id,
        display_order: selectedCalculations.length,
        display_name: undefined // Use default name
      };
      onCalculationsChange([...selectedCalculations, newCalculation]);
    }
  };

  // Handle select all with validation
  const handleSelectAllRaw = () => {
    const compatibleRawFields = rawFields.filter(isCalculationCompatible);
    const rawCalculations = compatibleRawFields.map((calc, index) => ({
      calculation_id: calc.id,
      display_order: selectedCalculations.length + index,
      display_name: undefined
    }));
    onCalculationsChange([...selectedCalculations, ...rawCalculations]);
  };

  const handleSelectAllAggregated = () => {
    const compatibleAggregated = aggregatedCalculations.filter(isCalculationCompatible);
    const aggregatedCalcs = compatibleAggregated.map((calc, index) => ({
      calculation_id: calc.id,
      display_order: selectedCalculations.length + index,
      display_name: undefined
    }));
    onCalculationsChange([...selectedCalculations, ...aggregatedCalcs]);
  };

  const handleSelectAll = () => {
    const compatibleCalculations = availableCalculations.filter(isCalculationCompatible);
    const allCalculations = compatibleCalculations.map((calc, index) => ({
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
          <h5>Select Fields and Calculations for {scope} Report</h5>
          <p className="text-muted">
            Choose raw fields (individual values) and aggregated calculations to include in your report.
          </p>
        </div>
        <div className="col-md-6">
          <div className="d-flex gap-2 justify-content-end">
            <button
              className="btn btn-outline-info btn-sm"
              onClick={handleSelectAllRaw}
              disabled={rawFields.length === 0}
            >
              <i className="bi bi-file-text"></i> All Raw Fields
            </button>
            <button
              className="btn btn-outline-warning btn-sm"
              onClick={handleSelectAllAggregated}
              disabled={aggregatedCalculations.length === 0}
            >
              <i className="bi bi-calculator"></i> All Calculations
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
        <div className="col-md-4">
          <input
            type="text"
            className="form-control"
            placeholder="Search fields and calculations..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="col-md-4">
          <select
            className="form-select"
            value={calculationType}
            onChange={(e) => setCalculationType(e.target.value as 'all' | 'raw' | 'aggregated')}
          >
            <option value="all">All Types</option>
            <option value="raw">Raw Fields Only</option>
            <option value="aggregated">Aggregated Calculations Only</option>
          </select>
        </div>
        <div className="col-md-4">
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

      {/* Summary Information */}
      <div className="row mb-3">
        <div className="col-12">
          <div className="d-flex gap-3 text-muted small">
            <span>Total Available: {availableCalculations.length}</span>
            <span>Raw Fields: {rawFields.length}</span>
            <span>Aggregated Calculations: {aggregatedCalculations.length}</span>
            <span>Currently Selected: {selectedCalculations.length}</span>
          </div>
        </div>
      </div>

      {/* Selected Calculations Summary */}
      {selectedCalculations.length > 0 && (
        <div className="alert alert-info mb-3">
          <strong>Selected Fields & Calculations ({selectedCalculations.length}):</strong>
          <div className="mt-2">
            {selectedCalculations.map(calc => {
              const availableCalc = availableCalculations.find(ac => ac.id === calc.calculation_id);
              const displayName = calc.display_name || availableCalc?.name || `Calculation ${calc.calculation_id}`;
              const isRaw = availableCalc?.aggregation_function === 'RAW';
              return (
                <span 
                  key={calc.calculation_id} 
                  className={`badge ${isRaw ? 'bg-info' : 'bg-primary'} me-1 mb-1`}
                  title={isRaw ? 'Raw Field' : 'Aggregated Calculation'}
                >
                  {isRaw && <i className="bi bi-file-text me-1"></i>}
                  {!isRaw && <i className="bi bi-calculator me-1"></i>}
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

      {/* Scope Compatibility Warning */}
      {scope === 'DEAL' && incompatibleCalculations.length > 0 && (
        <div className="alert alert-warning mb-3">
          <i className="bi bi-exclamation-triangle me-2"></i>
          <strong>Deal-Level Report Compatibility:</strong> Some calculations are not compatible with deal-level reports 
          because they would create multiple rows per deal. These have been filtered out or disabled.
          <details className="mt-2">
            <summary>Why are some calculations incompatible?</summary>
            <ul className="mt-2 mb-0">
              <li><strong>Raw Tranche/TrancheBal fields:</strong> Would show individual tranche data, creating multiple rows per deal</li>
              <li><strong>Tranche-level calculations:</strong> Designed to aggregate at tranche level, not deal level</li>
              <li><strong>Solution:</strong> Use deal-level aggregated calculations instead (SUM, AVG, etc.)</li>
            </ul>
          </details>
        </div>
      )}

      {scope === 'TRANCHE' && incompatibleCalculations.length > 0 && (
        <div className="alert alert-warning mb-3">
          <i className="bi bi-exclamation-triangle me-2"></i>
          <strong>Tranche-Level Report Compatibility:</strong> Some calculations are not compatible with tranche-level reports 
          because they are designed for deal-level aggregation. These have been filtered out or disabled.
          <details className="mt-2">
            <summary>Why are some calculations incompatible?</summary>
            <ul className="mt-2 mb-0">
              <li><strong>Deal-level calculations:</strong> Designed to aggregate data at the deal level, not appropriate for tranche-level analysis</li>
              <li><strong>Deal-level custom SQL:</strong> Contains business logic specific to deal-level aggregation</li>
              <li><strong>Solution:</strong> Use tranche-level calculations or raw fields instead</li>
            </ul>
          </details>
        </div>
      )}

      {/* Available Calculations List */}
      <div className="row">
        {/* Compatible Calculations */}
        {compatibleCalculations.length === 0 && incompatibleCalculations.length === 0 ? (
          <div className="col-12">
            <div className="text-center text-muted p-4">
              {searchTerm || selectedCategory !== 'all' || calculationType !== 'all'
                ? 'No fields or calculations match your search criteria.' 
                : 'No fields or calculations available.'}
            </div>
          </div>
        ) : (
          <>
            {compatibleCalculations.map(calc => {
              const isSelected = isCalculationSelected(calc.id);
              const isRaw = calc.aggregation_function === 'RAW';
              return (
                <div key={calc.id} className="col-md-6 col-lg-4 mb-3">
                  <div 
                    className={`card h-100 ${isSelected ? 'border-primary bg-light' : ''} ${isRaw ? 'border-info' : ''}`}
                    style={{ cursor: 'pointer' }}
                    onClick={() => handleCalculationToggle(calc)}
                  >
                    <div className="card-body">
                      <div className="d-flex justify-content-between align-items-start mb-2">
                        <h6 className="card-title mb-0">
                          {isRaw && <i className="bi bi-file-text text-info me-1" title="Raw Field"></i>}
                          {!isRaw && <i className="bi bi-calculator text-primary me-1" title="Aggregated Calculation"></i>}
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
                        <span className={`badge ${isRaw ? 'bg-info' : 'bg-success'}`}>
                          {isRaw ? 'Raw Field' : calc.aggregation_function}
                        </span>
                        <span className="badge bg-success ms-1">
                          <i className="bi bi-check-circle me-1"></i>Compatible
                        </span>
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
                      {isRaw && (
                        <p className="card-text small text-info">
                          <i className="bi bi-info-circle me-1"></i>
                          Shows individual row values without aggregation
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Incompatible Calculations (shown as disabled) */}
            {incompatibleCalculations.map(calc => {
              const isRaw = calc.aggregation_function === 'RAW';
              const incompatibilityReason = getIncompatibilityReason(calc);
              return (
                <div key={calc.id} className="col-md-6 col-lg-4 mb-3">
                  <div 
                    className="card h-100 border-warning bg-light"
                    style={{ opacity: 0.7, cursor: 'not-allowed' }}
                    title={incompatibilityReason || 'Not compatible with current report scope'}
                  >
                    <div className="card-body">
                      <div className="d-flex justify-content-between align-items-start mb-2">
                        <h6 className="card-title mb-0 text-muted">
                          {isRaw && <i className="bi bi-file-text text-muted me-1" title="Raw Field"></i>}
                          {!isRaw && <i className="bi bi-calculator text-muted me-1" title="Aggregated Calculation"></i>}
                          {calc.name}
                          <i className="bi bi-exclamation-triangle text-warning ms-1" title="Not compatible"></i>
                        </h6>
                        <input
                          type="checkbox"
                          className="form-check-input"
                          checked={false}
                          disabled={true}
                        />
                      </div>
                      <div className="text-muted small mb-2">
                        <span className="badge bg-secondary me-1">{calc.category}</span>
                        <span className={`badge ${isRaw ? 'bg-info' : 'bg-success'}`}>
                          {isRaw ? 'Raw Field' : calc.aggregation_function}
                        </span>
                        <span className="badge bg-warning text-dark ms-1">
                          <i className="bi bi-exclamation-triangle me-1"></i>Incompatible
                        </span>
                      </div>
                      <p className="card-text small text-muted">
                        <strong>Source:</strong> {calc.source_model}.{calc.source_field}
                      </p>
                      {incompatibilityReason && (
                        <div className="alert alert-warning small py-2 mb-2">
                          <i className="bi bi-info-circle me-1"></i>
                          {incompatibilityReason}
                        </div>
                      )}
                      {calc.description && (
                        <p className="card-text small text-muted">
                          {calc.description}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </>
        )}
      </div>

      {/* Footer Info */}
      <div className="row mt-3">
        <div className="col-12">
          <small className="text-muted">
            Showing {compatibleCalculations.length} compatible + {incompatibleCalculations.length} incompatible 
            of {availableCalculations.length} total fields and calculations. 
            {selectedCalculations.length > 0 && ` ${selectedCalculations.length} selected.`}
          </small>
          {scope === 'DEAL' && incompatibleCalculations.length > 0 && (
            <div className="small text-warning mt-1">
              <i className="bi bi-exclamation-triangle me-1"></i>
              {incompatibleCalculations.length} calculation(s) are incompatible with deal-level reports and are shown as disabled.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CalculationSelector;