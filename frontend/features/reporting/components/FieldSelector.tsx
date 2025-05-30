import React, { useState, useMemo } from 'react';
import { AvailableField, ReportField } from '../../../types/reporting';

interface FieldSelectorProps {
  scope: 'DEAL' | 'TRANCHE';
  availableFields: AvailableField[];
  selectedFields: ReportField[];
  onFieldsChange: (fields: ReportField[]) => void;
  loading?: boolean;
}

const FieldSelector: React.FC<FieldSelectorProps> = ({
  scope,
  availableFields,
  selectedFields,
  onFieldsChange,
  loading = false
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  // Group fields by category
  const fieldsByCategory = useMemo(() => {
    const grouped: Record<string, AvailableField[]> = {};
    availableFields.forEach(field => {
      if (!grouped[field.category]) {
        grouped[field.category] = [];
      }
      grouped[field.category].push(field);
    });
    return grouped;
  }, [availableFields]);

  const categories = useMemo(() => {
    return Object.keys(fieldsByCategory).sort();
  }, [fieldsByCategory]);

  // Filter fields based on search and category
  const filteredFields = useMemo(() => {
    let fields = availableFields;

    // Filter by category
    if (selectedCategory !== 'all') {
      fields = fields.filter(field => field.category === selectedCategory);
    }

    // Filter by search term
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      fields = fields.filter(field => 
        field.display_name.toLowerCase().includes(search) ||
        field.field_name.toLowerCase().includes(search) ||
        field.description?.toLowerCase().includes(search)
      );
    }

    return fields;
  }, [availableFields, selectedCategory, searchTerm]);

  // Check if a field is selected
  const isFieldSelected = (fieldName: string): boolean => {
    return selectedFields.some(field => field.field_name === fieldName);
  };

  // Handle field toggle
  const handleFieldToggle = (availableField: AvailableField) => {
    const isSelected = isFieldSelected(availableField.field_name);

    if (isSelected) {
      // Remove field
      const updatedFields = selectedFields.filter(
        field => field.field_name !== availableField.field_name
      );
      onFieldsChange(updatedFields);
    } else {
      // Add field
      const newField: ReportField = {
        field_name: availableField.field_name,
        display_name: availableField.display_name,
        field_type: availableField.field_type,
        is_required: false
      };
      onFieldsChange([...selectedFields, newField]);
    }
  };

  // Handle select all defaults
  const handleSelectDefaults = () => {
    const defaultFields = availableFields
      .filter(field => field.is_default)
      .map(field => ({
        field_name: field.field_name,
        display_name: field.display_name,
        field_type: field.field_type,
        is_required: false
      }));
    onFieldsChange(defaultFields);
  };

  // Handle select all
  const handleSelectAll = () => {
    const allFields = availableFields.map(field => ({
      field_name: field.field_name,
      display_name: field.display_name,
      field_type: field.field_type,
      is_required: false
    }));
    onFieldsChange(allFields);
  };

  // Handle clear all
  const handleClearAll = () => {
    onFieldsChange([]);
  };

  if (loading) {
    return (
      <div className="text-center p-4">
        <div className="spinner-border" role="status">
          <span className="visually-hidden">Loading fields...</span>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header and Controls */}
      <div className="row mb-3">
        <div className="col-md-6">
          <h5>Select Fields for {scope} Report</h5>
          <p className="text-muted">
            Choose which fields to include in your report. Default fields are pre-selected.
          </p>
        </div>
        <div className="col-md-6">
          <div className="d-flex gap-2 justify-content-end">
            <button
              className="btn btn-outline-primary btn-sm"
              onClick={handleSelectDefaults}
              disabled={availableFields.length === 0}
            >
              <i className="bi bi-star"></i> Select Defaults
            </button>
            <button
              className="btn btn-outline-secondary btn-sm"
              onClick={handleSelectAll}
              disabled={availableFields.length === 0}
            >
              Select All
            </button>
            <button
              className="btn btn-outline-danger btn-sm"
              onClick={handleClearAll}
              disabled={selectedFields.length === 0}
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
            placeholder="Search fields..."
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

      {/* Selected Fields Summary */}
      {selectedFields.length > 0 && (
        <div className="alert alert-info mb-3">
          <strong>Selected Fields ({selectedFields.length}):</strong>
          <div className="mt-2">
            {selectedFields.map(field => (
              <span key={field.field_name} className="badge bg-primary me-1 mb-1">
                {field.display_name}
                <button
                  type="button"
                  className="btn-close btn-close-white ms-1"
                  style={{ fontSize: '0.7em' }}
                  onClick={() => handleFieldToggle(availableFields.find(f => f.field_name === field.field_name)!)}
                ></button>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Available Fields List */}
      <div className="row">
        {filteredFields.length === 0 ? (
          <div className="col-12">
            <div className="text-center text-muted p-4">
              {searchTerm || selectedCategory !== 'all' 
                ? 'No fields match your search criteria.' 
                : 'No fields available.'}
            </div>
          </div>
        ) : (
          filteredFields.map(field => {
            const isSelected = isFieldSelected(field.field_name);
            return (
              <div key={field.field_name} className="col-md-6 col-lg-4 mb-3">
                <div 
                  className={`card h-100 ${isSelected ? 'border-primary bg-light' : ''}`}
                  style={{ cursor: 'pointer' }}
                  onClick={() => handleFieldToggle(field)}
                >
                  <div className="card-body">
                    <div className="d-flex justify-content-between align-items-start mb-2">
                      <h6 className="card-title mb-0">
                        {field.display_name}
                        {field.is_default && (
                          <span className="badge bg-warning text-dark ms-1" title="Default field">
                            <i className="bi bi-star-fill"></i>
                          </span>
                        )}
                      </h6>
                      <input
                        type="checkbox"
                        className="form-check-input"
                        checked={isSelected}
                        onChange={() => handleFieldToggle(field)}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </div>
                    <div className="text-muted small mb-2">
                      <span className="badge bg-secondary me-1">{field.category}</span>
                      <span className="badge bg-info">{field.field_type}</span>
                    </div>
                    <p className="card-text small text-muted">
                      <strong>Field:</strong> {field.field_name}
                    </p>
                    {field.description && (
                      <p className="card-text small">
                        {field.description}
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
            Showing {filteredFields.length} of {availableFields.length} available fields. 
            {selectedFields.length > 0 && ` ${selectedFields.length} selected.`}
          </small>
        </div>
      </div>
    </div>
  );
};

export default FieldSelector;