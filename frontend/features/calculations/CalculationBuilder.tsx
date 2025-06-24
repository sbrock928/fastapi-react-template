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
import UsageModal from './components/UsageModal';
import SqlPreviewModal from './components/SqlPreviewModal';

type CalculationTab = 'user-defined' | 'system-defined';

const CalculationBuilder: React.FC = () => {
  const { showToast } = useToast();
  
  // Replace separate hooks with unified hook
  const {
    userCalculations,
    systemCalculations,
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

  // Modal states (remove CDI modal states - now handled by global context)
  const [showModal, setShowModal] = useState<boolean>(false);
  const [modalType, setModalType] = useState<'user-defined' | 'system-sql'>('user-defined');
  const [editingCalculation, setEditingCalculation] = useState<UserCalculation | SystemCalculation | null>(null);
  const [showUsageModal, setShowUsageModal] = useState<boolean>(false);
  const [selectedUsageData, setSelectedUsageData] = useState<any>(null);
  const [usageLoading, setUsageLoading] = useState<boolean>(false);
  const [usageScope] = useState<'DEAL' | 'TRANCHE' | 'ALL'>('ALL');

  // Preview modal states
  const [showPreviewModal, setShowPreviewModal] = useState<boolean>(false);
  const [previewData, setPreviewData] = useState<any>(null);
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);

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

  // Sample parameters for SQL preview
  const SAMPLE_PREVIEW_PARAMS = {
    deal_tranche_mapping: { 101: ['A', 'B'], 102: [], 103: [] },
    cycle: 202404
  };

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
    
    if (type === 'user-defined') {
      // Initialize form with UserCalculation for user-defined modal
      initializeForm(calc as UserCalculation | null);
    } else if (type === 'system-sql') {
      // For system SQL, populate form with system calculation data if editing
      if (calc && calc.calculation_type === 'system_sql') {
        const systemCalc = calc as SystemCalculation;
        updateCalculation({
          name: systemCalc.name,
          description: systemCalc.description || '',
          function_type: 'SYSTEM_SQL',
          source: '', // Not used for system SQL
          source_field: systemCalc.raw_sql, // SQL stored in source_field
          level: systemCalc.group_level,
          weight_field: systemCalc.result_column_name // Result column stored in weight_field
        });
      } else {
        // Start with empty form for new system calculation
        initializeForm(null);
      }
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
        // Convert CalculationForm to SystemCalculationCreateRequest or SystemCalculationUpdateRequest
        // For system SQL, we store SQL in source_field and result column in weight_field
        const systemCalcData = {
          name: calculation.name,
          description: calculation.description,
          raw_sql: calculation.source_field || '', // SQL is stored in source_field
          result_column_name: calculation.weight_field || '', // Result column is stored in weight_field
          group_level: (calculation.level || 'deal') as 'deal' | 'tranche'
        };

        if (editingCalculation) {
          // Update existing system calculation using PATCH
          await calculationsApi.updateSystemCalculation(editingCalculation.id, systemCalcData);
          showToast('System calculation updated successfully!', 'success');
        } else {
          // Create new system calculation
          await calculationsApi.createSystemSqlCalculation(systemCalcData);
          showToast('System calculation created successfully!', 'success');
        }
        
        success = true;
        handleCloseModal();
        refetchCalculations();
      } catch (error: any) {
        console.error('Error saving system calculation:', error);
        const action = editingCalculation ? 'updating' : 'creating';
        
        // Extract detailed error message and throw it so the modal can catch it
        let errorMessage = `Error ${action} system calculation`;
        if (error.response?.data?.detail) {
          if (typeof error.response.data.detail === 'string') {
            errorMessage = error.response.data.detail;
          } else if (Array.isArray(error.response.data.detail)) {
            const detailedErrors = error.response.data.detail.map((err: any) => 
              typeof err === 'string' ? err : err.msg || err.message || JSON.stringify(err)
            );
            errorMessage = detailedErrors.join(', ');
          } else if (error.response.data.detail.msg) {
            errorMessage = error.response.data.detail.msg;
          }
        } else if (error.message) {
          errorMessage = error.message;
        }
        
        showToast(errorMessage, 'error');
        
        // Throw the error so the modal can display it
        throw new Error(errorMessage);
      }
    }
    
    if (success) {
      setHasUnsavedChanges(false);
    }
  };

  // Update the existing calculations state when unified data changes
  const [filteredUserCalculations, setFilteredUserCalculations] = useState<UserCalculation[]>([]);
  const [filteredSystemCalculations, setFilteredSystemCalculations] = useState<SystemCalculation[]>([]);
  const [userFilter, setUserFilter] = useState<string>('all');
  const [systemFilter, setSystemFilter] = useState<string>('all');

  // Update the calculations state management
  useEffect(() => {
    setFilteredUserCalculations(userCalculations);
  }, [userCalculations]);

  useEffect(() => {
    setFilteredSystemCalculations(systemCalculations);
  }, [systemCalculations]);

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

  // Usage tracking state
  const [userUsage, setUserUsage] = useState<Record<number, any>>({});
  const [systemUsage, setSystemUsage] = useState<Record<number, any>>({});

  // Fetch usage data for calculations
  const fetchUsageData = async () => {
    try {
      // Fetch usage for user calculations
      const userUsageMap: Record<number, any> = {};
      for (const calc of userCalculations) {
        try {
          const response = await calculationsApi.getUserCalculationUsage(calc.id);
          userUsageMap[calc.id] = response.data;
        } catch (error) {
          console.error(`Error fetching usage for user calculation ${calc.id}:`, error);
          userUsageMap[calc.id] = { is_in_use: false, report_count: 0, reports: [] };
        }
      }
      setUserUsage(userUsageMap);

      // Fetch usage for system calculations
      const systemUsageMap: Record<number, any> = {};
      for (const calc of systemCalculations) {
        try {
          const response = await calculationsApi.getSystemCalculationUsage(calc.id);
          systemUsageMap[calc.id] = response.data;
        } catch (error) {
          console.error(`Error fetching usage for system calculation ${calc.id}:`, error);
          systemUsageMap[calc.id] = { is_in_use: false, report_count: 0, reports: [] };
        }
      }
      setSystemUsage(systemUsageMap);
    } catch (error) {
      console.error('Error fetching usage data:', error);
    }
  };

  // Fetch usage data when calculations change
  useEffect(() => {
    if (userCalculations.length > 0 || systemCalculations.length > 0) {
      fetchUsageData();
    }
  }, [userCalculations, systemCalculations]);

  // Handle showing usage information with scope-aware fetching
  const handleShowUsage = async (calcId: number, calcName: string) => {
    setUsageLoading(true);
    setShowUsageModal(true);
    setSelectedUsageData(null);
    
    try {
      const isUserCalc = activeTab === 'user-defined';
      const scopeParam = usageScope === 'ALL' ? undefined : usageScope;
      
      let response;
      if (isUserCalc) {
        response = await calculationsApi.getUserCalculationUsage(calcId, scopeParam);
      } else {
        response = await calculationsApi.getSystemCalculationUsage(calcId, scopeParam);
      }
      
      setSelectedUsageData({
        ...response.data,
        calculation_name: calcName,
        scope_filter: usageScope
      });
    } catch (error) {
      console.error('Error fetching usage information:', error);
      showToast('Error fetching usage information', 'error');
      setShowUsageModal(false);
    } finally {
      setUsageLoading(false);
    }
  };

  // Handle SQL preview - FIXED: Proper error handling and data validation
  const handlePreviewSQL = async (calcId: number) => {
    setPreviewLoading(true);
    setShowPreviewModal(true); // Show modal first with loading state
    
    // Set calculation type based on active tab
    // setPreviewCalculationType(activeTab === 'system-defined' ? 'system_calculation' : 'user_calculation');
    
    try {
      let response;
      
      // Determine which API to call based on the current tab
      if (activeTab === 'user-defined') {
        response = await calculationsApi.previewUserSQL(calcId, SAMPLE_PREVIEW_PARAMS);
      } else if (activeTab === 'system-defined') {
        response = await calculationsApi.previewSystemSql(calcId, SAMPLE_PREVIEW_PARAMS);
      } else {
        // Default to user calculation for other tabs
        response = await calculationsApi.previewSQL(calcId, SAMPLE_PREVIEW_PARAMS);
      }
      
      // FIXED: Handle both successful and error responses properly
      if (response.data) {
        // Check if the response contains an error
        if (response.data.error) {
          // Set preview data with error information
          setPreviewData({
            sql: response.data.sql_preview || '-- Error generating SQL preview\n-- Please try again or contact support',
            error: response.data.error,
            calculation_type: response.data.calculation_type || 'unknown',
            group_level: response.data.group_level || 'unknown',
            columns: [],
            parameters: response.data.parameters_used || {}
          });
          showToast(`SQL preview generated with warnings: ${response.data.error}`, 'warning');
        } else if (response.data.sql_preview || response.data.sql) {
          // Successful response - map the backend format to frontend format
          setPreviewData({
            sql: response.data.sql_preview || response.data.sql,
            calculation_type: response.data.calculation_type || 'unknown',
            group_level: response.data.group_level || 'unknown',
            columns: response.data.columns || [],
            parameters: response.data.parameters_used || response.data.parameters || {}
          });
        } else {
          throw new Error('Invalid response format from preview API - no SQL found');
        }
      } else {
        throw new Error('Empty response from preview API');
      }
    } catch (error) {
      console.error('Error previewing SQL:', error);
      setPreviewData({
        sql: '-- Error generating SQL preview\n-- Please try again or contact support',
        error: error instanceof Error ? error.message : 'Unknown error',
        calculation_type: 'unknown',
        group_level: 'unknown',
        columns: [],
        parameters: {}
      });
      showToast('Failed to preview SQL. Please try again.', 'error');
    } finally {
      setPreviewLoading(false);
    }
  };

  // Define tab data interface
  interface TabData {
    calculations?: UserCalculation[] | SystemCalculation[];
    filteredCalculations?: UserCalculation[] | SystemCalculation[];
    selectedFilter?: string;
    setSelectedFilter?: React.Dispatch<React.SetStateAction<string>>;
    loading: boolean;
    deleteCalculation?: (id: number, name: string) => Promise<void>;
  }

  // Handle delete for user calculations
  const handleDeleteUserCalculation = async (id: number, name: string): Promise<void> => {
    try {
      await calculationsApi.deleteCalculation(id);
      showToast(`User calculation "${name}" deleted successfully!`, 'success');
      refetchCalculations();
    } catch (error: any) {
      console.error('Error deleting user calculation:', error);
      let errorMessage = `Error deleting calculation: ${error.message}`;
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      showToast(errorMessage, 'error');
    }
  };

  // Handle delete for system calculations
  const handleDeleteSystemCalculation = async (id: number, name: string): Promise<void> => {
    try {
      await calculationsApi.deleteSystemCalculation(id);
      showToast(`System calculation "${name}" deleted successfully!`, 'success');
      refetchCalculations();
    } catch (error: any) {
      console.error('Error deleting system calculation:', error);
      let errorMessage = `Error deleting calculation: ${error.message}`;
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      showToast(errorMessage, 'error');
    }
  };

  // Get tab data with proper delete handlers
  const getCurrentTabData = (): TabData => {
    if (activeTab === 'user-defined') {
      return {
        calculations: userCalculations,
        filteredCalculations: filteredUserCalculations,
        selectedFilter: userFilter,
        setSelectedFilter: setUserFilter,
        loading: calculationsLoading,
        deleteCalculation: handleDeleteUserCalculation
      };
    } else {
      return {
        calculations: systemCalculations,
        filteredCalculations: filteredSystemCalculations,
        selectedFilter: systemFilter,
        setSelectedFilter: setSystemFilter,
        loading: calculationsLoading,
        deleteCalculation: handleDeleteSystemCalculation
      };
    }
  };

  const tabData = getCurrentTabData();

  // Calculate filtered counts for tab badges
  const getSystemSqlCount = () => {
    // Only count system SQL calculations (CDI variables removed)
    return systemCalculations.filter(calc => {
      return calc.calculation_type === 'system_sql';
    }).length;
  };

  return (
    <div className="container-fluid">
      {/* Header */}
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h3>Calculation Builder</h3>
          <p className="text-muted mb-0">Create and manage calculations for reporting</p>
        </div>
      </div>

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
                    <span className="badge bg-primary ms-2">{getSystemSqlCount()}</span>
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

                    {tabData.selectedFilter !== undefined && tabData.setSelectedFilter && (
                      <FilterSection
                        selectedFilter={tabData.selectedFilter}
                        onFilterChange={tabData.setSelectedFilter}
                        fieldsLoading={fieldsLoading}
                      />
                    )}

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
                            {tabData.filteredCalculations && tabData.filteredCalculations.map((calc: any) => (
                              <div key={calc.id} className="col-12">
                                <CalculationCard
                                  calculation={calc}
                                  usage={userUsage[calc.id]}
                                  usageScope={usageScope}
                                  onEdit={(calc) => handleOpenModal('user-defined', calc)}
                                  onDelete={tabData.deleteCalculation || (() => {})}
                                  onShowUsage={handleShowUsage}
                                  onPreviewSQL={() => handlePreviewSQL(calc.id)}
                                />
                              </div>
                            ))}
                            
                            {tabData.filteredCalculations && tabData.filteredCalculations.length === 0 && !tabData.loading && (
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
                    usage={systemUsage}
                    usageScope={usageScope}
                    onCreateSystemSql={() => handleOpenModal('system-sql')}
                    onEditSystemSql={(calc) => handleOpenModal('system-sql', calc)}
                    onDeleteSystemSql={handleDeleteSystemCalculation}
                    onShowUsage={handleShowUsage}
                    onPreviewSQL={(calcId) => handlePreviewSQL(calcId)}
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

          <UsageModal
            isOpen={showUsageModal}
            selectedUsageData={selectedUsageData}
            usageLoading={usageLoading}
            onClose={() => setShowUsageModal(false)}
          />

          <SqlPreviewModal
            isOpen={showPreviewModal}
            previewData={previewData}
            previewLoading={previewLoading}
            onClose={() => setShowPreviewModal(false)}
          />
        </>
      )}
    </div>
  );
};

export default CalculationBuilder;