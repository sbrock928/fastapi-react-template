// frontend/src/components/CalculationBuilder.tsx
import React, { useState, useEffect } from 'react';
import { useToast } from '@/context/ToastContext';
import { calculationsApi } from '@/services/calculationsApi';
import type { Calculation, PreviewData } from '@/types/calculations';

// Components
import FilterSection from './components/FilterSection';
import CalculationCard from './components/CalculationCard';
import CalculationModal from './components/CalculationModal';
import SqlPreviewModal from './components/SqlPreviewModal';
import UsageModal from './components/UsageModal';

// Hooks
import { useCalculations } from './hooks/useCalculations';
import { useCalculationConfig, useCalculationForm } from './hooks/useCalculationConfig';

// Constants
import { SAMPLE_PREVIEW_PARAMS } from './constants/calculationConstants';

const CalculationBuilder: React.FC = () => {
  const { showToast } = useToast();

  // Main calculations state
  const {
    calculations,
    filteredCalculations,
    selectedFilter,
    setSelectedFilter,
    isLoading,
    calculationUsage,
    fetchCalculations,
    deleteCalculation
  } = useCalculations();

  // Configuration state
  const {
    allAvailableFields,
    aggregationFunctions,
    sourceModels,
    groupLevels,
    fieldsLoading,
    fetchCalculationConfig
  } = useCalculationConfig();

  // Modal states
  const [showModal, setShowModal] = useState<boolean>(false);
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

  // Handle opening modal for create/edit
  const handleOpenModal = (calc: Calculation | null = null) => {
    setEditingCalculation(calc);
    initializeForm(calc);
    setShowModal(true);
  };

  // Handle closing modal
  const handleCloseModal = () => {
    setShowModal(false);
    setEditingCalculation(null);
    resetForm();
  };

  // Handle saving calculation
  const handleSaveCalculation = async () => {
    await saveCalculation(() => {
      handleCloseModal();
      fetchCalculations();
    });
  };

  // Handle SQL preview
  const handlePreviewSQL = async (calcId: number) => {
    setPreviewLoading(true);
    setPreviewData(null);
    setShowPreviewModal(true);
    
    try {
      const response = await calculationsApi.previewSQL(calcId, SAMPLE_PREVIEW_PARAMS);
      setPreviewData(response.data);
    } catch (error: any) {
      console.error('Error generating SQL preview:', error);
      showToast(`Error generating SQL preview: ${error.message}`, 'error');
    } finally {
      setPreviewLoading(false);
    }
  };

  // Handle showing usage information
  const handleShowUsage = (calcId: number, calcName: string) => {
    const usage = calculationUsage[calcId];
    if (usage) {
      setSelectedUsageData({ ...usage, calculation_name: calcName });
      setShowUsageModal(true);
    }
  };

  // Get display calculations based on filter
  const displayCalculations = selectedFilter === 'all' ? calculations : filteredCalculations;

  return (
    <div className="container-fluid">
      {/* Header */}
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h3>Calculation Builder</h3>
          <p className="text-muted mb-0">Create and manage ORM-based calculations for reporting</p>
        </div>
        <button
          onClick={() => handleOpenModal()}
          disabled={fieldsLoading}
          className="btn btn-primary"
        >
          <i className="bi bi-plus-lg me-2"></i>
          New Calculation
        </button>
      </div>

      {/* Filter Section */}
      <FilterSection
        selectedFilter={selectedFilter}
        onFilterChange={setSelectedFilter}
        fieldsLoading={fieldsLoading}
      />

      {/* Available Calculations List */}
      <div className="card">
        <div className="card-header bg-primary">
          <h5 className="card-title mb-0">Available Calculations</h5>
        </div>
        <div className="card-body">
          {isLoading || fieldsLoading ? (
            <div className="text-center py-4">
              <div className="spinner-border text-primary" role="status">
                <span className="visually-hidden">Loading...</span>
              </div>
              <p className="mt-2 mb-0">
                {isLoading ? 'Loading calculations...' : 'Loading configuration...'}
              </p>
            </div>
          ) : (
            <div className="row g-3">
              {displayCalculations.map((calc) => (
                <div key={calc.id} className="col-12">
                  <CalculationCard
                    calculation={calc}
                    usage={calculationUsage[calc.id]}
                    onEdit={handleOpenModal}
                    onDelete={deleteCalculation}
                    onPreviewSQL={handlePreviewSQL}
                    onShowUsage={handleShowUsage}
                  />
                </div>
              ))}
              
              {displayCalculations.length === 0 && !isLoading && !fieldsLoading && (
                <div className="col-12">
                  <div className="text-center py-4 text-muted">
                    No calculations available. Create your first calculation above.
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      <CalculationModal
        isOpen={showModal}
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
        onUpdateCalculation={updateCalculation}
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
    </div>
  );
};

export default CalculationBuilder;