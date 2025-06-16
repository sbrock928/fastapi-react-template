// frontend/features/calculations/components/CDIVariablesTab.tsx
// Tab component for managing CDI Variable calculations

import React, { useState, useEffect } from 'react';
import { useToast } from '@/context/ToastContext';
import { cdiVariableApi } from '@/services/calculationsApi';
import CDIVariableModal from './CDIVariableModal';
import type { 
  CDIVariableResponse
} from '@/types/cdi';

interface CDIVariablesTabProps {
  onRefreshNeeded?: () => void;
}

const CDIVariablesTab: React.FC<CDIVariablesTabProps> = ({ onRefreshNeeded }) => {
  const { showToast } = useToast();

  // State management
  const [cdiVariables, setCdiVariables] = useState<CDIVariableResponse[]>([]);
  const [filteredVariables, setFilteredVariables] = useState<CDIVariableResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingVariable, setEditingVariable] = useState<CDIVariableResponse | null>(null);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');

  // Load CDI variables on mount
  useEffect(() => {
    loadCDIVariables();
  }, []);

  // Filter variables when search term changes
  useEffect(() => {
    filterVariables();
  }, [cdiVariables, searchTerm]);

  const loadCDIVariables = async () => {
    try {
      setLoading(true);
      const response = await cdiVariableApi.getAllCDIVariables();
      setCdiVariables(response.data);
    } catch (error) {
      console.error('Failed to load CDI variables:', error);
      showToast('Failed to load CDI variables', 'error');
    } finally {
      setLoading(false);
    }
  };

  const filterVariables = () => {
    let filtered = cdiVariables;

    // Filter by search term
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      filtered = filtered.filter(variable =>
        variable.name.toLowerCase().includes(search) ||
        variable.description?.toLowerCase().includes(search) ||
        variable.variable_pattern.toLowerCase().includes(search) ||
        variable.result_column_name.toLowerCase().includes(search)
      );
    }

    setFilteredVariables(filtered);
  };

  const handleCreateVariable = () => {
    setEditingVariable(null);
    setModalMode('create');
    setShowModal(true);
  };

  const handleEditVariable = (variable: CDIVariableResponse) => {
    setEditingVariable(variable);
    setModalMode('edit');
    setShowModal(true);
  };

  const handleDeleteVariable = async (variable: CDIVariableResponse) => {
    if (!window.confirm(`Are you sure you want to delete "${variable.name}"?`)) {
      return;
    }

    try {
      await cdiVariableApi.deleteCDIVariable(variable.id);
      showToast('CDI variable deleted successfully', 'success');
      loadCDIVariables();
      onRefreshNeeded?.();
    } catch (error) {
      console.error('Failed to delete CDI variable:', error);
      showToast('Failed to delete CDI variable', 'error');
    }
  };

  const handleVariableSaved = () => {
    loadCDIVariables();
    onRefreshNeeded?.();
    setShowModal(false);
  };

  return (
    <div className="tab-pane fade show active">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h5 className="mb-0">CDI Variable Calculations</h5>
        <button
          onClick={handleCreateVariable}
          className="btn btn-primary"
          title="Create a new CDI variable calculation"
        >
          <i className="bi bi-diagram-3 me-2"></i>
          New CDI Variable
        </button>
      </div>

      {/* Info Alert */}
      <div className="alert alert-info mb-4">
        <div className="d-flex align-items-start">
          <i className="bi bi-info-circle me-3 mt-1"></i>
          <div>
            <h6 className="alert-heading mb-2">CDI Variable Calculations</h6>
            <p className="mb-2">
              CDI (Credit Data Interface) variables allow you to extract and map specific financial metrics 
              from CDI reporting data based on variable patterns and tranche mappings.
            </p>
            <ul className="mb-0">
              <li><strong>Variable Patterns:</strong> Define the naming pattern for CDI variables (e.g., #RPT_RRI_{'{tranche_suffix}'})</li>
              <li><strong>Tranche Mappings:</strong> Map tranche suffixes to specific tranche IDs for data extraction</li>
              <li><strong>Dynamic SQL:</strong> Automatically generates SQL queries based on patterns and mappings</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Search and Filter Controls */}
      <div className="row mb-3">
        <div className="col-md-4">
          <input
            type="text"
            className="form-control"
            placeholder="Search CDI variables..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="col-md-5">
          <div className="text-muted small d-flex align-items-center">
            <i className="bi bi-info-circle me-2"></i>
            Showing {filteredVariables.length} of {cdiVariables.length} CDI variables
          </div>
        </div>
      </div>

      {/* CDI Variables List */}
      <div className="card">
        <div className="card-header bg-primary">
          <h6 className="card-title mb-0 text-white">
            <i className="bi bi-diagram-3 me-2"></i>
            CDI Variable Calculations ({filteredVariables.length})
          </h6>
        </div>
        <div className="card-body">
          {loading ? (
            <div className="text-center py-4">
              <div className="spinner-border text-primary" role="status">
                <span className="visually-hidden">Loading...</span>
              </div>
              <p className="mt-2 mb-0">Loading CDI variables...</p>
            </div>
          ) : (
            <>
              {filteredVariables.length > 0 ? (
                <div className="row g-3">
                  {filteredVariables.map((variable) => (
                    <div key={variable.id} className="col-12">
                      <div className="card border">
                        <div className="card-body">
                          <div className="d-flex justify-content-between align-items-start">
                            <div className="flex-grow-1">
                              <div className="d-flex align-items-center gap-2 mb-2">
                                <h6 className="card-title mb-0 d-flex align-items-center">
                                  <i className="bi bi-diagram-3 me-2"></i>
                                  {variable.name}
                                </h6>
                                <span className={`badge ${variable.group_level === 'deal' ? 'bg-info' : 'bg-success'}`}>
                                  {variable.group_level === 'deal' ? 'Deal Level' : 'Tranche Level'}
                                </span>
                                {variable.group_level === 'tranche' && (
                                  <span className="badge bg-light text-dark">
                                    {Object.keys(variable.tranche_mappings).length} tranche types
                                  </span>
                                )}
                              </div>
                              
                              {variable.description && (
                                <p className="card-text text-muted mb-2">{variable.description}</p>
                              )}
                              
                              <div className="bg-light rounded p-2 mb-2">
                                <small className="text-muted">
                                  <strong>Pattern:</strong> {variable.variable_pattern}
                                  <span className="ms-3">
                                    <strong>Result Column:</strong> {variable.result_column_name}
                                  </span>
                                </small>
                              </div>

                              {/* Tranche Mappings - Only show for tranche-level calculations */}
                              {variable.group_level === 'tranche' && Object.keys(variable.tranche_mappings).length > 0 && (
                                <div className="mb-2">
                                  <small className="text-muted">
                                    <strong>Tranche Mappings:</strong>
                                  </small>
                                  <div className="mt-1">
                                    {Object.entries(variable.tranche_mappings).map(([suffix, trancheIds]) => (
                                      <span key={suffix} className="badge bg-secondary me-1 mb-1">
                                        {suffix}: {trancheIds.join(', ')}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}
                              
                              {variable.created_at && (
                                <div className="text-muted mt-2">
                                  <small>
                                    Created: {new Date(variable.created_at).toLocaleString()}
                                    {variable.created_by && (
                                      <span className="ms-3">by {variable.created_by}</span>
                                    )}
                                  </small>
                                </div>
                              )}
                            </div>
                            
                            <div className="btn-group-vertical">
                              <button
                                onClick={() => handleEditVariable(variable)}
                                className="btn btn-outline-warning btn-sm"
                                title="Edit CDI variable"
                              >
                                <i className="bi bi-pencil"></i> Edit
                              </button>
                              
                              <button
                                onClick={() => handleDeleteVariable(variable)}
                                className="btn btn-outline-danger btn-sm"
                                title="Delete CDI variable"
                              >
                                <i className="bi bi-trash"></i> Delete
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-4 text-muted">
                  <i className="bi bi-diagram-3 display-4 d-block mb-3"></i>
                  <h6>No CDI Variables Found</h6>
                  {searchTerm ? (
                    <p className="mb-3">No CDI variables match your current search criteria. Try adjusting your search term.</p>
                  ) : (
                    <p className="mb-3">CDI variables provide dynamic mapping of financial metrics from CDI reporting data.</p>
                  )}
                  <button
                    onClick={handleCreateVariable}
                    className="btn btn-primary"
                  >
                    <i className="bi bi-diagram-3 me-2"></i>
                    Create First CDI Variable
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* CDI Variable Modal */}
      <CDIVariableModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        onSave={handleVariableSaved}
        editingVariable={editingVariable}
        mode={modalMode}
      />
    </div>
  );
};

export default CDIVariablesTab;