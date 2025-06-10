// frontend/features/calculations/CalculationBuilder.tsx
import React, { useState, useEffect } from 'react';
import { useToast } from '@/context/ToastContext';
import { calculationsApi } from '@/services/calculationsApi';
import type { Calculation, PreviewData } from '@/types/calculations';

// Components
import FilterSection from './components/FilterSection';
import CalculationCard from './components/CalculationCard';
import CalculationModal from './components/CalculationModal';
import SystemCalculationsTab from './components/SystemCalculationsTab';
import SqlPreviewModal from './components/SqlPreviewModal';
import UsageModal from './components/UsageModal';

// Hooks
import { useCalculations } from './hooks/useCalculations';
import { useCalculationConfig, useCalculationForm } from './hooks/useCalculationConfig';
import { useSystemCalculations } from './hooks/useSystemCalculations';

// Constants
import { SAMPLE_PREVIEW_PARAMS } from './constants/calculationConstants';

type CalculationTab = 'user-defined' | 'system-defined';

const CalculationBuilder: React.FC = () => {
  const { showToast } = useToast();

  // Tab state
  const [activeTab, setActiveTab] = useState<CalculationTab>('user-defined');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState<boolean>(false);

  // User-defined calculations state
  const {
    calculations: userCalculations,
    filteredCalculations: filteredUserCalculations,
    selectedFilter: userFilter,
    setSelectedFilter: setUserFilter,
    isLoading: userLoading,
    calculationUsage: userUsage,
    fetchCalculations: fetchUserCalculations,
    deleteCalculation: deleteUserCalculation
  } = useCalculations();

  // System calculations state
  const {
    systemCalculations,
    filteredSystemCalculations,
    selectedFilter: systemFilter,
    setSelectedFilter: setSystemFilter,
    isLoading: systemLoading,
    systemUsage,
    fetchSystemCalculations,
    createSystemFieldCalculation,
    createSystemSqlCalculation
  } = useSystemCalculations();

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
  const [modalType, setModalType] = useState<'user-defined' | 'system-field' | 'system-sql'>('user-defined');
  const [editingCalculation, setEditingCalculation] = useState<Calculation | null>(null);
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
  } = useCalculationForm(editingCalculation);

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
    type: 'user-defined' | 'system-field' | 'system-sql',
    calc: Calculation | null = null
  ) => {
    setModalType(type);
    setEditingCalculation(calc);
    initializeForm(calc);
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
        fetchUserCalculations();
      });
    } else if (modalType === 'system-field') {
      success = await createSystemFieldCalculation(calculation, () => {
        handleCloseModal();
        fetchSystemCalculations();
      });
    } else if (modalType === 'system-sql') {
      success = await createSystemSqlCalculation(calculation, () => {
        handleCloseModal();
        fetchSystemCalculations();
      });
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
      setPreviewData(response.data);
    } catch (error: unknown) {
      console.error('Error generating SQL preview:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      showToast(`Error generating SQL preview: ${errorMessage}`, 'error');
    } finally {
      setPreviewLoading(false);
    }
  };

  // Handle showing usage information
  const handleShowUsage = (calcId: number, calcName: string) => {
    const usage = activeTab === 'user-defined' 
      ? userUsage[calcId] 
      : systemUsage[calcId];
    
    if (usage) {
      setSelectedUsageData({ ...usage, calculation_name: calcName });
      setShowUsageModal(true);
    }
  };

  // Get current calculations and state based on active tab
  const getCurrentTabData = () => {
    if (activeTab === 'user-defined') {
      return {
        calculations: userCalculations,
        filteredCalculations: filteredUserCalculations,
        selectedFilter: userFilter,
        setSelectedFilter: setUserFilter,
        loading: userLoading,
        usage: userUsage,
        deleteCalculation: deleteUserCalculation
      };
    } else {
      return {
        calculations: systemCalculations,
        filteredCalculations: filteredSystemCalculations,
        selectedFilter: systemFilter,
        setSelectedFilter: setSystemFilter,
        loading: systemLoading,
        usage: systemUsage,
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
                    <span className="badge bg-success ms-2">{systemCalculations.length}</span>
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
                                  usage={tabData.usage[calc.id]}
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
                    calculations={systemCalculations}
                    filteredCalculations={filteredSystemCalculations}
                    selectedFilter={systemFilter}
                    setSelectedFilter={setSystemFilter}
                    loading={systemLoading}
                    usage={systemUsage}
                    onCreateSystemField={() => handleOpenModal('system-field')}
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