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
import { parseCalculationId } from '@/types/calculations';

// Helper function to get display type for AvailableCalculation
const getAvailableCalculationDisplayType = (calc: AvailableCalculation): string => {
  if (isUserDefinedCalculation(calc)) {
    return `User Defined (${calc.aggregation_function})`;
  } else if (isSystemSqlCalculation(calc)) {
    // Enhanced CDI variable detection
    const isCDIVariable = (
      calc.name.toLowerCase().includes('cdi') ||
      calc.description?.toLowerCase().includes('cdi variable') ||
      calc.description?.toLowerCase().includes('cdi calculation') ||
      calc.category?.toLowerCase().includes('cdi') ||
      calc.id.toLowerCase().includes('cdi') ||
      (calc.name.toLowerCase().includes('investment_income') ||
       calc.name.toLowerCase().includes('excess_interest') ||
       calc.name.toLowerCase().includes('principal_payments') ||
       calc.name.toLowerCase().includes('interest_payments'))
    );
    
    return isCDIVariable ? 'CDI Var' : 'System SQL';
  } else if (isStaticFieldCalculation(calc)) {
    return 'Raw Field';
  } else if (calc.calculation_type === 'DEPENDENT_CALCULATION') {
    return 'Dependent';
  }
  return 'Unknown';
};

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
  const [calculationType, setCalculationType] = useState<'all' | 'user' | 'system' | 'static' | 'dependent'>('all');
  const [sortBy, setSortBy] = useState<'name' | 'type' | 'category'>('name');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

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
    } else if (calculationType === 'dependent') {
      calculations = calculations.filter(calc => calc.calculation_type === 'DEPENDENT_CALCULATION');
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

    // Filter out static fields that duplicate default columns
    calculations = calculations.filter(calc => {
      if (isStaticFieldCalculation(calc)) {
        const duplicateStaticFields = [
          'static_deal.dl_nbr',
          'static_tranche.tr_id',
          'static_tranchebal.cycle_cde'
        ];
        return !duplicateStaticFields.includes(calc.id);
      }
      return true;
    });

    // Separate compatible and incompatible
    const compatible = calculations.filter(calc => {
      const { isCompatible } = getCalculationCompatibilityInfo(calc, scope);
      return isCompatible;
    });

    const incompatible = calculations.filter(calc => {
      const { isCompatible } = getCalculationCompatibilityInfo(calc, scope);
      return !isCompatible;
    });

    // Sort calculations
    const sortFunction = (a: AvailableCalculation, b: AvailableCalculation) => {
      let aValue: string, bValue: string;
      
      switch (sortBy) {
        case 'type':
          aValue = getAvailableCalculationDisplayType(a);
          bValue = getAvailableCalculationDisplayType(b);
          break;
        case 'category':
          aValue = a.category;
          bValue = b.category;
          break;
        case 'name':
        default:
          aValue = a.name;
          bValue = b.name;
          break;
      }
      
      const result = aValue.localeCompare(bValue);
      return sortDirection === 'desc' ? -result : result;
    };

    return { 
      compatibleCalculations: compatible.sort(sortFunction), 
      incompatibleCalculations: incompatible.sort(sortFunction) 
    };
  }, [availableCalculations, calculationType, selectedCategory, searchTerm, scope, sortBy, sortDirection]);

  // Check if calculation is selected
  const isCalculationSelected = (calc: AvailableCalculation): boolean => {
    return selectedCalculations.some(selected => selected.calculation_id === calc.id);
  };

  // Handle calculation toggle
  const handleCalculationToggle = (calc: AvailableCalculation) => {
    const isSelected = isCalculationSelected(calc);
    
    if (isSelected) {
      // Remove calculation
      const updatedCalculations = selectedCalculations.filter(
        selected => selected.calculation_id !== calc.id
      );
      onCalculationsChange(updatedCalculations);
    } else {
      // Check compatibility before adding
      const { isCompatible, reason } = getCalculationCompatibilityInfo(calc, scope);
      if (!isCompatible && reason) {
        console.warn(`Cannot add incompatible calculation: ${reason}`);
        return;
      }
      
      // Add calculation
      const newCalculation = createReportCalculation(calc, selectedCalculations.length);
      onCalculationsChange([...selectedCalculations, newCalculation]);
    }
  };

  // Handle bulk selections
  const handleSelectAllCompatible = () => {
    const newCalculations = compatibleCalculations
      .filter(calc => !isCalculationSelected(calc))
      .map((calc, index) => createReportCalculation(calc, selectedCalculations.length + index));
    
    onCalculationsChange([...selectedCalculations, ...newCalculations]);
  };

  const handleClearAll = () => {
    onCalculationsChange([]);
  };

  const handleSelectByType = (type: 'user' | 'system' | 'static') => {
    let targetCalculations: AvailableCalculation[] = [];
    
    if (type === 'user') {
      targetCalculations = compatibleCalculations.filter(calc => isUserDefinedCalculation(calc));
    } else if (type === 'system') {
      targetCalculations = compatibleCalculations.filter(calc => isSystemSqlCalculation(calc));
    } else if (type === 'static') {
      targetCalculations = compatibleCalculations.filter(calc => isStaticFieldCalculation(calc));
    }

    const newCalculations = targetCalculations
      .filter(calc => !isCalculationSelected(calc))
      .map((calc, index) => createReportCalculation(calc, selectedCalculations.length + index));
    
    onCalculationsChange([...selectedCalculations, ...newCalculations]);
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
      {/* Header */}
      <div className="row mb-4">
        <div className="col-md-6">
          <h5>Select Calculations for {scope} Report</h5>
          <p className="text-muted">
            Browse and select from {availableCalculations.length} available calculations.
          </p>
        </div>
        <div className="col-md-6 text-end">
          <div className="btn-group" role="group">
            <button
              className="btn btn-outline-primary btn-sm"
              onClick={() => handleSelectByType('user')}
              disabled={userCalculations.length === 0}
            >
              <i className="bi bi-person-gear me-1"></i>
              All User ({userCalculations.length})
            </button>
            <button
              className="btn btn-outline-warning btn-sm"
              onClick={() => handleSelectByType('system')}
              disabled={systemCalculations.length === 0}
            >
              <i className="bi bi-code-square me-1"></i>
              All System ({systemCalculations.length})
            </button>
            <button
              className="btn btn-outline-info btn-sm"
              onClick={() => handleSelectByType('static')}
              disabled={staticFields.length === 0}
            >
              <i className="bi bi-file-text me-1"></i>
              All Raw Fields ({staticFields.length})
            </button>
          </div>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="card mb-4">
        <div className="card-body">
          <div className="row g-3">
            <div className="col-md-3">
              <label className="form-label">Search</label>
              <input
                type="text"
                className="form-control"
                placeholder="Search calculations..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <div className="col-md-2">
              <label className="form-label">Type</label>
              <select
                className="form-select"
                value={calculationType}
                onChange={(e) => setCalculationType(e.target.value as 'all' | 'user' | 'system' | 'static' | 'dependent')}
              >
                <option value="all">All Types</option>
                <option value="user">User Calculations</option>
                <option value="system">System Calculations</option>
                <option value="static">Raw Fields</option>
                <option value="dependent">Dependent Calculations</option>
              </select>
            </div>
            <div className="col-md-2">
              <label className="form-label">Category</label>
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
            <div className="col-md-2">
              <label className="form-label">Sort By</label>
              <select
                className="form-select"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'name' | 'type' | 'category')}
              >
                <option value="name">Name</option>
                <option value="type">Type</option>
                <option value="category">Category</option>
              </select>
            </div>
            <div className="col-md-1">
              <label className="form-label">Order</label>
              <button
                className="btn btn-outline-secondary w-100"
                onClick={() => setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')}
              >
                <i className={`bi bi-sort-${sortDirection === 'asc' ? 'down' : 'up'}`}></i>
              </button>
            </div>
            <div className="col-md-2">
              <label className="form-label">Actions</label>
              <div className="btn-group w-100">
                <button
                  className="btn btn-success btn-sm"
                  onClick={handleSelectAllCompatible}
                  disabled={compatibleCalculations.length === 0}
                >
                  Select All
                </button>
                <button
                  className="btn btn-danger btn-sm"
                  onClick={handleClearAll}
                  disabled={selectedCalculations.length === 0}
                >
                  Clear
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Summary */}
      <div className="row mb-3">
        <div className="col-12">
          <div className="d-flex justify-content-between align-items-center">
            <small className="text-muted">
              Showing {compatibleCalculations.length + incompatibleCalculations.length} calculations
              ({compatibleCalculations.length} compatible, {incompatibleCalculations.length} incompatible)
            </small>
            <span className="badge bg-primary">
              {selectedCalculations.length} Selected
            </span>
          </div>
        </div>
      </div>

      {/* Selected Calculations */}
      {selectedCalculations.length > 0 && (
        <div className="alert alert-info mb-3">
          <strong>Selected Calculations ({selectedCalculations.length}):</strong>
          <div className="mt-2">
            {selectedCalculations.map(calc => {
              const availableCalc = availableCalculations.find(ac => ac.id === calc.calculation_id);
              const displayName = calc.display_name || availableCalc?.name || `Calculation ${calc.calculation_id}`;
              
              let badgeClass = 'bg-secondary';
              let icon = 'bi-question-circle';
              if (availableCalc) {
                const displayType = getAvailableCalculationDisplayType(availableCalc);
                if (displayType.includes('User Defined')) {
                  badgeClass = 'bg-primary';
                  icon = 'bi-person-gear';
                } else if (displayType === 'CDI Var') {
                  badgeClass = 'bg-info text-dark';
                  icon = 'bi-database';
                } else if (displayType === 'System SQL') {
                  badgeClass = 'bg-warning text-dark';
                  icon = 'bi-code-square';
                } else if (displayType === 'Raw Field') {
                  badgeClass = 'bg-info';
                  icon = 'bi-file-text';
                } else if (displayType === 'Dependent') {
                  badgeClass = 'bg-light text-dark';
                  icon = 'bi-arrow-repeat';
                }
              }
              
              return (
                <span 
                  key={calc.calculation_id}
                  className={`badge ${badgeClass} me-1 mb-1`}
                  title={availableCalc ? getAvailableCalculationDisplayType(availableCalc) : 'Unknown calculation type'}
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

      {/* Calculations Table */}
      <div className="card">
        <div className="card-body p-0">
          <div className="table-responsive">
            <table className="table table-hover mb-0">
              <thead className="table-light">
                <tr>
                  <th style={{ width: '40px' }}>
                    <input
                      type="checkbox"
                      className="form-check-input"
                      checked={compatibleCalculations.length > 0 && compatibleCalculations.every(calc => isCalculationSelected(calc))}
                      onChange={() => {
                        const allSelected = compatibleCalculations.every(calc => isCalculationSelected(calc));
                        if (allSelected) {
                          handleClearAll();
                        } else {
                          handleSelectAllCompatible();
                        }
                      }}
                    />
                  </th>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Category</th>
                  <th>Source</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {/* Compatible Calculations */}
                {compatibleCalculations.map(calc => {
                  const isSelected = isCalculationSelected(calc);
                  const displayType = getAvailableCalculationDisplayType(calc);
                  const isUser = isUserDefinedCalculation(calc);
                  const isSystem = isSystemSqlCalculation(calc);
                  const isStatic = isStaticFieldCalculation(calc);
                  
                  let typeIcon = 'bi-question-circle';
                  let typeBadgeClass = 'bg-secondary';
                  
                  if (isUser) {
                    typeIcon = 'bi-person-gear';
                    typeBadgeClass = 'bg-primary';
                  } else if (isSystem) {
                    const isCDIVar = displayType === 'CDI Var';
                    typeIcon = isCDIVar ? 'bi-database' : 'bi-code-square';
                    typeBadgeClass = isCDIVar ? 'bg-info text-dark' : 'bg-warning text-dark';
                  } else if (isStatic) {
                    typeIcon = 'bi-file-text';
                    typeBadgeClass = 'bg-info';
                  }

                  let sourceDisplay = '';
                  if (isUser && calc.source_model && calc.source_field) {
                    sourceDisplay = `${calc.source_model}.${calc.source_field}`;
                  } else if (isSystem) {
                    sourceDisplay = 'Custom SQL';
                  } else if (isStatic) {
                    const parsed = parseCalculationId(calc.id);
                    sourceDisplay = parsed.identifier;
                  }

                  return (
                    <tr 
                      key={calc.id} 
                      className={`${isSelected ? 'table-primary' : ''} cursor-pointer`}
                      onClick={() => handleCalculationToggle(calc)}
                    >
                      <td>
                        <input
                          type="checkbox"
                          className="form-check-input"
                          checked={isSelected}
                          onChange={() => handleCalculationToggle(calc)}
                          onClick={(e) => e.stopPropagation()}
                        />
                      </td>
                      <td>
                        <strong>{calc.name}</strong>
                        {calc.is_default && (
                          <span className="badge bg-warning text-dark ms-1" title="Default calculation">
                            <i className="bi bi-star-fill"></i>
                          </span>
                        )}
                      </td>
                      <td>
                        <span className={`badge ${typeBadgeClass}`}>
                          <i className={`bi ${typeIcon} me-1`}></i>
                          {displayType}
                        </span>
                      </td>
                      <td>
                        <span className="badge bg-light text-dark">{calc.category}</span>
                      </td>
                      <td>
                        <small className="text-muted">{sourceDisplay}</small>
                      </td>
                      <td>
                        <small className="text-muted">
                          {calc.description || 'No description available'}
                        </small>
                      </td>
                    </tr>
                  );
                })}

                {/* Incompatible Calculations (if any) */}
                {incompatibleCalculations.map(calc => {
                  const displayType = getAvailableCalculationDisplayType(calc);
                  const { reason } = getCalculationCompatibilityInfo(calc, scope);
                  
                  return (
                    <tr key={calc.id} className="table-secondary opacity-50">
                      <td>
                        <input
                          type="checkbox"
                          className="form-check-input"
                          disabled
                        />
                      </td>
                      <td>
                        <span className="text-muted">{calc.name}</span>
                        <i className="bi bi-exclamation-triangle text-warning ms-1" title="Not compatible"></i>
                      </td>
                      <td>
                        <span className="badge bg-secondary">
                          {displayType}
                        </span>
                      </td>
                      <td>
                        <span className="badge bg-light text-muted">{calc.category}</span>
                      </td>
                      <td>
                        <small className="text-muted">
                          {calc.source_model && calc.source_field ? `${calc.source_model}.${calc.source_field}` : 'Custom SQL'}
                        </small>
                      </td>
                      <td>
                        <small className="text-warning">
                          {reason || 'Not compatible with current report scope'}
                        </small>
                      </td>
                    </tr>
                  );
                })}

                {(compatibleCalculations.length === 0 && incompatibleCalculations.length === 0) && (
                  <tr>
                    <td colSpan={6} className="text-center text-muted p-4">
                      {searchTerm || selectedCategory !== 'all' || calculationType !== 'all'
                        ? 'No calculations match your search criteria.' 
                        : 'No calculations available.'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Incompatible calculations warning */}
      {scope === 'DEAL' && incompatibleCalculations.length > 0 && (
        <div className="alert alert-warning mt-3">
          <i className="bi bi-exclamation-triangle me-2"></i>
          <strong>Deal-Level Report Compatibility:</strong> {incompatibleCalculations.length} calculation(s) are not compatible with deal-level reports 
          because they would create multiple rows per deal. These are shown as disabled above.
        </div>
      )}
    </div>
  );
};

export default CalculationSelector;