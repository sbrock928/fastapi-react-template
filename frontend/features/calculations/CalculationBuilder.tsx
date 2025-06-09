// frontend/src/components/CalculationBuilder.tsx
import React, { useState, useEffect } from 'react';
import { useToast } from '@/context/ToastContext';
import { calculationsApi } from '@/services/calculationsApi';
import type {
  Calculation,
  CalculationField,
  AggregationFunction,
  SourceModel,
  GroupLevel,
  CalculationForm,
  PreviewData,
  CalculationConfig
} from '@/types/calculations';

const CalculationBuilder: React.FC = () => {
  const { showToast } = useToast();

  // State management
  const [calculations, setCalculations] = useState<Calculation[]>([]);
  const [filteredCalculations, setFilteredCalculations] = useState<Calculation[]>([]);
  const [selectedFilter, setSelectedFilter] = useState<string>('all');
  const [showModal, setShowModal] = useState<boolean>(false);
  const [editingCalculation, setEditingCalculation] = useState<Calculation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showPreviewModal, setShowPreviewModal] = useState<boolean>(false);
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  
  const [calculation, setCalculation] = useState<CalculationForm>({
    name: '',
    function_type: 'SUM',
    source: '',
    source_field: '',
    level: 'deal',
    weight_field: '',
    description: ''
  });

  const [allAvailableFields, setAllAvailableFields] = useState<Record<string, CalculationField[]>>({});
  const [aggregationFunctions, setAggregationFunctions] = useState<AggregationFunction[]>([]);
  const [sourceModels, setSourceModels] = useState<SourceModel[]>([]);
  const [groupLevels, setGroupLevels] = useState<GroupLevel[]>([]);
  const [fieldsLoading, setFieldsLoading] = useState<boolean>(false);

  // Fetch calculation configuration from API
  const fetchCalculationConfig = async (): Promise<void> => {
    setFieldsLoading(true);
    try {
      const response = await calculationsApi.getCalculationConfig();
      const data: CalculationConfig = response.data.data || {};
      
      // Set all configuration data from API
      setAllAvailableFields(data.field_mappings || {});
      setAggregationFunctions(data.aggregation_functions || []);
      setSourceModels(data.source_models || []);
      setGroupLevels(data.group_levels || []);
    } catch (error) {
      console.error('Error fetching calculation configuration:', error);
      showToast('Error loading calculation configuration. Using default settings.', 'error');
      
      // Fallback to hardcoded configuration if API fails
      setAllAvailableFields({
        'Deal': [
          { value: 'dl_nbr', label: 'Deal Number', type: 'number' }
        ],
        'Tranche': [
          { value: 'tr_id', label: 'Tranche ID', type: 'string' },
          { value: 'dl_nbr', label: 'Deal Number', type: 'number' }
        ],
        'TrancheBal': [
          { value: 'tr_end_bal_amt', label: 'Ending Balance Amount', type: 'currency' },
          { value: 'tr_pass_thru_rte', label: 'Pass Through Rate', type: 'percentage' },
          { value: 'tr_accrl_days', label: 'Accrual Days', type: 'number' },
          { value: 'tr_int_dstrb_amt', label: 'Interest Distribution Amount', type: 'currency' },
          { value: 'tr_prin_dstrb_amt', label: 'Principal Distribution Amount', type: 'currency' },
          { value: 'tr_int_accrl_amt', label: 'Interest Accrual Amount', type: 'currency' },
          { value: 'tr_int_shtfl_amt', label: 'Interest Shortfall Amount', type: 'currency' },
          { value: 'cycle_cde', label: 'Cycle Code', type: 'number' }
        ]
      });
      
      setAggregationFunctions([
        { value: 'SUM', label: 'SUM - Total amount', description: 'Add all values together', category: 'aggregated' },
        { value: 'AVG', label: 'AVG - Average', description: 'Calculate average value', category: 'aggregated' },
        { value: 'COUNT', label: 'COUNT - Count records', description: 'Count number of records', category: 'aggregated' },
        { value: 'MIN', label: 'MIN - Minimum value', description: 'Find minimum value', category: 'aggregated' },
        { value: 'MAX', label: 'MAX - Maximum value', description: 'Find maximum value', category: 'aggregated' },
        { value: 'WEIGHTED_AVG', label: 'WEIGHTED_AVG - Weighted average', description: 'Calculate weighted average using specified weight field', category: 'aggregated' },
        { value: 'RAW', label: 'RAW - Individual field value', description: 'Show the actual field value for each row without aggregation', category: 'raw' }
      ]);
      
      setSourceModels([
        { value: 'Deal', label: 'Deal', description: 'Base deal information' },
        { value: 'Tranche', label: 'Tranche', description: 'Tranche structure data' },
        { value: 'TrancheBal', label: 'TrancheBal', description: 'Tranche balance and performance data' }
      ]);
      
      setGroupLevels([
        { value: 'deal', label: 'Deal Level', description: 'Aggregate to deal level' },
        { value: 'tranche', label: 'Tranche Level', description: 'Aggregate to tranche level' }
      ]);
    } finally {
      setFieldsLoading(false);
    }
  };

  // Get available fields for a source model
  const getAvailableFields = (sourceModel: string): CalculationField[] => {
    return allAvailableFields[sourceModel] || [];
  };

  useEffect(() => {
    fetchCalculations();
    fetchCalculationConfig();
  }, []);

  useEffect(() => {
    filterCalculations();
  }, [calculations, selectedFilter]);

  const fetchCalculations = async (): Promise<void> => {
    setIsLoading(true);
    try {
      const response = await calculationsApi.getCalculations();
      setCalculations(response.data);
    } catch (error) {
      console.error('Error fetching calculations:', error);
      showToast('Error loading calculations. Please refresh the page.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const filterCalculations = (): void => {
    let filtered = calculations;
    
    if (selectedFilter === 'deal') {
      filtered = calculations.filter(calc => calc.group_level === 'deal');
    } else if (selectedFilter === 'tranche') {
      filtered = calculations.filter(calc => calc.group_level === 'tranche');
    }
    
    setFilteredCalculations(filtered);
  };

  const handlePreviewSQL = async (calcId: number): Promise<void> => {
    setPreviewLoading(true);
    setPreviewData(null);
    setShowPreviewModal(true);
    
    try {
      const response = await calculationsApi.previewSQL(calcId, {
        group_level: 'deal',
        sample_deals: '101,102,103',
        sample_tranches: 'A,B',
        sample_cycle: '202404'
      });
      setPreviewData(response.data);
    } catch (error: any) {
      console.error('Error generating SQL preview:', error);
      showToast(`Error generating SQL preview: ${error.message}`, 'error');
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleOpenModal = (calc: Calculation | null = null): void => {
    if (calc) {
      // Edit mode
      setEditingCalculation(calc);
      setCalculation({
        name: calc.name,
        description: calc.description || '',
        function_type: calc.aggregation_function,
        source: calc.source_model,
        source_field: calc.source_field,
        level: calc.group_level,
        weight_field: calc.weight_field || ''
      });
    } else {
      // Create mode
      setEditingCalculation(null);
      setCalculation({
        name: '',
        function_type: 'SUM',
        source: '',
        source_field: '',
        level: 'deal',
        weight_field: '',
        description: ''
      });
    }
    setError(null);
    setShowModal(true);
  };

  const handleCloseModal = (): void => {
    setShowModal(false);
    setEditingCalculation(null);
    setError(null);
    setCalculation({
      name: '',
      function_type: 'SUM',
      source: '',
      source_field: '',
      level: 'deal',
      weight_field: '',
      description: ''
    });
  };

  const handleSaveCalculation = async (): Promise<void> => {
    if (!calculation.name || !calculation.function_type || !calculation.source || !calculation.source_field) {
      setError('Please fill in all required fields (Name, Function Type, Source, and Source Field)');
      return;
    }

    if (calculation.function_type === 'WEIGHTED_AVG' && !calculation.weight_field) {
      setError('Weight field is required for weighted average calculations');
      return;
    }

    setIsSaving(true);
    try {
      // Map frontend field names to backend expected field names
      const payload = {
        name: calculation.name,
        description: calculation.description,
        aggregation_function: calculation.function_type,
        source_model: calculation.source,
        source_field: calculation.source_field,
        group_level: calculation.level,
        weight_field: calculation.weight_field || null
      };

      let savedCalculation: Calculation;
      if (editingCalculation) {
        const response = await calculationsApi.updateCalculation(editingCalculation.id, { ...payload, id: editingCalculation.id });
        savedCalculation = response.data;
      } else {
        const response = await calculationsApi.createCalculation(payload);
        savedCalculation = response.data;
      }
      
      showToast(`Calculation "${savedCalculation.name}" ${editingCalculation ? 'updated' : 'saved'} successfully!`, 'success');
      
      // Close modal and refresh calculations list
      handleCloseModal();
      fetchCalculations();
    } catch (error: any) {
      console.error('Error saving calculation:', error);
      
      // Extract detailed error message from API response
      let errorMessage = 'Error saving calculation';
      
      if (error.response?.data?.detail) {
        // Backend sends detailed error in 'detail' field
        errorMessage = error.response.data.detail;
      } else if (error.response?.data?.message) {
        // Alternative error message field
        errorMessage = error.response.data.message;
      } else if (error.message) {
        // Fallback to generic error message
        errorMessage = error.message;
      }
      
      setError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteCalculation = async (id: number, name: string): Promise<void> => {
    if (!window.confirm(`Are you sure you want to delete "${name}"?`)) {
      return;
    }

    try {
      await calculationsApi.deleteCalculation(id);
      showToast(`Calculation "${name}" deleted successfully!`, 'success');
      fetchCalculations();
    } catch (error: any) {
      console.error('Error deleting calculation:', error);
      showToast(`Error deleting calculation: ${error.message}`, 'error');
    }
  };

  const getPreviewFormula = (): string => {
    if (!calculation.function_type || !calculation.source_field) {
      return 'Select aggregation function and field to see preview';
    }

    const field = `${calculation.source}.${calculation.source_field}`;
    
    if (calculation.function_type === 'WEIGHTED_AVG') {
      const weightField = calculation.weight_field ? `${calculation.source}.${calculation.weight_field}` : '[weight_field]';
      return `SUM(${field} * ${weightField}) / NULLIF(SUM(${weightField}), 0)`;
    }
    
    return `${calculation.function_type}(${field})`;
  };

  const getFullSQLPreview = (): string => {
    if (!calculation.function_type || !calculation.source || !calculation.source_field) {
      return 'Select aggregation function, source model, and field to see SQL preview';
    }

    // Build the aggregation expression
    let aggregationExpr = '';
    const sourceField = `${calculation.source.toLowerCase()}.${calculation.source_field}`;
    
    if (calculation.function_type === 'WEIGHTED_AVG') {
      const weightField = calculation.weight_field ? 
        `${calculation.source.toLowerCase()}.${calculation.weight_field}` : 
        '[weight_field_required]';
      aggregationExpr = `sum(${sourceField} * ${weightField}) / NULLIF(sum(${weightField}), 0)`;
    } else if (calculation.function_type === 'RAW') {
      aggregationExpr = sourceField;
    } else {
      aggregationExpr = `${calculation.function_type.toLowerCase()}(${sourceField})`;
    }

    // Build FROM and JOIN clauses based on required models
    const requiredModels = new Set(['Deal']); // Always need Deal
    
    // Add required models based on source
    if (calculation.source === 'Tranche' || calculation.level === 'tranche') {
      requiredModels.add('Tranche');
    }
    if (calculation.source === 'TrancheBal') {
      requiredModels.add('Tranche'); // TrancheBal requires Tranche join
      requiredModels.add('TrancheBal');
    }

    // Build GROUP BY columns for aggregated functions
    const groupByColumns = [];
    if (calculation.function_type !== 'RAW') {
      groupByColumns.push('deal.dl_nbr');
      if (requiredModels.has('TrancheBal')) {
        groupByColumns.push('tranchebal.cycle_cde');
      }
      if (calculation.level === 'tranche' && requiredModels.has('Tranche')) {
        groupByColumns.push('tranche.tr_id');
      }
    }

    // Build SELECT columns - include GROUP BY fields for aggregated calculations
    const selectColumns = [];
    
    if (calculation.function_type === 'RAW') {
      // For RAW calculations, include all relevant fields
      selectColumns.push('deal.dl_nbr AS deal_number');
      selectColumns.push('tranchebal.cycle_cde AS cycle_code');
      if (calculation.level === 'tranche') {
        selectColumns.push('tranche.tr_id AS tranche_id');
      }
    } else {
      // For aggregated calculations, include GROUP BY fields in SELECT
      selectColumns.push('deal.dl_nbr AS deal_number');
      if (requiredModels.has('TrancheBal')) {
        selectColumns.push('tranchebal.cycle_cde AS cycle_code');
      }
      if (calculation.level === 'tranche' && requiredModels.has('Tranche')) {
        selectColumns.push('tranche.tr_id AS tranche_id');
      }
    }
    
    // Add the calculation result
    const calcName = calculation.name || 'Calculation Result';
    selectColumns.push(`${aggregationExpr} AS "${calcName}"`);

    let fromClause = 'FROM deal';
    if (requiredModels.has('Tranche')) {
      fromClause += ' JOIN tranche ON deal.dl_nbr = tranche.dl_nbr';
    }
    if (requiredModels.has('TrancheBal')) {
      fromClause += ' JOIN tranchebal ON tranche.dl_nbr = tranchebal.dl_nbr AND tranche.tr_id = tranchebal.tr_id';
    }

    // Build WHERE clause
    const whereConditions = [];
    whereConditions.push("deal.dl_nbr IN (101, 102, 103)");
    if (requiredModels.has('Tranche')) {
      whereConditions.push("tranche.tr_id IN ('A', 'B')");
    }
    if (requiredModels.has('TrancheBal')) {
      whereConditions.push("tranchebal.cycle_cde = 202404");
    }

    // Build GROUP BY clause for aggregated functions
    let groupByClause = '';
    if (calculation.function_type !== 'RAW' && groupByColumns.length > 0) {
      groupByClause = ` GROUP BY ${groupByColumns.join(', ')}`;
    }

    // Combine all parts with proper formatting
    const sqlParts = [
      `SELECT ${selectColumns.join(', ')}`,
      fromClause,
      `WHERE ${whereConditions.join(' AND ')}`
    ];
    
    if (groupByClause) {
      sqlParts.push(groupByClause.trim()); // Remove leading space
    }
    
    return sqlParts.join('\n');
  };

  return (
    <div className="container-fluid">
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
      <div className="card mb-4">
        <div className="card-header bg-primary">
          <h5 className="card-title mb-0">Filter Calculations</h5>
        </div>
        <div className="card-body">
          <div className="row">
            <div className="col-md-4">
              <label className="form-label">Group Level</label>
              <select
                value={selectedFilter}
                onChange={(e) => setSelectedFilter(e.target.value)}
                className="form-select"
              >
                <option value="all">All</option>
                <option value="deal">Deal Level</option>
                <option value="tranche">Tranche Level</option>
              </select>
              <div className="form-text">Filter calculations by their group level</div>
            </div>
          </div>
        </div>
      </div>

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
              {(selectedFilter === 'all' ? calculations : filteredCalculations).map((calc) => (
                <div key={calc.id} className="col-12">
                  <div className="card border">
                    <div className="card-body">
                      <div className="d-flex justify-content-between align-items-start">
                        <div className="flex-grow-1">
                          <div className="d-flex align-items-center gap-2 mb-2">
                            <h6 className="card-title mb-0">{calc.name}</h6>
                            <span className="badge bg-primary">{calc.aggregation_function}</span>
                            <span className={`badge ${
                              calc.group_level === 'deal' ? 'bg-success' : 'bg-info'
                            }`}>
                              {calc.group_level === 'deal' ? 'Deal Level' : 'Tranche Level'}
                            </span>
                            <span className="badge bg-secondary">{calc.source_model}</span>
                          </div>
                          {calc.description && (
                            <p className="card-text text-muted mb-2">{calc.description}</p>
                          )}
                          
                          <div className="bg-light rounded p-2 mb-2">
                            <small className="text-muted">
                              <strong>Source:</strong> {calc.source_model}.{calc.source_field}
                              {calc.weight_field && (
                                <span> | <strong>Weight:</strong> {calc.source_model}.{calc.weight_field}</span>
                              )}
                            </small>
                          </div>
                          
                          <div className="d-flex align-items-center gap-1 text-muted">
                            <i className="bi bi-database"></i>
                            <small>ORM-based calculation using SQLAlchemy func.{calc.aggregation_function.toLowerCase()}</small>
                          </div>
                          
                          {calc.created_at && (
                            <div className="text-muted mt-2">
                              <small>
                                Created: {new Date(calc.created_at).toLocaleString()}
                                {calc.updated_at && calc.updated_at !== calc.created_at && (
                                  <span className="ms-3">Updated: {new Date(calc.updated_at).toLocaleString()}</span>
                                )}
                              </small>
                            </div>
                          )}
                        </div>
                        <div className="btn-group">
                          <button
                            onClick={() => handlePreviewSQL(calc.id)}
                            className="btn btn-outline-info btn-sm"
                            title="Preview SQL"
                          >
                            <i className="bi bi-eye"></i> SQL
                          </button>
                          <button
                            onClick={() => handleOpenModal(calc)}
                            className="btn btn-outline-warning btn-sm"
                            title="Edit"
                          >
                            <i className="bi bi-pencil"></i> Edit
                          </button>
                          <button
                            onClick={() => handleDeleteCalculation(calc.id, calc.name)}
                            className="btn btn-outline-danger btn-sm"
                            title="Delete"
                          >
                            <i className="bi bi-trash"></i> Delete
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              
              {(selectedFilter === 'all' ? calculations : filteredCalculations).length === 0 && !isLoading && !fieldsLoading && (
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

      {/* Create/Edit Calculation Modal */}
      {showModal && (
        <div className="modal show d-block" tabIndex={-1} style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-xl modal-dialog-scrollable">
            <div className="modal-content">
              <div className="modal-header bg-primary">
                <h5 className="modal-title">
                  {editingCalculation ? 'Edit Calculation' : 'Create New Calculation'}
                </h5>
                <button
                  type="button"
                  className="btn-close btn-close-white"
                  onClick={handleCloseModal}
                ></button>
              </div>
              
              <div className="modal-body">
                {fieldsLoading ? (
                  <div className="text-center py-4">
                    <div className="spinner-border text-primary" role="status">
                      <span className="visually-hidden">Loading...</span>
                    </div>
                    <p className="mt-2 mb-0">Loading calculation configuration...</p>
                  </div>
                ) : (
                  <>
                    {error && (
                      <div className="alert alert-danger" role="alert">
                        {error}
                      </div>
                    )}

                    <div className="row g-3">
                      {/* Basic Information */}
                      <div className="col-md-6">
                        <label className="form-label">Calculation Name *</label>
                        <input
                          type="text"
                          value={calculation.name}
                          onChange={(e) => setCalculation({ ...calculation, name: e.target.value })}
                          className="form-control"
                          placeholder="e.g., Total Ending Balance"
                        />
                      </div>

                      <div className="col-md-6">
                        <label className="form-label">Group Level *</label>
                        <select
                          value={calculation.level}
                          onChange={(e) => setCalculation({ ...calculation, level: e.target.value })}
                          className="form-select"
                        >
                          {groupLevels.map(level => (
                            <option key={level.value} value={level.value}>
                              {level.label}
                            </option>
                          ))}
                        </select>
                        <div className="form-text">
                          {groupLevels.find(l => l.value === calculation.level)?.description}
                        </div>
                      </div>

                      {/* Description */}
                      <div className="col-12">
                        <label className="form-label">Description</label>
                        <textarea
                          value={calculation.description}
                          onChange={(e) => setCalculation({ ...calculation, description: e.target.value })}
                          className="form-control"
                          rows={3}
                          placeholder="Describe what this calculation measures..."
                        />
                      </div>

                      {/* Source Configuration */}
                      <div className="col-md-6">
                        <label className="form-label">Source Model *</label>
                        <select
                          value={calculation.source}
                          onChange={(e) => setCalculation({ ...calculation, source: e.target.value, source_field: '' })}
                          className="form-select"
                        >
                          <option value="">Select a source model...</option>
                          {sourceModels.map(model => (
                            <option key={model.value} value={model.value}>
                              {model.label}
                            </option>
                          ))}
                        </select>
                        <div className="form-text">
                          {sourceModels.find(m => m.value === calculation.source)?.description}
                        </div>
                      </div>

                      <div className="col-md-6">
                        <label className="form-label">Aggregation Function *</label>
                        <select
                          value={calculation.function_type}
                          onChange={(e) => setCalculation({ ...calculation, function_type: e.target.value })}
                          className="form-select"
                        >
                          {aggregationFunctions.map(func => (
                            <option key={func.value} value={func.value}>
                              {func.label}
                            </option>
                          ))}
                        </select>
                        <div className="form-text">
                          {aggregationFunctions.find(f => f.value === calculation.function_type)?.description}
                        </div>
                      </div>

                      {/* Field Selection */}
                      <div className="col-md-6">
                        <label className="form-label">Source Field *</label>
                        {fieldsLoading ? (
                          <div className="form-control d-flex align-items-center">
                            <div className="spinner-border spinner-border-sm me-2" role="status">
                              <span className="visually-hidden">Loading...</span>
                            </div>
                            <span className="text-muted">Loading fields...</span>
                          </div>
                        ) : (
                          <select
                            value={calculation.source_field}
                            onChange={(e) => setCalculation({ ...calculation, source_field: e.target.value })}
                            className="form-select"
                            disabled={!calculation.source || getAvailableFields(calculation.source).length === 0}
                          >
                            <option value="">Select a field...</option>
                            {getAvailableFields(calculation.source).map(field => (
                              <option key={field.value} value={field.value}>
                                {field.label} ({field.type})
                              </option>
                            ))}
                          </select>
                        )}
                        <div className="form-text">
                          {calculation.source ? `Available fields from ${calculation.source} model` : 'Select a source model first'}
                        </div>
                        {/* Show field description if available */}
                        {calculation.source_field && getAvailableFields(calculation.source).find(f => f.value === calculation.source_field)?.description && (
                          <div className="form-text text-info">
                            {getAvailableFields(calculation.source).find(f => f.value === calculation.source_field)?.description}
                          </div>
                        )}
                      </div>

                      {/* Weight Field for Weighted Average */}
                      {calculation.function_type === 'WEIGHTED_AVG' && (
                        <div className="col-md-6">
                          <label className="form-label">Weight Field *</label>
                          {fieldsLoading ? (
                            <div className="form-control d-flex align-items-center">
                              <div className="spinner-border spinner-border-sm me-2" role="status">
                                <span className="visually-hidden">Loading...</span>
                              </div>
                              <span className="text-muted">Loading fields...</span>
                            </div>
                          ) : (
                            <select
                              value={calculation.weight_field}
                              onChange={(e) => setCalculation({ ...calculation, weight_field: e.target.value })}
                              className="form-select"
                              disabled={!calculation.source || getAvailableFields(calculation.source).length === 0}
                            >
                              <option value="">Select weight field...</option>
                              {getAvailableFields(calculation.source).filter(f => f.type === 'currency' || f.type === 'number').map(field => (
                                <option key={field.value} value={field.value}>
                                  {field.label}
                                </option>
                              ))}
                            </select>
                          )}
                          <div className="form-text">
                            Field to use as weight for the weighted average calculation
                          </div>
                          {/* Show weight field description if available */}
                          {calculation.weight_field && getAvailableFields(calculation.source).find(f => f.value === calculation.weight_field)?.description && (
                            <div className="form-text text-info">
                              {getAvailableFields(calculation.source).find(f => f.value === calculation.weight_field)?.description}
                            </div>
                          )}
                        </div>
                      )}

                      {/* ORM Formula Preview */}
                      <div className="col-12">
                        <label className="form-label">Generated ORM Formula Preview</label>
                        <div className="bg-light rounded p-3 border">
                          <code className="text-dark">{getPreviewFormula()}</code>
                        </div>
                        <div className="form-text">
                          <strong>Model:</strong> {calculation.source} | 
                          <strong> Function:</strong> {calculation.function_type} | 
                          <strong> Level:</strong> {calculation.level}
                        </div>
                      </div>

                      {/* Full SQL Preview */}
                      <div className="col-12">
                        <label className="form-label">Complete SQL Query Preview</label>
                        <div className="bg-dark text-light rounded p-3 border" style={{ fontFamily: 'monospace' }}>
                          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: '0.85rem' }}>
                            {getFullSQLPreview()}
                          </pre>
                        </div>
                        <div className="form-text text-muted">
                          This shows the complete SQL query that will be executed when this calculation runs in a report, 
                          including all result fields and proper JOIN relationships.
                        </div>
                      </div>
                    </div>
                  </>
                )}
              </div>

              {/* Modal Footer */}
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleCloseModal}
                  disabled={isSaving || fieldsLoading}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveCalculation}
                  disabled={isSaving || fieldsLoading}
                  className="btn btn-success"
                >
                  {isSaving ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-2" role="status"></span>
                      Saving...
                    </>
                  ) : (
                    <>
                      <i className="bi bi-save me-2"></i>
                      {editingCalculation ? 'Update Calculation' : 'Save Calculation'}

      {/* SQL Preview Modal */}
      {showPreviewModal && (
        <div className="modal show d-block" tabIndex={-1} style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-xl modal-dialog-scrollable">
            <div className="modal-content" style={{ borderRadius: '12px', overflow: 'hidden' }}>
              <div 
                className="modal-header bg-primary"
              >
                <h5 className="modal-title">
                  <i className="bi bi-code-square me-2"></i>
                  SQL Preview
                </h5>
                <button
                  type="button"
                  className="btn-close btn-close-white"
                  onClick={() => setShowPreviewModal(false)}
                ></button>
              </div>
              
              <div className="modal-body" style={{ padding: '1.5rem' }}>
                {previewLoading ? (
                  <div 
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'center',
                      alignItems: 'center',
                      padding: '3rem 0'
                    }}
                  >
                    <div className="spinner-border text-primary mb-3" role="status">
                      <span className="visually-hidden">Loading...</span>
                    </div>
                    <span style={{ color: '#6c757d', fontSize: '0.9rem' }}>
                      Generating SQL preview...
                    </span>
                  </div>
                ) : previewData ? (
                  <div>
                    {/* Calculation Details */}
                    <div 
                      style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                        gap: '1rem',
                        marginBottom: '1.5rem'
                      }}
                    >
                      <div 
                        style={{
                          backgroundColor: '#f8f9fa',
                          borderRadius: '8px',
                          padding: '1rem',
                          border: '1px solid #e9ecef'
                        }}
                      >
                        <h6 
                          style={{
                            color: '#6c757d',
                            fontSize: '0.875rem',
                            fontWeight: '600',
                            marginBottom: '0.5rem',
                            textTransform: 'uppercase',
                            letterSpacing: '0.5px'
                          }}
                        >
                          Calculation Details
                        </h6>
                        <div style={{ fontSize: '0.9rem', color: '#495057' }}>
                          <div className="mb-2">
                            <strong>Name:</strong> {previewData.calculation_name}
                          </div>
                          <div>
                            <strong>Level:</strong>{' '}
                            <span 
                              style={{
                                display: 'inline-block',
                                padding: '0.25em 0.6em',
                                fontSize: '0.75em',
                                fontWeight: '700',
                                backgroundColor: '#6c757d',
                                color: '#fff',
                                borderRadius: '0.375rem'
                              }}
                            >
                              {previewData.aggregation_level}
                            </span>
                          </div>
                        </div>
                      </div>
                      
                      <div 
                        style={{
                          backgroundColor: '#f8f9fa',
                          borderRadius: '8px',
                          padding: '1rem',
                          border: '1px solid #e9ecef'
                        }}
                      >
                        <h6 
                          style={{
                            color: '#6c757d',
                            fontSize: '0.875rem',
                            fontWeight: '600',
                            marginBottom: '0.5rem',
                            textTransform: 'uppercase',
                            letterSpacing: '0.5px'
                          }}
                        >
                          Sample Parameters
                        </h6>
                        <div style={{ fontSize: '0.9rem', color: '#495057' }}>
                          <div className="mb-1">
                            <strong>Deals:</strong> {previewData.sample_parameters?.deals?.join(', ') || 'N/A'}
                          </div>
                          <div className="mb-1">
                            <strong>Tranches:</strong> {previewData.sample_parameters?.tranches?.join(', ') || 'N/A'}
                          </div>
                          <div>
                            <strong>Cycle:</strong> {previewData.sample_parameters?.cycle || 'N/A'}
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    {/* SQL Query */}
                    <div className="mb-3">
                      <div 
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          marginBottom: '0.75rem'
                        }}
                      >
                        <h6 
                          style={{
                            color: '#6c757d',
                            fontSize: '0.875rem',
                            fontWeight: '600',
                            marginBottom: '0',
                            textTransform: 'uppercase',
                            letterSpacing: '0.5px'
                          }}
                        >
                          Raw Execution SQL
                        </h6>
                        <button
                          className="btn btn-sm btn-outline-secondary"
                          onClick={() => {
                            if (previewData?.generated_sql) {
                              navigator.clipboard.writeText(previewData.generated_sql);
                            }
                          }}
                          title="Copy SQL to clipboard"
                          style={{
                            border: '1px solid #dee2e6',
                            backgroundColor: '#ffffff',
                            color: '#495057'
                          }}
                        >
                          <i className="bi bi-clipboard me-1"></i>
                          Copy
                        </button>
                      </div>
                      <div 
                        style={{
                          backgroundColor: '#ffffff',
                          color: '#212529',
                          border: '1px solid #dee2e6',
                          borderRadius: '8px',
                          padding: '1rem',
                          maxHeight: '400px',
                          overflowY: 'auto',
                          fontFamily: "'Consolas', 'Monaco', 'Courier New', monospace",
                          boxShadow: 'inset 0 1px 3px rgba(0, 0, 0, 0.1)'
                        }}
                      >
                        <pre 
                          style={{ 
                            fontSize: '0.875rem',
                            lineHeight: '1.4',
                            margin: '0',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word',
                            color: '#212529'
                          }}
                        >
                          {previewData.generated_sql}
                        </pre>
                      </div>
                      <div 
                        style={{
                          fontSize: '0.8rem',
                          color: '#6c757d',
                          marginTop: '0.5rem',
                          fontStyle: 'italic'
                        }}
                      >
                        This is the exact same SQL that executes when this calculation runs in a report.
                      </div>
                    </div>
                  </div>
                ) : (
                  <div 
                    style={{
                      textAlign: 'center',
                      padding: '3rem 0',
                      color: '#6c757d'
                    }}
                  >
                    <i 
                      className="bi bi-exclamation-circle"
                      style={{
                        fontSize: '3rem',
                        marginBottom: '1rem',
                        display: 'block'
                      }}
                    ></i>
                    <p>No preview data available</p>
                  </div>
                )}
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowPreviewModal(false)}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CalculationBuilder;