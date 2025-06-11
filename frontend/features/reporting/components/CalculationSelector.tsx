// frontend/features/reporting/components/CalculationSelector.tsx
// Updated to work with the new separated calculation system

import React, { useState, useMemo } from 'react';
import { 
  AvailableCalculation, 
  ReportCalculation, 
  isStaticFieldCalculation,
  isUserDefinedCalculation,
  isSystemSqlCalculation,
  getCalculationCompatibilityInfo,
  createReportCalculation
} from '@/types/reporting';

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
  const [calculationType, setCalculationType] = useState<'all' | 'user' | 'system' | 'static'>('all');

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

  // Separate calculations by type for analysis
  const { userCalculations, systemCalculations, staticFields } = useMemo(() => {
    const user = availableCalculations.filter(calc => isUserDefinedCalculation(calc));
    const system = availableCalculations.filter(calc => isSystemSqlCalculation(calc));
    const static_ = availableCalculations.filter(calc => isStaticFieldCalculation(calc));
    return { 
      userCalculations: user, 
      systemCalculations: system, 
      staticFields: static_ 
    };
  }, [availableCalculations]);

  // Filter and separate compatible/incompatible calculations
  const { compatibleCalculations, incompatibleCalculations } = useMemo(() => {
    let calculations = availableCalculations;

    // Filter by calculation type
    if (calculationType === 'user') {
      calculations = calculations.filter(calc => isUserDefinedCalculation(calc));
    } else if (calculationType === 'system') {
      calculations = calculations.filter(calc => isSystemSqlCalculation(calc));
    } else if (calculationType === 'static') {
      calculations = calculations.filter(calc => isStaticFieldCalculation(calc));
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
        calc.aggregation_function?.toLowerCase().includes(search) ||
        calc.source_field?.toLowerCase().includes(search)
      );
    }

    // Separate compatible and incompatible
    const compatible = calculations.filter(calc => {
      const { isCompatible } = getCalculationCompatibilityInfo(calc, scope);
      return isCompatible;
    });
    const incompatible = calculations.filter(calc => {
      const { isCompatible } = getCalculationCompatibilityInfo(calc, scope);
      return !isCompatible;
    });

    return { compatibleCalculations: compatible, incompatibleCalculations: incompatible };
  }, [availableCalculations, selectedCategory, searchTerm, calculationType, scope]);

  // Check if a calculation is selected
  const isCalculationSelected = (calc: AvailableCalculation): boolean => {
    return selectedCalculations.some(selected => {
      if (typeof calc.id === 'string' && calc.id.startsWith('static_')) {
        // For static fields, compare by matching the static field logic
        return selected.calculation_type === 'static' && 
               hashStringToNumber(calc.id) === selected.calculation_id;
      } else {
        // For user/system calculations, compare by numeric ID
        return typeof calc.id === 'number' && calc.id === selected.calculation_id;
      }
    });
  };

  // Handle calculation toggle
  const handleCalculationToggle = (availableCalc: AvailableCalculation) => {
    const isSelected = isCalculationSelected(availableCalc);

    if (isSelected) {
      // Remove calculation
      const updatedCalculations = selectedCalculations.filter(selected => {
        if (typeof availableCalc.id === 'string' && availableCalc.id.startsWith('static_')) {
          return !(selected.calculation_type === 'static' && 
                  hashStringToNumber(availableCalc.id) === selected.calculation_id);
        } else {
          return !(typeof availableCalc.id === 'number' && availableCalc.id === selected.calculation_id);
        }
      });
      onCalculationsChange(updatedCalculations);
    } else {
      // Check compatibility before adding
      const { isCompatible, reason } = getCalculationCompatibilityInfo(availableCalc, scope);
      if (!isCompatible && reason) {
        // Could show a toast message here
        console.warn(`Cannot add incompatible calculation: ${reason}`);
        return;
      }
      
      // Add calculation using the helper function
      const newCalculation = createReportCalculation(availableCalc, selectedCalculations.length);
      onCalculationsChange([...selectedCalculations, newCalculation]);
    }
  };

  // Handle select all with validation and type filtering
  const handleSelectAllByType = (type: 'user' | 'system' | 'static') => {
    let targetCalculations: AvailableCalculation[] = [];
    
    if (type === 'user') {
      targetCalculations = userCalculations;
    } else if (type === 'system') {
      targetCalculations = systemCalculations;
    } else if (type === 'static') {
      targetCalculations = staticFields;
    }

    // Filter for compatible calculations
    const compatibleTargets = targetCalculations.filter(calc => {
      const { isCompatible } = getCalculationCompatibilityInfo(calc, scope);
      return isCompatible;
    });

    const newCalculations = compatibleTargets.map((calc, index) => 
      createReportCalculation(calc, selectedCalculations.length + index)
    );
    
    onCalculationsChange([...selectedCalculations, ...newCalculations]);
  };

  const handleSelectAll = () => {
    const compatibleCalcs = compatibleCalculations.map((calc, index) => 
      createReportCalculation(calc, index)
    );
    onCalculationsChange(compatibleCalcs);
  };

  // Handle clear all
  const handleClearAll = () => {
    onCalculationsChange([]);
  };

  // Helper function to convert string IDs to numbers (same as in types)
  function hashStringToNumber(str: string): number {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return Math.abs(hash);
  }

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
            Choose from user calculations, system calculations, and raw fields to include in your report.
          </p>
        </div>
        <div className="col-md-6">
          <div className="d-flex gap-2 justify-content-end flex-wrap">
            <button
              className="btn btn-outline-primary btn-sm"
              onClick={() => handleSelectAllByType('user')}
              disabled={userCalculations.length === 0}
            >
              <i className="bi bi-person-gear"></i> All User Calcs
            </button>
            <button
              className="btn btn-outline-warning btn-sm"
              onClick={() => handleSelectAllByType('system')}
              disabled={systemCalculations.length === 0}
            >
              <i className="bi bi-code-square"></i> All System Calcs
            </button>
            <button
              className="btn btn-outline-info btn-sm"
              onClick={() => handleSelectAllByType('static')}
              disabled={staticFields.length === 0}
            >
              <i className="bi bi-file-text"></i> All Raw Fields
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
        <div className="col-md-3">
          <input
            type="text"
            className="form-control"
            placeholder="Search calculations..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="col-md-3">
          <select
            className="form-select"
            value={calculationType}
            onChange={(e) => setCalculationType(e.target.value as 'all' | 'user' | 'system' | 'static')}
          >
            <option value="all">All Types</option>
            <option value="user">User Calculations</option>
            <option value="system">System Calculations</option>
            <option value="static">Raw Fields</option>
          </select>
        </div>
        <div className="col-md-3">
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
        <div className="col-md-3">
          <div className="text-muted small">
            {compatibleCalculations.length} compatible, {incompatibleCalculations.length} incompatible
          </div>
        </div>
      </div>

      {/* Summary Information */}
      <div className="row mb-3">
        <div className="col-12">
          <div className="d-flex gap-3 text-muted small flex-wrap">
            <span>Total Available: {availableCalculations.length}</span>
            <span>User Calculations: {userCalculations.length}</span>
            <span>System Calculations: {systemCalculations.length}</span>
            <span>Raw Fields: {staticFields.length}</span>
            <span className="fw-bold text-primary">Currently Selected: {selectedCalculations.length}</span>
          </div>
        </div>
      </div>

      {/* Selected Calculations Summary */}
      {selectedCalculations.length > 0 && (
        <div className="alert alert-info mb-3">
          <strong>Selected Calculations ({selectedCalculations.length}):</strong>
          <div className="mt-2">
            {selectedCalculations.map(calc => {
              const availableCalc = availableCalculations.find(ac => {
                if (calc.calculation_type === 'static') {
                  return typeof ac.id === 'string' && hashStringToNumber(ac.id) === calc.calculation_id;
                } else {
                  return typeof ac.id === 'number' && ac.id === calc.calculation_id;
                }
              });
              
              const displayName = calc.display_name || availableCalc?.name || `Calculation ${calc.calculation_id}`;
              const calcType = calc.calculation_type || 'unknown';
              const badgeClass = calcType === 'static' ? 'bg-info' : calcType === 'system' ? 'bg-warning text-dark' : 'bg-primary';
              const icon = calcType === 'static' ? 'bi-file-text' : calcType === 'system' ? 'bi-code-square' : 'bi-person-gear';
              
              return (
                <span 
                  key={`${calc.calculation_type}-${calc.calculation_id}`}
                  className={`badge ${badgeClass} me-1 mb-1`}
                  title={`${calcType} calculation`}
                >
                  <i className={`bi ${icon} me-1`}></i>
                  {displayName}
                  <button
                    type="button"
                    className="btn-close btn-close-white ms-1"
                    style={{ fontSize: '0.7em' }}
                    onClick={() => {
                      if (availableCalc) handleCalculationToggle(availableCalc);
                    }}
                  ></button>
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* Enhanced scope compatibility warnings */}
      {scope === 'DEAL' && incompatibleCalculations.length > 0 && (
        <div className="alert alert-warning mb-3">
          <i className="bi bi-exclamation-triangle me-2"></i>
          <strong>Deal-Level Report Compatibility:</strong> Some calculations are not compatible with deal-level reports 
          because they would create multiple rows per deal. These have been marked as incompatible below.
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

      {/* Calculation Cards */}
      <div className="row">
        {/* Compatible Calculations */}
        {compatibleCalculations.length === 0 && incompatibleCalculations.length === 0 ? (
          <div className="col-12">
            <div className="text-center text-muted p-4">
              {searchTerm || selectedCategory !== 'all' || calculationType !== 'all'
                ? 'No calculations match your search criteria.' 
                : 'No calculations available.'}
            </div>
          </div>
        ) : (
          <>
            {compatibleCalculations.map(calc => {
              const isSelected = isCalculationSelected(calc);
              const isUser = isUserDefinedCalculation(calc);
              const isSystem = isSystemSqlCalculation(calc);
              const isStatic = isStaticFieldCalculation(calc);
              
              let calcTypeInfo = { icon: 'bi-question-circle', label: 'Unknown', badgeClass: 'bg-secondary' };
              if (isUser) {
                calcTypeInfo = { icon: 'bi-person-gear', label: 'User Calculation', badgeClass: 'bg-primary' };
              } else if (isSystem) {
                calcTypeInfo = { icon: 'bi-code-square', label: 'System SQL', badgeClass: 'bg-warning text-dark' };
              } else if (isStatic) {
                calcTypeInfo = { icon: 'bi-file-text', label: 'Raw Field', badgeClass: 'bg-info' };
              }

              return (
                <div key={`${calc.calculation_type}-${calc.id}`} className="col-md-6 col-lg-4 mb-3">
                  <div 
                    className={`card h-100 ${isSelected ? 'border-primary bg-light' : ''}`}
                    style={{ cursor: 'pointer' }}
                    onClick={() => handleCalculationToggle(calc)}
                  >
                    <div className="card-body">
                      <div className="d-flex justify-content-between align-items-start mb-2">
                        <h6 className="card-title mb-0">
                          <i className={`bi ${calcTypeInfo.icon} me-1`}></i>
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
                        <span className={`badge ${calcTypeInfo.badgeClass}`}>
                          {calcTypeInfo.label}
                        </span>
                        <span className="badge bg-success ms-1">
                          <i className="bi bi-check-circle me-1"></i>Compatible
                        </span>
                      </div>
                      
                      {/* Enhanced source information */}
                      <p className="card-text small text-muted">
                        {isUser && (
                          <><strong>Source:</strong> {calc.source_model}.{calc.source_field}</>
                        )}
                        {isSystem && (
                          <><strong>Custom SQL</strong> → {calc.weight_field || 'result'}</>
                        )}
                        {isStatic && (
                          <><strong>Raw Field:</strong> {calc.source_field}</>
                        )}
                      </p>
                      
                      {calc.description && (
                        <p className="card-text small">
                          {calc.description}
                        </p>
                      )}
                      
                      {calc.weight_field && isUser && (
                        <p className="card-text small text-muted">
                          <strong>Weight Field:</strong> {calc.weight_field}
                        </p>
                      )}
                      
                      {/* Type-specific information */}
                      {isStatic && (
                        <p className="card-text small text-info">
                          <i className="bi bi-info-circle me-1"></i>
                          Shows individual row values without aggregation
                        </p>
                      )}
                      
                      {isSystem && (
                        <p className="card-text small text-warning">
                          <i className="bi bi-code-square me-1"></i>
                          Advanced custom SQL calculation
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Incompatible Calculations (shown as disabled) */}
            {incompatibleCalculations.map(calc => {
              const { reason } = getCalculationCompatibilityInfo(calc, scope);
              const isUser = isUserDefinedCalculation(calc);
              const isSystem = isSystemSqlCalculation(calc);
              const isStatic = isStaticFieldCalculation(calc);
              
              let calcTypeInfo = { icon: 'bi-question-circle', label: 'Unknown' };
              if (isUser) {
                calcTypeInfo = { icon: 'bi-person-gear', label: 'User Calculation' };
              } else if (isSystem) {
                calcTypeInfo = { icon: 'bi-code-square', label: 'System SQL' };
              } else if (isStatic) {
                calcTypeInfo = { icon: 'bi-file-text', label: 'Raw Field' };
              }
              
              return (
                <div key={`incompatible-${calc.calculation_type}-${calc.id}`} className="col-md-6 col-lg-4 mb-3">
                  <div 
                    className="card h-100 border-warning bg-light"
                    style={{ opacity: 0.7, cursor: 'not-allowed' }}
                    title={reason || 'Not compatible with current report scope'}
                  >
                    <div className="card-body">
                      <div className="d-flex justify-content-between align-items-start mb-2">
                        <h6 className="card-title mb-0 text-muted">
                          <i className={`bi ${calcTypeInfo.icon} text-muted me-1`}></i>
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
                        <span className="badge bg-light text-dark border">
                          {calcTypeInfo.label}
                        </span>
                        <span className="badge bg-warning text-dark ms-1">
                          <i className="bi bi-exclamation-triangle me-1"></i>Incompatible
                        </span>
                      </div>
                      
                      <p className="card-text small text-muted">
                        {isUser && (
                          <><strong>Source:</strong> {calc.source_model}.{calc.source_field}</>
                        )}
                        {isSystem && (
                          <><strong>Custom SQL</strong></>
                        )}
                        {isStatic && (
                          <><strong>Raw Field:</strong> {calc.source_field}</>
                        )}
                      </p>
                      
                      {reason && (
                        <div className="alert alert-warning small py-2 mb-2">
                          <i className="bi bi-info-circle me-1"></i>
                          {reason}
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

      {/* Footer Summary */}
      <div className="row mt-3">
        <div className="col-12">
          <small className="text-muted">
            Showing {compatibleCalculations.length} compatible + {incompatibleCalculations.length} incompatible 
            of {availableCalculations.length} total calculations. 
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