import React, { useState, useEffect } from 'react';
import { FilterConditionCreate, FilterOperator, AvailableField, FilterOperatorOption } from '../../../types/reporting';

interface FilterBuilderProps {
  filterConditions: FilterConditionCreate[];
  availableFields: AvailableField[];
  onFiltersChange: (filters: FilterConditionCreate[]) => void;
}

// Filter operator configurations
const FILTER_OPERATORS: FilterOperatorOption[] = [
  {
    value: 'equals',
    label: 'Equals',
    description: 'Exact match',
    valueType: 'single',
    supportedFieldTypes: ['text', 'number', 'date', 'percentage']
  },
  {
    value: 'not_equals',
    label: 'Not Equals',
    description: 'Does not match',
    valueType: 'single',
    supportedFieldTypes: ['text', 'number', 'date', 'percentage']
  },
  {
    value: 'contains',
    label: 'Contains',
    description: 'Text contains value',
    valueType: 'single',
    supportedFieldTypes: ['text']
  },
  {
    value: 'not_contains',
    label: 'Does Not Contain',
    description: 'Text does not contain value',
    valueType: 'single',
    supportedFieldTypes: ['text']
  },
  {
    value: 'starts_with',
    label: 'Starts With',
    description: 'Text starts with value',
    valueType: 'single',
    supportedFieldTypes: ['text']
  },
  {
    value: 'ends_with',
    label: 'Ends With',
    description: 'Text ends with value',
    valueType: 'single',
    supportedFieldTypes: ['text']
  },
  {
    value: 'greater_than',
    label: 'Greater Than',
    description: 'Value is greater than',
    valueType: 'single',
    supportedFieldTypes: ['number', 'date', 'percentage']
  },
  {
    value: 'less_than',
    label: 'Less Than',
    description: 'Value is less than',
    valueType: 'single',
    supportedFieldTypes: ['number', 'date', 'percentage']
  },
  {
    value: 'greater_than_or_equal',
    label: 'Greater Than or Equal',
    description: 'Value is greater than or equal to',
    valueType: 'single',
    supportedFieldTypes: ['number', 'date', 'percentage']
  },
  {
    value: 'less_than_or_equal',
    label: 'Less Than or Equal',
    description: 'Value is less than or equal to',
    valueType: 'single',
    supportedFieldTypes: ['number', 'date', 'percentage']
  },
  {
    value: 'is_null',
    label: 'Is Empty',
    description: 'Field has no value',
    valueType: 'none',
    supportedFieldTypes: ['text', 'number', 'date', 'percentage']
  },
  {
    value: 'is_not_null',
    label: 'Is Not Empty',
    description: 'Field has a value',
    valueType: 'none',
    supportedFieldTypes: ['text', 'number', 'date', 'percentage']
  }
];

export const FilterBuilder: React.FC<FilterBuilderProps> = ({
  filterConditions,
  availableFields,
  onFiltersChange
}) => {
  const [localFilters, setLocalFilters] = useState<FilterConditionCreate[]>(filterConditions);

  useEffect(() => {
    setLocalFilters(filterConditions);
  }, [filterConditions]);

  const handleAddFilter = () => {
    const newFilter: FilterConditionCreate = {
      field_name: '',
      operator: 'equals',
      value: ''
    };
    const updatedFilters = [...localFilters, newFilter];
    setLocalFilters(updatedFilters);
    onFiltersChange(updatedFilters);
  };

  const handleRemoveFilter = (index: number) => {
    const updatedFilters = localFilters.filter((_, i) => i !== index);
    setLocalFilters(updatedFilters);
    onFiltersChange(updatedFilters);
  };

  const handleFilterChange = (index: number, updates: Partial<FilterConditionCreate>) => {
    const updatedFilters = localFilters.map((filter, i) => {
      if (i === index) {
        const updatedFilter = { ...filter, ...updates };
        
        // Reset value if operator changed to one that doesn't need a value
        const operatorConfig = FILTER_OPERATORS.find(op => op.value === updatedFilter.operator);
        if (operatorConfig?.valueType === 'none') {
          updatedFilter.value = null;
        }
        
        return updatedFilter;
      }
      return filter;
    });
    setLocalFilters(updatedFilters);
    onFiltersChange(updatedFilters);
  };

  const getAvailableOperators = (fieldType: string): FilterOperatorOption[] => {
    return FILTER_OPERATORS.filter(op => 
      op.supportedFieldTypes.includes(fieldType as any)
    );
  };

  const getSelectedField = (fieldName: string): AvailableField | undefined => {
    return availableFields.find(field => field.field_name === fieldName);
  };

  const renderValueInput = (filter: FilterConditionCreate, index: number) => {
    const operatorConfig = FILTER_OPERATORS.find(op => op.value === filter.operator);
    
    if (operatorConfig?.valueType === 'none') {
      return null;
    }

    const selectedField = getSelectedField(filter.field_name);
    const fieldType = selectedField?.field_type || 'text';

    return (
      <div className="col-md-3">
        <label className="form-label">Value</label>
        {fieldType === 'number' || fieldType === 'percentage' ? (
          <input
            type="number"
            className="form-control"
            value={filter.value as string || ''}
            onChange={(e) => handleFilterChange(index, { value: e.target.value })}
            placeholder="Enter value"
          />
        ) : fieldType === 'date' ? (
          <input
            type="date"
            className="form-control"
            value={filter.value as string || ''}
            onChange={(e) => handleFilterChange(index, { value: e.target.value })}
          />
        ) : (
          <input
            type="text"
            className="form-control"
            value={filter.value as string || ''}
            onChange={(e) => handleFilterChange(index, { value: e.target.value })}
            placeholder="Enter value"
          />
        )}
      </div>
    );
  };

  return (
    <div className="filter-builder">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h5 className="mb-0">Filter Conditions</h5>
        <button
          type="button"
          className="btn btn-outline-primary btn-sm"
          onClick={handleAddFilter}
        >
          <i className="bi bi-plus-circle me-1"></i>
          Add Filter
        </button>
      </div>

      {localFilters.length === 0 ? (
        <div className="text-muted p-3 border rounded">
          <i className="bi bi-funnel me-2"></i>
          No filters configured. Click "Add Filter" to add filter conditions.
        </div>
      ) : (
        <div className="space-y-3">
          {localFilters.map((filter, index) => {
            const selectedField = getSelectedField(filter.field_name);
            const availableOperators = selectedField 
              ? getAvailableOperators(selectedField.field_type)
              : FILTER_OPERATORS;

            return (
              <div key={index} className="card">
                <div className="card-body">
                  <div className="row g-3 align-items-end">
                    <div className="col-md-3">
                      <label className="form-label">Field</label>
                      <select
                        className="form-select"
                        value={filter.field_name}
                        onChange={(e) => handleFilterChange(index, { 
                          field_name: e.target.value,
                          operator: 'equals', // Reset operator when field changes
                          value: '' // Reset value when field changes
                        })}
                      >
                        <option value="">Select a field</option>
                        {availableFields.map((field) => (
                          <option key={field.field_name} value={field.field_name}>
                            {field.display_name}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="col-md-3">
                      <label className="form-label">Operator</label>
                      <select
                        className="form-select"
                        value={filter.operator}
                        onChange={(e) => handleFilterChange(index, { 
                          operator: e.target.value as FilterOperator,
                          value: '' // Reset value when operator changes
                        })}
                        disabled={!filter.field_name}
                      >
                        {availableOperators.map((op) => (
                          <option key={op.value} value={op.value} title={op.description}>
                            {op.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    {renderValueInput(filter, index)}

                    <div className="col-md-auto">
                      <button
                        type="button"
                        className="btn btn-outline-danger btn-sm"
                        onClick={() => handleRemoveFilter(index)}
                        title="Remove filter"
                      >
                        <i className="bi bi-trash"></i>
                      </button>
                    </div>
                  </div>

                  {selectedField && (
                    <small className="text-muted">
                      <i className="bi bi-info-circle me-1"></i>
                      {selectedField.description}
                    </small>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {localFilters.length > 0 && (
        <div className="mt-3">
          <small className="text-muted">
            <i className="bi bi-info-circle me-1"></i>
            Filters are applied with AND logic - all conditions must be met.
          </small>
        </div>
      )}
    </div>
  );
};