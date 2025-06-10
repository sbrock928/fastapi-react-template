// frontend/features/calculations/components/SystemCalculationsTab.tsx
import React from 'react';
import type { Calculation } from '@/types/calculations';
import CalculationCard from './CalculationCard';
import FilterSection from './FilterSection';

interface SystemCalculationsTabProps {
  calculations: Calculation[];
  filteredCalculations: Calculation[];
  selectedFilter: string;
  setSelectedFilter: (filter: string) => void;
  loading: boolean;
  usage: Record<number, any>;
  onCreateSystemField: () => void;
  onCreateSystemSql: () => void;
  onPreviewSQL: (id: number) => void;
  onShowUsage: (id: number, name: string) => void;
}

const SystemCalculationsTab: React.FC<SystemCalculationsTabProps> = ({
  calculations,
  filteredCalculations,
  selectedFilter,
  setSelectedFilter,
  loading,
  usage,
  onCreateSystemField,
  onCreateSystemSql,
  onPreviewSQL,
  onShowUsage
}) => {
  // Separate calculations by type
  const systemFieldCalcs = filteredCalculations.filter(calc => calc.calculation_type === 'SYSTEM_FIELD');
  const systemSqlCalcs = filteredCalculations.filter(calc => calc.calculation_type === 'SYSTEM_SQL');

  // Dummy delete function (system calculations cannot be deleted)
  const handleDeleteAttempt = (_id: number, name: string) => {
    // This will never actually delete, just show a warning
    console.warn(`Cannot delete system calculation: ${name}`);
  };

  return (
    <div className="tab-pane fade show active">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h5 className="mb-0">System Defined Calculations</h5>
        <div className="btn-group">
          <button
            onClick={onCreateSystemField}
            className="btn btn-success"
            title="Create a new system field calculation"
          >
            <i className="bi bi-database-add me-2"></i>
            New Field Calculation
          </button>
          <button
            onClick={onCreateSystemSql}
            className="btn btn-warning"
            title="Create a new custom SQL calculation"
          >
            <i className="bi bi-code-square me-2"></i>
            New SQL Calculation
          </button>
        </div>
      </div>

      {/* Info Alert */}
      <div className="alert alert-info mb-4">
        <div className="d-flex align-items-start">
          <i className="bi bi-info-circle me-3 mt-1"></i>
          <div>
            <h6 className="alert-heading mb-2">System Calculations</h6>
            <p className="mb-2">
              System calculations are managed by administrators and provide core functionality for reports.
              They cannot be edited or deleted by users once created.
            </p>
            <ul className="mb-0">
              <li><strong>Field Calculations:</strong> Expose raw model fields for use in reports and user calculations</li>
              <li><strong>SQL Calculations:</strong> Advanced custom calculations using validated SQL queries</li>
            </ul>
          </div>
        </div>
      </div>

      <FilterSection
        selectedFilter={selectedFilter}
        onFilterChange={setSelectedFilter}
        fieldsLoading={loading}
      />

      {/* System Field Calculations Section */}
      <div className="card mb-4">
        <div className="card-header bg-success">
          <h6 className="card-title mb-0 text-white">
            <i className="bi bi-database me-2"></i>
            System Field Calculations ({systemFieldCalcs.length})
          </h6>
        </div>
        <div className="card-body">
          {loading ? (
            <div className="text-center py-4">
              <div className="spinner-border text-success" role="status">
                <span className="visually-hidden">Loading...</span>
              </div>
              <p className="mt-2 mb-0">Loading system field calculations...</p>
            </div>
          ) : (
            <>
              {systemFieldCalcs.length > 0 ? (
                <div className="row g-3">
                  {systemFieldCalcs.map((calc) => (
                    <div key={calc.id} className="col-12">
                      <CalculationCard
                        calculation={calc}
                        usage={usage[calc.id]}
                        onEdit={() => {}} // System calculations cannot be edited
                        onDelete={handleDeleteAttempt}
                        onPreviewSQL={onPreviewSQL}
                        onShowUsage={onShowUsage}
                      />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4 text-muted">
                  <i className="bi bi-database display-4 d-block mb-3"></i>
                  <h6>No System Field Calculations</h6>
                  <p className="mb-3">System field calculations provide access to raw model fields.</p>
                  <button
                    onClick={onCreateSystemField}
                    className="btn btn-success"
                  >
                    <i className="bi bi-database-add me-2"></i>
                    Create First Field Calculation
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* System SQL Calculations Section */}
      <div className="card">
        <div className="card-header bg-warning">
          <h6 className="card-title mb-0 text-dark">
            <i className="bi bi-code-square me-2"></i>
            System SQL Calculations ({systemSqlCalcs.length})
          </h6>
        </div>
        <div className="card-body">
          {loading ? (
            <div className="text-center py-4">
              <div className="spinner-border text-warning" role="status">
                <span className="visually-hidden">Loading...</span>
              </div>
              <p className="mt-2 mb-0">Loading system SQL calculations...</p>
            </div>
          ) : (
            <>
              {systemSqlCalcs.length > 0 ? (
                <div className="row g-3">
                  {systemSqlCalcs.map((calc) => (
                    <div key={calc.id} className="col-12">
                      <CalculationCard
                        calculation={calc}
                        usage={usage[calc.id]}
                        onEdit={() => {}} // System calculations cannot be edited
                        onDelete={handleDeleteAttempt}
                        onPreviewSQL={onPreviewSQL}
                        onShowUsage={onShowUsage}
                      />
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4 text-muted">
                  <i className="bi bi-code-square display-4 d-block mb-3"></i>
                  <h6>No System SQL Calculations</h6>
                  <p className="mb-3">System SQL calculations provide advanced custom logic using validated SQL.</p>
                  <button
                    onClick={onCreateSystemSql}
                    className="btn btn-warning"
                  >
                    <i className="bi bi-code-square me-2"></i>
                    Create First SQL Calculation
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Statistics Footer */}
      <div className="card bg-light mt-4">
        <div className="card-body">
          <div className="row text-center">
            <div className="col-md-3">
              <div className="h4 mb-0 text-primary">{calculations.length}</div>
              <small className="text-muted">Total System Calculations</small>
            </div>
            <div className="col-md-3">
              <div className="h4 mb-0 text-success">{systemFieldCalcs.length}</div>
              <small className="text-muted">Field Calculations</small>
            </div>
            <div className="col-md-3">
              <div className="h4 mb-0 text-warning">{systemSqlCalcs.length}</div>
              <small className="text-muted">SQL Calculations</small>
            </div>
            <div className="col-md-3">
              <div className="h4 mb-0 text-info">
                {Object.values(usage).filter(u => u?.is_in_use).length}
              </div>
              <small className="text-muted">In Active Use</small>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemCalculationsTab;