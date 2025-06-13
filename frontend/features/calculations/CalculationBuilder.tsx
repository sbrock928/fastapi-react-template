// frontend/features/calculations/CalculationBuilder.tsx
// Main component for managing both user and system calculations

import React, { useState, useEffect } from 'react';
import { useToast } from '@/context/ToastContext';
import { calculationsApi } from '@/services/calculationsApi';
import { useUnifiedCalculations } from './hooks/useUnifiedCalculations';
import { useCalculationConfig, useCalculationForm } from './hooks/useCalculationConfig';
import type { UserCalculation, SystemCalculation } from '@/types/calculations';

// Components
import FilterSection from './components/FilterSection';
import CalculationCard from './components/CalculationCard';
import CalculationModal from './components/CalculationModal';
import SystemCalculationsTab from './components/SystemCalculationsTab';
import SqlPreviewModal from './components/SqlPreviewModal';
import UsageModal from './components/UsageModal';

// Constants
import { SAMPLE_PREVIEW_PARAMS } from './constants/calculationConstants';

type CalculationTab = 'user-defined' | 'system-defined';

// Define types for calculations that might have usage_info
type CalculationWithUsage = (UserCalculation | SystemCalculation) & {
  usage_info?: {
    calculation_id: number;
    calculation_name: string;
    is_in_use: boolean;
    report_count: number;
    reports: any[];
  };
};

type PreviewData = {
  sql: string;
  columns: string[];
  calculation_type: string;
  group_level: string;
  parameters: any;
};

const CalculationBuilder: React.FC = () => {
  const { showToast } = useToast();
  
  // Use unified calculations hook instead of separate hooks
  const {
    userCalculations,
    systemCalculations,
    summary,
    isLoading: calculationsLoading,
    refetch: refetchCalculations
  } = useUnifiedCalculations();

  // Tab state
  const [activeTab, setActiveTab] = useState<CalculationTab>('user-defined');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState<boolean>(false);

  // Configuration state
  const {
    allAvailableFields,
    aggregationFunctions,
    sourceModels,
    groupLevels,
    fieldsLoading,
    configError,
    hasLoadedConfig,
    fetchCalculationConfig,
    retryLoadConfig,
    isConfigAvailable
  } = useCalculationConfig();

  // Modal states
  const [showModal, setShowModal] = useState<boolean>(false);
  const [modalType, setModalType] = useState<'user-defined' | 'system-sql'>('user-defined');
  const [editingCalculation, setEditingCalculation] = useState<UserCalculation | SystemCalculation | null>(null);
  const [showPreviewModal, setShowPreviewModal] = useState<boolean>(false);
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const [showUsageModal, setShowUsageModal] = useState<boolean>(false);
  const [selectedUsageData, setSelectedUsageData] = useState<any>(null);

  // Form state
  const {
    calculation,
    error,
    isSaving,
    updateCalculation,
    saveCalculation,
    resetForm,
    initializeForm
  } = useCalculationForm(editingCalculation as UserCalculation | null);

  // Initialize data
  useEffect(() => {
    fetchCalculationConfig();
  }, []);

  // Tab switching with unsaved changes protection
  const handleTabSwitch = (newTab: CalculationTab) => {
    if (hasUnsavedChanges) {
      const confirmSwitch = window.confirm(
        'You have unsaved changes. Switching tabs will discard your changes. Continue?'
      );
      if (!confirmSwitch) return;
      
      // Reset form and unsaved changes
      resetForm();
      setHasUnsavedChanges(false);
      setShowModal(false);
    }
    setActiveTab(newTab);
  };

  // Handle opening modal for create/edit
  const handleOpenModal = (
    type: 'user-defined' | 'system-sql',
    calc: UserCalculation | SystemCalculation | null = null
  ) => {
    setModalType(type);
    setEditingCalculation(calc);
    // Only initialize form with UserCalculation for user-defined modal
    if (type === 'user-defined') {
      initializeForm(calc as UserCalculation | null);
    } else {
      initializeForm(null); // For system SQL, start with empty form
    }
    setShowModal(true);
    setHasUnsavedChanges(false);
  };

  // Handle closing modal
  const handleCloseModal = () => {
    if (hasUnsavedChanges) {
      const confirmClose = window.confirm(
        'You have unsaved changes. Closing will discard your changes. Continue?'
      );
      if (!confirmClose) return;
    }
    
    setShowModal(false);
    setEditingCalculation(null);
    setModalType('user-defined');
    resetForm();
    setHasUnsavedChanges(false);
  };

  // Handle form changes (track unsaved changes)
  const handleFormChange = (updates: any) => {
    updateCalculation(updates);
    setHasUnsavedChanges(true);
  };

  // Handle saving calculation
  const handleSaveCalculation = async () => {
    let success = false;
    
    if (modalType === 'user-defined') {
      success = await saveCalculation(() => {
        handleCloseModal();
        refetchCalculations();
      });
    } else if (modalType === 'system-sql') {
      try {
        // Convert CalculationForm to SystemCalculationCreateRequest
        // For system SQL, we store SQL in source_field and result column in weight_field
        const systemCalcData = {
          name: calculation.name,
          description: calculation.description,
          raw_sql: calculation.source_field || '', // SQL is stored in source_field
          result_column_name: calculation.weight_field || '', // Result column is stored in weight_field
          group_level: (calculation.level || 'deal') as 'deal' | 'tranche'
        };
        await calculationsApi.createSystemSqlCalculation(systemCalcData);
        success = true;
        handleCloseModal();
        refetchCalculations();
        showToast('System calculation created successfully!', 'success');
      } catch (error) {
        console.error('Error creating system calculation:', error);
        showToast('Error creating system calculation', 'error');
      }
    }
    
    if (success) {
      setHasUnsavedChanges(false);
    }
  };

  // Handle SQL preview
  const handlePreviewSQL = async (calcId: number) => {
    setPreviewLoading(true);
    setPreviewData(null);
    setShowPreviewModal(true);
    
    try {
      const response = await calculationsApi.previewSQL(calcId, SAMPLE_PREVIEW_PARAMS);
      // Ensure the response data matches our PreviewData type
      const previewData = {
        sql: response.data.sql || '',
        columns: response.data.columns || [],
        calculation_type: response.data.calculation_type || '',
        group_level: response.data.group_level || '',
        parameters: response.data.parameters || {}
      };
      setPreviewData(previewData);
    } catch (error: unknown) {
      console.error('Error generating SQL preview:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      showToast(`Error generating SQL preview: ${errorMessage}`, 'error');
    } finally {
      setPreviewLoading(false);
    }
  };

  // Update the existing calculations state when unified data changes
  const [filteredUserCalculations, setFilteredUserCalculations] = useState<UserCalculation[]>([]);
  const [filteredSystemCalculations, setFilteredSystemCalculations] = useState<SystemCalculation[]>([]);
  const [userFilter, setUserFilter] = useState<string>('all');
  const [systemFilter, setSystemFilter] = useState<string>('all');

  // Filter calculations based on selected filters
  useEffect(() => {
    let filtered = userCalculations;
    if (userFilter === 'deal') {
      filtered = userCalculations.filter(calc => calc.group_level === 'deal');
    } else if (userFilter === 'tranche') {
      filtered = userCalculations.filter(calc => calc.group_level === 'tranche');
    }
    setFilteredUserCalculations(filtered);
  }, [userCalculations, userFilter]);

  useEffect(() => {
    let filtered = systemCalculations;
    if (systemFilter === 'deal') {
      filtered = systemCalculations.filter(calc => calc.group_level === 'deal');
    } else if (systemFilter === 'tranche') {
      filtered = systemCalculations.filter(calc => calc.group_level === 'tranche');
    }
    setFilteredSystemCalculations(filtered);
  }, [systemCalculations, systemFilter]);

  // Handle showing usage information using embedded usage_info
  const handleShowUsage = (calcId: number, calcName: string) => {
    const calculation = activeTab === 'user-defined' 
      ? userCalculations.find(calc => calc.id === calcId)
      : systemCalculations.find(calc => calc.id === calcId);
    
    const calcWithUsage = calculation as CalculationWithUsage;
    if (calcWithUsage?.usage_info) {
      setSelectedUsageData({ ...calcWithUsage.usage_info, calculation_name: calcName });
      setShowUsageModal(true);
    }
  };

  // Get current tab data
  const getCurrentTabData = () => {
    if (activeTab === 'user-defined') {
      return {
        calculations: userCalculations,
        filteredCalculations: filteredUserCalculations,
        selectedFilter: userFilter,
        setSelectedFilter: setUserFilter,
        loading: calculationsLoading,
        deleteCalculation: () => showToast('Delete functionality will be implemented', 'info')
      };
    } else {
      return {
        calculations: systemCalculations,
        filteredCalculations: filteredSystemCalculations,
        selectedFilter: systemFilter,
        setSelectedFilter: setSystemFilter,
        loading: calculationsLoading,
        deleteCalculation: () => showToast('System calculations cannot be deleted', 'warning')
      };
    }
  };

  const tabData = getCurrentTabData();

  return (
    <div className="container-fluid">
      {/* Header */}
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h3>Calculation Builder</h3>
          <p className="text-muted mb-0">Create and manage calculations for reporting</p>
        </div>
      </div>

      {/* Calculation Statistics - now using summary from unified endpoint */}
      {isConfigAvailable() && (
        <div className="card bg-light mt-4">
          <div className="card-body">
            <h6 className="card-title text-center mb-3">
              <i className="bi bi-bar-chart me-2"></i>
              Calculation Statistics
            </h6>
            <div className="row text-center">
              <div className="col-md-3">
                <div className="h4 mb-0 text-primary">{summary.user_calculation_count}</div>
                <small className="text-muted">Total User Calculations</small>
              </div>
              <div className="col-md-3">
                <div className="h4 mb-0 text-info">{summary.user_in_use_count}</div>
                <small className="text-muted">User Calcs In Use</small>
              </div>
              <div className="col-md-3">
                <div className="h4 mb-0 text-success">{summary.system_calculation_count}</div>
                <small className="text-muted">Total System Calculations</small>
              </div>
              <div className="col-md-3">
                <div className="h4 mb-0 text-warning">{summary.system_in_use_count}</div>
                <small className="text-muted">System Calcs In Use</small>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Configuration Error State */}
      {configError && (
        <div className="alert alert-danger d-flex align-items-center" role="alert">
          <i className="bi bi-exclamation-triangle-fill me-3"></i>
          <div className="flex-grow-1">
            <h6 className="alert-heading mb-1">Configuration Error</h6>
            <p className="mb-2">{configError}</p>
            <small className="text-muted">
              The calculation builder requires configuration data from the server to function properly.
            </small>
          </div>
          <button
            onClick={retryLoadConfig}
            disabled={fieldsLoading}
            className="btn btn-outline-danger"
          >
            {fieldsLoading ? (
              <>
                <span className="spinner-border spinner-border-sm me-2" role="status"></span>
                Retrying...
              </>
            ) : (
              <>
                <i className="bi bi-arrow-clockwise me-2"></i>
                Retry
              </>
            )}
          </button>
        </div>
      )}

      {/* Configuration Loading State */}
      {fieldsLoading && !hasLoadedConfig && (
        <div className="card">
          <div className="card-body text-center py-5">
            <div className="spinner-border text-primary mb-3" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
            <h5>Loading Configuration</h5>
            <p className="text-muted mb-0">
              Fetching calculation configuration from server...
            </p>
          </div>
        </div>
      )}

      {/* Main Content - Only show if config is available */}
      {isConfigAvailable() && (
        <>
          {/* Tab Navigation */}
          <div className="card mb-4">
            <div className="card-header p-0">
              <nav>
                <div className="nav nav-tabs card-header-tabs" role="tablist">
                  <button
                    className={`nav-link ${activeTab === 'user-defined' ? 'active' : ''}`}
                    type="button"
                    onClick={() => handleTabSwitch('user-defined')}
                    disabled={hasUnsavedChanges}
                  >
                    <i className="bi bi-person-gear me-2"></i>
                    User Defined Calculations
                    <span className="badge bg-primary ms-2">{userCalculations.length}</span>
                  </button>
                  <button
                    className={`nav-link ${activeTab === 'system-defined' ? 'active' : ''}`}
                    type="button"
                    onClick={() => handleTabSwitch('system-defined')}
                    disabled={hasUnsavedChanges}
                  >
                    <i className="bi bi-gear-fill me-2"></i>
                    System Defined Calculations
                    <span className="badge bg-primary ms-2">{systemCalculations.length}</span>
                  </button>
                </div>
              </nav>
            </div>

            <div className="card-body">
              {/* Unsaved Changes Warning */}
              {hasUnsavedChanges && (
                <div className="alert alert-warning d-flex align-items-center mb-3">
                  <i className="bi bi-exclamation-triangle me-2"></i>
                  <span>You have unsaved changes. Save or cancel before switching tabs.</span>
                </div>
              )}

              {/* Tab Content */}
              <div className="tab-content">
                {/* User Defined Calculations Tab */}
                {activeTab === 'user-defined' && (
                  <div className="tab-pane fade show active">
                    <div className="d-flex justify-content-between align-items-center mb-3">
                      <h5 className="mb-0">User Defined Calculations</h5>
                      <button
                        onClick={() => handleOpenModal('user-defined')}
                        disabled={fieldsLoading}
                        className="btn btn-primary"
                      >
                        <i className="bi bi-plus-lg me-2"></i>
                        New User Calculation
                      </button>
                    </div>

                    <FilterSection
                      selectedFilter={tabData.selectedFilter}
                      onFilterChange={tabData.setSelectedFilter}
                      fieldsLoading={fieldsLoading}
                    />

                    {/* User Calculations List */}
                    <div className="card">
                      <div className="card-header bg-primary">
                        <h6 className="card-title mb-0 text-white">Available User Calculations</h6>
                      </div>
                      <div className="card-body">
                        {tabData.loading ? (
                          <div className="text-center py-4">
                            <div className="spinner-border text-primary" role="status">
                              <span className="visually-hidden">Loading...</span>
                            </div>
                            <p className="mt-2 mb-0">Loading calculations...</p>
                          </div>
                        ) : (
                          <div className="row g-3">
                            {tabData.filteredCalculations.map((calc) => (
                              <div key={calc.id} className="col-12">
                                <CalculationCard
                                  calculation={calc}
                                  onEdit={(calc) => handleOpenModal('user-defined', calc)}
                                  onDelete={tabData.deleteCalculation}
                                  onPreviewSQL={handlePreviewSQL}
                                  onShowUsage={handleShowUsage}
                                />
                              </div>
                            ))}
                            
                            {tabData.filteredCalculations.length === 0 && !tabData.loading && (
                              <div className="col-12">
                                <div className="text-center py-4 text-muted">
                                  No user calculations available. Create your first calculation above.
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* System Defined Calculations Tab */}
                {activeTab === 'system-defined' && (
                  <SystemCalculationsTab
                    filteredCalculations={filteredSystemCalculations}
                    selectedFilter={systemFilter}
                    setSelectedFilter={setSystemFilter}
                    loading={calculationsLoading}
                    usage={{}} // Pass empty object since usage is now embedded in calculations
                    onCreateSystemSql={() => handleOpenModal('system-sql')}
                    onPreviewSQL={handlePreviewSQL}
                    onShowUsage={handleShowUsage}
                  />
                )}
              </div>
            </div>
          </div>

          
        </>
      )}

      {/* Modals - Only render if config is available */}
      {isConfigAvailable() && (
        <>
          <CalculationModal
            isOpen={showModal}
            modalType={modalType}
            editingCalculation={editingCalculation}
            calculation={calculation}
            error={error}
            isSaving={isSaving}
            fieldsLoading={fieldsLoading}
            allAvailableFields={allAvailableFields}
            aggregationFunctions={aggregationFunctions}
            sourceModels={sourceModels}
            groupLevels={groupLevels}
            onClose={handleCloseModal}
            onSave={handleSaveCalculation}
            onUpdateCalculation={handleFormChange}
            hasUnsavedChanges={hasUnsavedChanges}
          />

          <SqlPreviewModal
            isOpen={showPreviewModal}
            previewData={previewData}
            previewLoading={previewLoading}
            onClose={() => setShowPreviewModal(false)}
          />

          <UsageModal
            isOpen={showUsageModal}
            selectedUsageData={selectedUsageData}
            onClose={() => setShowUsageModal(false)}
          />
        </>
      )}
    </div>
  );
};

export default CalculationBuilder;