// frontend/features/calculations/components/CalculationCard.tsx
import React from 'react';
import type { Calculation } from '@/types/calculations';
import { 
  getCalculationDisplayType, 
  getCalculationSourceDescription, 
  getCalculationCategory,
  isSystemCalculation,
  isUserDefinedCalculation,
  isSystemFieldCalculation,
  isSystemSqlCalculation
} from '@/types/calculations';

interface CalculationCardProps {
  calculation: Calculation;
  usage: any;
  onEdit: (calc: Calculation) => void;
  onDelete: (id: number, name: string) => void;
  onPreviewSQL: (id: number) => void;
  onShowUsage: (id: number, name: string) => void;
}

const CalculationCard: React.FC<CalculationCardProps> = ({
  calculation,
  usage,
  onEdit,
  onDelete,
  onPreviewSQL,
  onShowUsage
}) => {
  const isSystem = isSystemCalculation(calculation);
  const displayType = getCalculationDisplayType(calculation);
  const sourceDescription = getCalculationSourceDescription(calculation);
  const category = getCalculationCategory(calculation);

  const getCalculationTypeIcon = () => {
    if (isUserDefinedCalculation(calculation)) {
      return 'bi-person-gear';
    } else if (isSystemFieldCalculation(calculation)) {
      return 'bi-database';
    } else if (isSystemSqlCalculation(calculation)) {
      return 'bi-code-square';
    }
    return 'bi-question-circle';
  };

  const getCalculationTypeBadge = () => {
    if (isUserDefinedCalculation(calculation)) {
      return 'bg-primary';
    } else if (isSystemFieldCalculation(calculation)) {
      return 'bg-success';
    } else if (isSystemSqlCalculation(calculation)) {
      return 'bg-warning text-dark';
    }
    return 'bg-secondary';
  };

  const getGroupLevelBadge = () => {
    return calculation.group_level === 'deal' ? 'bg-info' : 'bg-secondary';
  };

  return (
    <div className={`card border ${isSystem ? 'border-success' : 'border-primary'}`}>
      <div className="card-body">
        <div className="d-flex justify-content-between align-items-start">
          <div className="flex-grow-1">
            <div className="d-flex align-items-center gap-2 mb-2">
              <h6 className="card-title mb-0 d-flex align-items-center">
                <i className={`bi ${getCalculationTypeIcon()} me-2`}></i>
                {calculation.name}
              </h6>
              <span className={`badge ${getCalculationTypeBadge()}`}>
                {displayType}
              </span>
              <span className={`badge ${getGroupLevelBadge()}`}>
                {calculation.group_level === 'deal' ? 'Deal Level' : 'Tranche Level'}
              </span>
              <span className="badge bg-light text-dark">{category}</span>
              {isSystem && (
                <span className="badge bg-success">
                  <i className="bi bi-shield-check me-1"></i>
                  System Managed
                </span>
              )}
            </div>
            
            {calculation.description && (
              <p className="card-text text-muted mb-2">{calculation.description}</p>
            )}
            
            <div className="bg-light rounded p-2 mb-2">
              <small className="text-muted">
                <strong>Source:</strong> {sourceDescription}
                {/* Show additional details based on calculation type */}
                {isUserDefinedCalculation(calculation) && calculation.weight_field && (
                  <span> | <strong>Weight:</strong> {calculation.source_model}.{calculation.weight_field}</span>
                )}
                {isSystemSqlCalculation(calculation) && (
                  <span> | <strong>Returns:</strong> {calculation.result_column_name}</span>
                )}
              </small>
            </div>
            
            {/* System-specific information */}
            {isSystemSqlCalculation(calculation) && (
              <div className="d-flex align-items-center gap-1 text-muted mb-2">
                <i className="bi bi-code-square"></i>
                <small>Custom SQL calculation with validated query</small>
              </div>
            )}
            
            {isSystemFieldCalculation(calculation) && (
              <div className="d-flex align-items-center gap-1 text-muted mb-2">
                <i className="bi bi-database"></i>
                <small>Raw field from {calculation.source_model} model ({calculation.field_type})</small>
              </div>
            )}
            
            {isUserDefinedCalculation(calculation) && (
              <div className="d-flex align-items-center gap-1 text-muted mb-2">
                <i className="bi bi-calculator"></i>
                <small>User-created aggregated calculation using {calculation.aggregation_function}</small>
              </div>
            )}
            
            {/* Usage Information */}
            {usage && (
              <div className="mt-2">
                {usage.is_in_use ? (
                  <div className="alert alert-warning py-2 mb-2">
                    <i className="bi bi-exclamation-triangle me-1"></i>
                    <small>
                      <strong>In Use:</strong> Currently used in {usage.report_count} report template(s):
                      <span className="ms-1">
                        {usage.reports.slice(0, 3).map((report: any, index: number) => (
                          <span key={report.report_id}>
                            {index > 0 && ', '}
                            <strong>{report.report_name}</strong>
                          </span>
                        ))}
                        {usage.reports.length > 3 && <span>, and {usage.reports.length - 3} more...</span>}
                      </span>
                    </small>
                  </div>
                ) : (
                  <div className="text-muted">
                    <small>
                      <i className="bi bi-check-circle me-1"></i>
                      Not currently used in any report templates
                    </small>
                  </div>
                )}
              </div>
            )}
            
            {calculation.created_at && (
              <div className="text-muted mt-2">
                <small>
                  Created: {new Date(calculation.created_at).toLocaleString()}
                  {calculation.updated_at && calculation.updated_at !== calculation.created_at && (
                    <span className="ms-3">Updated: {new Date(calculation.updated_at).toLocaleString()}</span>
                  )}
                  {calculation.created_by && (
                    <span className="ms-3">by {calculation.created_by}</span>
                  )}
                </small>
              </div>
            )}
          </div>
          
          <div className="btn-group-vertical">
            <button
              onClick={() => onPreviewSQL(calculation.id)}
              className="btn btn-outline-info btn-sm"
              title="Preview SQL"
            >
              <i className="bi bi-eye"></i> SQL
            </button>
            
            <button
              onClick={() => onEdit(calculation)}
              className={`btn btn-sm ${
                isSystem
                  ? 'btn-outline-secondary' 
                  : usage?.is_in_use 
                    ? 'btn-outline-secondary' 
                    : 'btn-outline-warning'
              }`}
              title={
                isSystem
                  ? 'System calculations cannot be edited'
                  : usage?.is_in_use 
                    ? 'Cannot edit - calculation is in use'
                    : 'Edit calculation'
              }
              disabled={isSystem || usage?.is_in_use}
            >
              <i className="bi bi-pencil"></i> 
              {isSystem ? 'Protected' : 'Edit'}
            </button>
            
            <button
              onClick={() => onDelete(calculation.id, calculation.name)}
              className={`btn btn-sm ${
                isSystem
                  ? 'btn-outline-secondary' 
                  : usage?.is_in_use 
                    ? 'btn-outline-secondary' 
                    : 'btn-outline-danger'
              }`}
              title={
                isSystem
                  ? 'System calculations cannot be deleted'
                  : usage?.is_in_use 
                    ? 'Cannot delete - calculation is in use'
                    : 'Delete calculation'
              }
              disabled={isSystem || usage?.is_in_use}
            >
              <i className="bi bi-trash"></i> 
              {isSystem ? 'Protected' : 'Delete'}
            </button>
            
            <button
              onClick={() => onShowUsage(calculation.id, calculation.name)}
              className="btn btn-outline-secondary btn-sm"
              title="View Usage Details"
            >
              <i className="bi bi-bar-chart"></i> 
              {usage?.report_count > 0 && (
                <span className="badge bg-warning text-dark ms-1">
                  {usage.report_count}
                </span>
              )}
            </button>
          </div>
        </div>

        {/* System Calculation Special Notices */}
        {isSystem && (
          <div className="mt-3 p-2 bg-success bg-opacity-10 border border-success rounded">
            <div className="d-flex align-items-center">
              <i className="bi bi-shield-check text-success me-2"></i>
              <small className="text-success">
                <strong>System Managed:</strong> This calculation is protected and cannot be modified by users.
                {isSystemSqlCalculation(calculation) && (
                  <span> Contains validated custom SQL logic.</span>
                )}
                {isSystemFieldCalculation(calculation) && (
                  <span> Provides direct access to model field data.</span>
                )}
              </small>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CalculationCard;