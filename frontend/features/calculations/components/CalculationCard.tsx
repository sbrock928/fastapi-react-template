import React from 'react';
import type { Calculation } from '@/types/calculations';

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
  return (
    <div className="card border">
      <div className="card-body">
        <div className="d-flex justify-content-between align-items-start">
          <div className="flex-grow-1">
            <div className="d-flex align-items-center gap-2 mb-2">
              <h6 className="card-title mb-0">{calculation.name}</h6>
              <span className="badge bg-primary">{calculation.aggregation_function}</span>
              <span className={`badge ${
                calculation.group_level === 'deal' ? 'bg-success' : 'bg-info'
              }`}>
                {calculation.group_level === 'deal' ? 'Deal Level' : 'Tranche Level'}
              </span>
              <span className="badge bg-secondary">{calculation.source_model}</span>
            </div>
            
            {calculation.description && (
              <p className="card-text text-muted mb-2">{calculation.description}</p>
            )}
            
            <div className="bg-light rounded p-2 mb-2">
              <small className="text-muted">
                <strong>Source:</strong> {calculation.source_model}.{calculation.source_field}
                {calculation.weight_field && (
                  <span> | <strong>Weight:</strong> {calculation.source_model}.{calculation.weight_field}</span>
                )}
              </small>
            </div>
            
            <div className="d-flex align-items-center gap-1 text-muted">
              <i className="bi bi-database"></i>
              <small>ORM-based calculation using SQLAlchemy func.{calculation.aggregation_function.toLowerCase()}</small>
            </div>
            
            {/* Usage Information */}
            {usage && (
              <div className="mt-2">
                {usage.is_in_use ? (
                  <div className="alert alert-warning py-2 mb-2">
                    <i className="bi bi-exclamation-triangle me-1"></i>
                    <small>
                      <strong>In Use:</strong> Currently used in {usage.report_count} report template(s):
                      <span className="ms-1">
                        {usage.reports.map((report: any, index: number) => (
                          <span key={report.report_id}>
                            {index > 0 && ', '}
                            <strong>{report.report_name}</strong>
                          </span>
                        ))}
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
                </small>
              </div>
            )}
          </div>
          
          <div className="btn-group">
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
                usage?.is_in_use 
                  ? 'btn-outline-secondary' 
                  : 'btn-outline-warning'
              }`}
              title={
                usage?.is_in_use 
                  ? 'Cannot edit - calculation is in use'
                  : 'Edit calculation'
              }
              disabled={usage?.is_in_use}
            >
              <i className="bi bi-pencil"></i> Edit
            </button>
            <button
              onClick={() => onDelete(calculation.id, calculation.name)}
              className={`btn btn-sm ${
                usage?.is_in_use 
                  ? 'btn-outline-secondary' 
                  : 'btn-outline-danger'
              }`}
              title={
                usage?.is_in_use 
                  ? 'Cannot delete - calculation is in use'
                  : 'Delete calculation'
              }
              disabled={usage?.is_in_use}
            >
              <i className="bi bi-trash"></i> Delete
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
      </div>
    </div>
  );
};

export default CalculationCard;