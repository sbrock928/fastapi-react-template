import React, { useState, useEffect } from 'react';
import { reportsApi } from '@/services/api';
import { useToast } from '@/context/ToastContext';
import type { ColumnDefinition } from '@/types';

interface ColumnSelectorProps {
  reportScope: 'DEAL' | 'TRANCHE';
  selectedColumns: string[];
  onColumnToggle: (columnKey: string) => void;
  onSelectDefaults: () => void;
  onSelectAll: () => void;
  onSelectNone: () => void;
}

const ColumnSelector: React.FC<ColumnSelectorProps> = ({
  reportScope,
  selectedColumns,
  onColumnToggle,
  onSelectDefaults,
  onSelectAll,
  onSelectNone
}) => {
  const { showToast } = useToast();
  const [columnCategories, setColumnCategories] = useState<Record<string, ColumnDefinition[]>>({});
  const [loading, setLoading] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['Identification', 'Deal Information']));

  // Load available columns when scope changes
  useEffect(() => {
    loadAvailableColumns();
  }, [reportScope]);

  const loadAvailableColumns = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/reports/columns/${reportScope.toLowerCase()}`);
      const data = await response.json();
      setColumnCategories(data);
    } catch (error) {
      console.error('Error loading columns:', error);
      showToast('Error loading available columns', 'error');
    } finally {
      setLoading(false);
    }
  };

  const toggleCategory = (category: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(category)) {
      newExpanded.delete(category);
    } else {
      newExpanded.add(category);
    }
    setExpandedCategories(newExpanded);
  };

  const selectAllInCategory = (category: string) => {
    const categoryColumns = columnCategories[category] || [];
    categoryColumns.forEach(col => {
      if (!selectedColumns.includes(col.key)) {
        onColumnToggle(col.key);
      }
    });
  };

  const deselectAllInCategory = (category: string) => {
    const categoryColumns = columnCategories[category] || [];
    categoryColumns.forEach(col => {
      if (selectedColumns.includes(col.key)) {
        onColumnToggle(col.key);
      }
    });
  };

  const getColumnIcon = (columnType: string) => {
    switch (columnType) {
      case 'basic': return 'bi-database';
      case 'calculated': return 'bi-calculator';
      case 'aggregated': return 'bi-bar-chart';
      default: return 'bi-info-circle';
    }
  };

  const getDataTypeIcon = (dataType: string) => {
    switch (dataType) {
      case 'currency': return 'bi-currency-dollar';
      case 'percentage': return 'bi-percent';
      case 'date': return 'bi-calendar';
      case 'number': return 'bi-123';
      default: return 'bi-type';
    }
  };

  if (loading) {
    return (
      <div className="text-center py-4">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
        <p className="mt-2">Loading available columns...</p>
      </div>
    );
  }

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h5 className="mb-0">Select Report Columns</h5>
        <div className="btn-group btn-group-sm">
          <button
            type="button"
            className="btn btn-outline-primary"
            onClick={onSelectDefaults}
          >
            <i className="bi bi-star"></i> Defaults
          </button>
          <button
            type="button"
            className="btn btn-outline-success"
            onClick={onSelectAll}
          >
            <i className="bi bi-check-all"></i> All
          </button>
          <button
            type="button"
            className="btn btn-outline-secondary"
            onClick={onSelectNone}
          >
            <i className="bi bi-x-square"></i> None
          </button>
        </div>
      </div>

      <div className="alert alert-info">
        <i className="bi bi-info-circle me-2"></i>
        Select the columns and calculations to include in your {reportScope.toLowerCase()}-level report.
        <strong> Selected: {selectedColumns.length} columns</strong>
      </div>

      <div className="accordion" id="columnAccordion">
        {Object.entries(columnCategories).map(([category, columns]) => {
          const isExpanded = expandedCategories.has(category);
          const selectedInCategory = columns.filter(col => selectedColumns.includes(col.key)).length;
          
          return (
            <div key={category} className="accordion-item">
              <h2 className="accordion-header">
                <button
                  className={`accordion-button ${!isExpanded ? 'collapsed' : ''}`}
                  type="button"
                  onClick={() => toggleCategory(category)}
                >
                  <div className="d-flex justify-content-between align-items-center w-100 me-2">
                    <span>
                      <strong>{category}</strong>
                      <span className="ms-2 badge bg-secondary">
                        {selectedInCategory} of {columns.length}
                      </span>
                    </span>
                    <div className="btn-group btn-group-sm me-2" onClick={(e) => e.stopPropagation()}>
                      <button
                        type="button"
                        className="btn btn-outline-primary btn-sm"
                        onClick={() => selectAllInCategory(category)}
                        title="Select all in category"
                      >
                        <i className="bi bi-check-all"></i>
                      </button>
                      <button
                        type="button"
                        className="btn btn-outline-secondary btn-sm"
                        onClick={() => deselectAllInCategory(category)}
                        title="Deselect all in category"
                      >
                        <i className="bi bi-x-square"></i>
                      </button>
                    </div>
                  </div>
                </button>
              </h2>
              <div className={`accordion-collapse collapse ${isExpanded ? 'show' : ''}`}>
                <div className="accordion-body">
                  <div className="row">
                    {columns
                      .sort((a, b) => a.sort_order - b.sort_order)
                      .map(column => (
                        <div key={column.key} className="col-md-6 mb-2">
                          <div className={`p-2 border rounded ${selectedColumns.includes(column.key) ? 'border-primary bg-light' : ''}`}>
                            <div className="form-check">
                              <input
                                className="form-check-input"
                                type="checkbox"
                                id={`column-${column.key}`}
                                checked={selectedColumns.includes(column.key)}
                                onChange={() => onColumnToggle(column.key)}
                              />
                              <label className="form-check-label w-100" htmlFor={`column-${column.key}`}>
                                <div className="d-flex justify-content-between align-items-start">
                                  <div className="flex-grow-1">
                                    <div className="fw-bold d-flex align-items-center">
                                      <i className={`bi ${getColumnIcon(column.column_type)} me-1`}></i>
                                      {column.label}
                                      {column.is_default && (
                                        <span className="badge bg-warning text-dark ms-1" style={{ fontSize: '0.6rem' }}>
                                          Default
                                        </span>
                                      )}
                                    </div>
                                    <div className="small text-muted">
                                      {column.description}
                                    </div>
                                  </div>
                                  <div className="text-end ms-2">
                                    <i 
                                      className={`bi ${getDataTypeIcon(column.data_type)} text-muted`}
                                      title={column.data_type}
                                    ></i>
                                  </div>
                                </div>
                              </label>
                            </div>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {selectedColumns.length === 0 && (
        <div className="alert alert-warning mt-3">
          <i className="bi bi-exclamation-triangle me-2"></i>
          Please select at least one column for your report.
        </div>
      )}
    </div>
  );
};

export default ColumnSelector;