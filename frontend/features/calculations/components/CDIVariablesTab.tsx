// frontend/features/calculations/components/CDIVariablesTab.tsx
// Tab component for managing CDI Variable calculations

import React, { useState, useEffect } from 'react';
import { useToast } from '@/context/ToastContext';
import { cdiVariableApi, calculationsApi } from '@/services/calculationsApi';
import UsageModal from './UsageModal';
import type { 
  CDIVariableResponse
} from '@/types/cdi';

interface CDIVariablesTabProps {
  onRefreshNeeded?: () => void;
  onCreateVariable?: () => void;
  onEditVariable?: (variable: CDIVariableResponse) => void;
}

const CDIVariablesTab: React.FC<CDIVariablesTabProps> = ({ 
  onRefreshNeeded,
  onCreateVariable,
  onEditVariable
}) => {
  const { showToast } = useToast();

  // State management
  const [cdiVariables, setCdiVariables] = useState<CDIVariableResponse[]>([]);
  const [filteredVariables, setFilteredVariables] = useState<CDIVariableResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [variableUsage, setVariableUsage] = useState<Record<number, any>>({});

  // Usage modal states
  const [showUsageModal, setShowUsageModal] = useState<boolean>(false);
  const [selectedUsageData, setSelectedUsageData] = useState<any>(null);
  const [usageLoading, setUsageLoading] = useState<boolean>(false);

  // Load CDI variables on mount
  useEffect(() => {
    loadCDIVariables();
  }, []);

  // Filter variables when search term changes
  useEffect(() => {
    filterVariables();
  }, [cdiVariables, searchTerm]);

  // Load usage information when variables change
  useEffect(() => {
    if (cdiVariables.length > 0) {
      loadVariableUsage();
    }
  }, [cdiVariables]);

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

  const loadVariableUsage = async () => {
    const usageMap: Record<number, any> = {};
    
    for (const variable of cdiVariables) {
      try {
        // CDI variables are system calculations, so use system calculation usage endpoint
        const response = await calculationsApi.getSystemCalculationUsage(variable.id);
        usageMap[variable.id] = response.data;
      } catch (error) {
        console.error(`Error fetching usage for CDI variable ${variable.id}:`, error);
        usageMap[variable.id] = { is_in_use: false, report_count: 0, reports: [] };
      }
    }
    
    setVariableUsage(usageMap);
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
    onCreateVariable?.();
  };

  const handleEditVariable = (variable: CDIVariableResponse) => {
    onEditVariable?.(variable);
  };

  const handleDeleteVariable = async (variable: CDIVariableResponse) => {
    // Check if variable is in use before allowing deletion
    const usage = variableUsage[variable.id];
    
    if (usage?.is_in_use) {
      const reportNames = usage.reports.map((r: any) => r.report_name).join(', ');
      showToast(
        `Cannot delete CDI variable "${variable.name}" because it is currently being used in the following report templates: ${reportNames}. Please remove the variable from these reports before deleting it.`,
        'error'
      );
      return;
    }

    if (!window.confirm(`Are you sure you want to delete "${variable.name}"?`)) {
      return;
    }

    try {
      await cdiVariableApi.deleteCDIVariable(variable.id);
      showToast('CDI variable deleted successfully', 'success');
      loadCDIVariables();
      onRefreshNeeded?.();
    } catch (error: any) {
      console.error('Failed to delete CDI variable:', error);
      
      // Extract detailed error message from API response
      let errorMessage = 'Failed to delete CDI variable';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      showToast(errorMessage, 'error');
    }
  };

  const handleShowUsage = async (variable: CDIVariableResponse) => {
    setSelectedUsageData(null);
    setUsageLoading(true);
    setShowUsageModal(true);

    try {
      // Load detailed usage data for the selected variable
      const response = await calculationsApi.getSystemCalculationUsage(variable.id);
      setSelectedUsageData(response.data);
    } catch (error) {
      console.error('Failed to load usage data:', error);
      showToast('Failed to load usage data', 'error');
    } finally {
      setUsageLoading(false);
    }
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
                  {filteredVariables.map((variable) => {
                    const usage = variableUsage[variable.id];
                    return (
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
                                  className={`btn btn-sm ${usage?.is_in_use ? 'btn-outline-secondary' : 'btn-outline-danger'}`}
                                  title={usage?.is_in_use ? 'Cannot delete - variable is in use' : 'Delete CDI variable'}
                                  disabled={usage?.is_in_use}
                                >
                                  <i className="bi bi-trash"></i> {usage?.is_in_use ? 'In Use' : 'Delete'}
                                </button>

                                {/* Usage Button - Only show for tranche-level calculations */}
                                {variable.group_level === 'tranche' && (
                                  <button
                                  onClick={() => handleShowUsage(variable)}
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
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
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

      {/* Usage Modal - Keep this one since it's specific to the tab */}
      <UsageModal
        isOpen={showUsageModal}
        onClose={() => setShowUsageModal(false)}
        selectedUsageData={selectedUsageData}
        usageLoading={usageLoading}
      />
    </div>
  );
};

export default CDIVariablesTab;