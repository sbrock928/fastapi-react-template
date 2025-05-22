import React, { useState, useEffect, useCallback } from 'react';
import { reportsApi } from '@/services/api';
import { useToast } from '@/context/ToastContext';
import OverrideCell from './OverrideCell';
import OverrideNotesModal from './OverrideNotesModal';
import type { 
  Tranche, 
  TrancheOverride, 
  OverrideableColumn, 
  OverrideSummary 
} from '@/types';

interface TrancheOverridesStepProps {
  reportId?: number; // For editing existing reports
  selectedTranches: Record<number, number[]>; // dealId -> trancheIds[]
  tranches: Record<number, Tranche[]>; // dealId -> Tranche[]
  onOverridesChange: (overrides: TrancheOverride[]) => void;
  initialOverrides?: TrancheOverride[];
}

const TrancheOverridesStep: React.FC<TrancheOverridesStepProps> = ({
  reportId,
  selectedTranches,
  tranches,
  onOverridesChange,
  initialOverrides = []
}) => {
  const { showToast } = useToast();
  
  // State
  const [overrideableColumns, setOverrideableColumns] = useState<OverrideableColumn[]>([]);
  const [activeOverrides, setActiveOverrides] = useState<TrancheOverride[]>(initialOverrides);
  const [loading, setLoading] = useState(false);
  const [overrideSummary, setOverrideSummary] = useState<OverrideSummary | null>(null);
  
  // Modal states
  const [showNotesModal, setShowNotesModal] = useState(false);
  const [selectedTrancheForNotes, setSelectedTrancheForNotes] = useState<number | null>(null);
  
  // Import/Export states
  const [showImportModal, setShowImportModal] = useState(false);
  const [csvData, setCsvData] = useState('');
  const [importLoading, setImportLoading] = useState(false);

  // Get flat list of all selected tranches
  const allSelectedTranches = React.useMemo(() => {
    const trancheList: Tranche[] = [];
    Object.entries(selectedTranches).forEach(([dealIdStr, trancheIds]) => {
      const dealId = parseInt(dealIdStr);
      const dealTranches = tranches[dealId] || [];
      trancheIds.forEach(trancheId => {
        const tranche = dealTranches.find(t => t.id === trancheId);
        if (tranche) {
          trancheList.push(tranche);
        }
      });
    });
    return trancheList.sort((a, b) => `${a.deal_id}-${a.name}`.localeCompare(`${b.deal_id}-${b.name}`));
  }, [selectedTranches, tranches]);

  // Load overrideable columns
  useEffect(() => {
    const loadOverrideableColumns = async () => {
      try {
        const response = await reportsApi.getOverrideableColumns('tranche');
        setOverrideableColumns(response.data);
      } catch (error) {
        console.error('Error loading overrideable columns:', error);
        showToast('Error loading overrideable columns', 'error');
      }
    };

    loadOverrideableColumns();
  }, []);

  // Load existing overrides for edit mode
  useEffect(() => {
    if (reportId) {
      loadExistingOverrides();
    }
  }, [reportId]);

  // Notify parent of override changes
  useEffect(() => {
    onOverridesChange(activeOverrides);
  }, [activeOverrides, onOverridesChange]);

  const loadExistingOverrides = async () => {
    if (!reportId) return;
    
    try {
      const [overridesResponse, summaryResponse] = await Promise.all([
        reportsApi.getReportOverrides(reportId),
        reportsApi.getOverrideSummary(reportId)
      ]);
      
      setActiveOverrides(overridesResponse.data);
      setOverrideSummary(summaryResponse.data);
    } catch (error) {
      console.error('Error loading existing overrides:', error);
      showToast('Error loading existing overrides', 'error');
    }
  };

  const handleOverrideChange = useCallback(async (
    trancheId: number,
    columnName: string,
    value: any,
    notes?: string
  ) => {
    if (!reportId) {
      // For new reports, just update local state
      const existingIndex = activeOverrides.findIndex(
        o => o.tranche_id === trancheId && o.column_name === columnName
      );

      if (value === null || value === undefined || value === '') {
        // Remove override
        if (existingIndex >= 0) {
          setActiveOverrides(prev => prev.filter((_, i) => i !== existingIndex));
        }
      } else {
        // Add or update override
        const newOverride: TrancheOverride = {
          tranche_id: trancheId,
          column_name: columnName,
          override_value: value,
          override_type: 'manual',
          notes: notes || ''
        };

        if (existingIndex >= 0) {
          setActiveOverrides(prev => prev.map((override, i) => 
            i === existingIndex ? newOverride : override
          ));
        } else {
          setActiveOverrides(prev => [...prev, newOverride]);
        }
      }
    } else {
      // For existing reports, save to backend
      try {
        if (value === null || value === undefined || value === '') {
          await reportsApi.clearTrancheOverride(reportId, trancheId, columnName);
          setActiveOverrides(prev => prev.filter(
            o => !(o.tranche_id === trancheId && o.column_name === columnName)
          ));
          showToast('Override cleared', 'success');
        } else {
          const overrideData = {
            tranche_id: trancheId,
            column_name: columnName,
            override_value: value,
            override_type: 'manual' as const,
            notes: notes || '',
            created_by: 'current_user' // TODO: Get from auth context
          };

          const response = await reportsApi.setTrancheOverride(reportId, overrideData);
          
          // Update local state
          const existingIndex = activeOverrides.findIndex(
            o => o.tranche_id === trancheId && o.column_name === columnName
          );

          if (existingIndex >= 0) {
            setActiveOverrides(prev => prev.map((override, i) => 
              i === existingIndex ? response.data : override
            ));
          } else {
            setActiveOverrides(prev => [...prev, response.data]);
          }
          
          showToast('Override saved', 'success');
        }
      } catch (error) {
        console.error('Error saving override:', error);
        showToast('Error saving override', 'error');
      }
    }
  }, [reportId, activeOverrides, showToast]);

  const getOverrideValue = (trancheId: number, columnName: string): any => {
    const override = activeOverrides.find(
      o => o.tranche_id === trancheId && o.column_name === columnName
    );
    return override?.override_value;
  };

  const getCalculatedValue = (trancheId: number, columnName: string): any => {
    // This would normally fetch from the backend or calculate based on tranche data
    const tranche = allSelectedTranches.find(t => t.id === trancheId);
    if (!tranche) return null;

    // Map common column names to tranche properties
    switch (columnName) {
      case 'principal_amount':
        return tranche.principal_amount;
      case 'interest_rate':
        return tranche.interest_rate;
      case 'credit_rating':
        return tranche.credit_rating;
      case 'payment_priority':
        return tranche.payment_priority;
      default:
        return null; // Would be calculated or fetched from backend
    }
  };

  const handleResetAll = async () => {
    if (!window.confirm('Are you sure you want to reset all overrides? This action cannot be undone.')) {
      return;
    }

    try {
      if (reportId) {
        await reportsApi.clearAllReportOverrides(reportId);
      }
      setActiveOverrides([]);
      showToast('All overrides reset', 'success');
    } catch (error) {
      console.error('Error resetting overrides:', error);
      showToast('Error resetting overrides', 'error');
    }
  };

  const handleExportTemplate = async () => {
    try {
      setLoading(true);
      const response = reportId 
        ? await reportsApi.exportOverridesToCsv(reportId)
        : await generateLocalTemplate();
      
      // Download CSV file
      const blob = new Blob([response.csv_content], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = response.filename || 'overrides_template.csv';
      link.click();
      URL.revokeObjectURL(url);
      
      showToast('Template exported successfully', 'success');
    } catch (error) {
      console.error('Error exporting template:', error);
      showToast('Error exporting template', 'error');
    } finally {
      setLoading(false);
    }
  };

  const generateLocalTemplate = async () => {
    // Generate template for new reports
    const rows: any[] = [];
    
    allSelectedTranches.forEach(tranche => {
      overrideableColumns.forEach(col => {
        rows.push({
          tranche_id: tranche.id,
          tranche_name: tranche.name,
          column_name: col.key,
          column_label: col.label,
          data_type: col.data_type,
          override_value: '',
          override_type: 'manual',
          notes: '',
          calculation_description: col.calculation_description
        });
      });
    });

    const csv = [
      Object.keys(rows[0] || {}).join(','),
      ...rows.map(row => Object.values(row).map(v => `"${v}"`).join(','))
    ].join('\n');

    return {
      csv_content: csv,
      filename: 'new_report_overrides_template.csv'
    };
  };

  const handleImportOverrides = async () => {
    if (!csvData.trim()) {
      showToast('Please paste CSV data to import', 'warning');
      return;
    }

    setImportLoading(true);
    try {
      if (reportId) {
        const response = await reportsApi.importOverridesFromCsv(reportId, csvData, false);
        showToast(`Imported ${response.imported_count} overrides`, 'success');
        await loadExistingOverrides(); // Reload
      } else {
        // Parse CSV for new reports
        const lines = csvData.trim().split('\n');
        const headers = lines[0].split(',').map(h => h.replace(/"/g, '').trim());
        const newOverrides: TrancheOverride[] = [];

        for (let i = 1; i < lines.length; i++) {
          const values = lines[i].split(',').map(v => v.replace(/"/g, '').trim());
          const row: any = {};
          
          headers.forEach((header, index) => {
            row[header] = values[index] || '';
          });

          if (row.tranche_id && row.column_name && row.override_value) {
            newOverrides.push({
              tranche_id: parseInt(row.tranche_id),
              column_name: row.column_name,
              override_value: row.override_value,
              override_type: row.override_type || 'manual',
              notes: row.notes || ''
            });
          }
        }

        setActiveOverrides(prev => [...prev, ...newOverrides]);
        showToast(`Imported ${newOverrides.length} overrides`, 'success');
      }

      setShowImportModal(false);
      setCsvData('');
    } catch (error) {
      console.error('Error importing overrides:', error);
      showToast('Error importing overrides', 'error');
    } finally {
      setImportLoading(false);
    }
  };

  const openNotesModal = (trancheId: number) => {
    setSelectedTrancheForNotes(trancheId);
    setShowNotesModal(true);
  };

  const formatValue = (value: any, dataType: string): string => {
    if (value === null || value === undefined) return '';
    
    switch (dataType) {
      case 'currency':
        return new Intl.NumberFormat('en-US', { 
          style: 'currency', 
          currency: 'USD',
          notation: 'compact'
        }).format(Number(value));
      case 'percentage':
        return `${(Number(value) * 100).toFixed(2)}%`;
      case 'number':
        return Number(value).toLocaleString();
      default:
        return String(value);
    }
  };

  if (allSelectedTranches.length === 0) {
    return (
      <div className="alert alert-info">
        <i className="bi bi-info-circle me-2"></i>
        No tranches selected. Please select tranches in the previous step to configure overrides.
      </div>
    );
  }

  return (
    <div>
      <h5 className="mb-3">Step 4: Manual Overrides & Mappings</h5>
      <p className="text-muted">
        Set manual values for specific tranches when automated calculations need adjustment
        or when bridging data gaps between tables.
      </p>

      {/* Override Summary Card */}
      <div className="card mb-3 border-info">
        <div className="card-header bg-info text-white">
          <h6 className="mb-0">Override Summary</h6>
        </div>
        <div className="card-body">
          <div className="row">
            <div className="col-md-3">
              <strong>Total Tranches:</strong> {allSelectedTranches.length}
            </div>
            <div className="col-md-3">
              <strong>Overrideable Columns:</strong> {overrideableColumns.length}
            </div>
            <div className="col-md-3">
              <strong>Active Overrides:</strong> {activeOverrides.length}
            </div>
            <div className="col-md-3">
              <button 
                className="btn btn-sm btn-outline-secondary"
                onClick={handleExportTemplate}
                disabled={loading}
              >
                <i className="bi bi-download"></i> Export Template
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Overrides Table */}
      <div className="card">
        <div className="card-header">
          <div className="d-flex justify-content-between align-items-center">
            <h6 className="mb-0">Tranche Value Overrides</h6>
            <div className="btn-group btn-group-sm">
              <button 
                className="btn btn-outline-primary"
                onClick={() => setShowImportModal(true)}
              >
                <i className="bi bi-upload"></i> Import Overrides
              </button>
              <button 
                className="btn btn-outline-secondary"
                onClick={handleResetAll}
              >
                <i className="bi bi-arrow-clockwise"></i> Reset All
              </button>
            </div>
          </div>
        </div>
        <div className="card-body p-0">
          <div className="table-responsive" style={{ maxHeight: '500px' }}>
            <table className="table table-sm table-hover mb-0">
              <thead className="sticky-top bg-light">
                <tr>
                  <th style={{ minWidth: '200px' }}>Tranche</th>
                  {overrideableColumns.map(col => (
                    <th key={col.key} style={{ minWidth: '120px' }}>
                      {col.label}
                      {col.calculation_description && (
                        <i 
                          className="bi bi-info-circle ms-1" 
                          title={col.calculation_description}
                        ></i>
                      )}
                    </th>
                  ))}
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                {allSelectedTranches.map(tranche => (
                  <tr key={tranche.id}>
                    <td>
                      <div className="fw-bold">{tranche.name}</div>
                      <div className="small text-muted">{tranche.class_name}</div>
                    </td>
                    {overrideableColumns.map(col => (
                      <td key={col.key}>
                        <OverrideCell 
                          tranche={tranche}
                          column={col}
                          currentValue={getCalculatedValue(tranche.id, col.key)}
                          overrideValue={getOverrideValue(tranche.id, col.key)}
                          onOverrideChange={handleOverrideChange}
                          formatValue={formatValue}
                        />
                      </td>
                    ))}
                    <td>
                      <button 
                        className="btn btn-sm btn-outline-secondary"
                        onClick={() => openNotesModal(tranche.id)}
                        title="Add notes for this tranche"
                      >
                        <i className="bi bi-chat-text"></i>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="mt-3">
        <small className="text-muted">
          <span className="badge bg-light text-dark me-2">
            <i className="bi bi-calculator me-1"></i>Calculated
          </span>
          <span className="badge bg-warning text-dark me-2">
            <i className="bi bi-pencil me-1"></i>Manual Override
          </span>
          <span className="badge bg-info text-dark me-2">
            <i className="bi bi-arrow-left-right me-1"></i>Mapped Value
          </span>
        </small>
      </div>

      {/* Import Modal */}
      {showImportModal && (
        <div className="modal fade show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-lg">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Import Overrides</h5>
                <button 
                  type="button" 
                  className="btn-close" 
                  onClick={() => setShowImportModal(false)}
                ></button>
              </div>
              <div className="modal-body">
                <div className="mb-3">
                  <label htmlFor="csvData" className="form-label">CSV Data</label>
                  <textarea
                    id="csvData"
                    className="form-control"
                    rows={10}
                    value={csvData}
                    onChange={(e) => setCsvData(e.target.value)}
                    placeholder="Paste your CSV data here..."
                  />
                  <div className="form-text">
                    Expected columns: tranche_id, column_name, override_value, override_type, notes
                  </div>
                </div>
              </div>
              <div className="modal-footer">
                <button 
                  type="button" 
                  className="btn btn-secondary" 
                  onClick={() => setShowImportModal(false)}
                >
                  Cancel
                </button>
                <button 
                  type="button" 
                  className="btn btn-primary"
                  onClick={handleImportOverrides}
                  disabled={importLoading || !csvData.trim()}
                >
                  {importLoading ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-2"></span>
                      Importing...
                    </>
                  ) : (
                    'Import Overrides'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Notes Modal */}
      {showNotesModal && selectedTrancheForNotes && (
        <OverrideNotesModal
          trancheId={selectedTrancheForNotes}
          tranche={allSelectedTranches.find(t => t.id === selectedTrancheForNotes)!}
          activeOverrides={activeOverrides.filter(o => o.tranche_id === selectedTrancheForNotes)}
          onClose={() => {
            setShowNotesModal(false);
            setSelectedTrancheForNotes(null);
          }}
          onNotesUpdate={handleOverrideChange}
        />
      )}
    </div>
  );
};

export default TrancheOverridesStep;