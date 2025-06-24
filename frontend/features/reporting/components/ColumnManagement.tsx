import React, { useState, useCallback } from 'react';
import { Eye, EyeOff, GripVertical, ArrowUp, ArrowDown } from 'lucide-react';
import type { 
  ReportColumnPreferences,
  ReportCalculation,
  ReportScope
} from '@/types/reporting';
import { 
  ColumnFormat, 
  SortDirection,
  getColumnFormatLabel, 
  getDefaultColumnPreferences,
  addColumnSort,
  removeColumnSort,
  updateColumnSortDirection,
  getColumnSortInfo
} from '@/types/reporting';

interface ColumnManagementProps {
  calculations: ReportCalculation[];
  reportScope: ReportScope;
  columnPreferences?: ReportColumnPreferences;
  onColumnPreferencesChange: (preferences: ReportColumnPreferences) => void;
}

const ColumnManagement: React.FC<ColumnManagementProps> = ({
  calculations,
  reportScope,
  columnPreferences,
  onColumnPreferencesChange
}) => {
  // Initialize column preferences if not provided
  const [preferences, setPreferences] = useState<ReportColumnPreferences>(() => {
    return columnPreferences || getDefaultColumnPreferences(calculations, reportScope, true);
  });

  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);

  // Update parent when preferences change
  const updatePreferences = useCallback((newPreferences: ReportColumnPreferences) => {
    setPreferences(newPreferences);
    onColumnPreferencesChange(newPreferences);
  }, [onColumnPreferencesChange]);

  // Handle drag start
  const handleDragStart = (e: React.DragEvent, index: number) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = 'move';
  };

  // Handle drag over
  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    if (draggedIndex !== null && draggedIndex !== index) {
      setDragOverIndex(index);
    }
  };

  // Handle drag drop
  const handleDrop = (e: React.DragEvent, dropIndex: number) => {
    e.preventDefault();
    
    if (draggedIndex === null || draggedIndex === dropIndex) {
      setDraggedIndex(null);
      setDragOverIndex(null);
      return;
    }

    const newColumns = [...preferences.columns];
    const draggedColumn = newColumns[draggedIndex];
    
    // Remove dragged item
    newColumns.splice(draggedIndex, 1);
    
    // Insert at new position
    const insertIndex = draggedIndex < dropIndex ? dropIndex - 1 : dropIndex;
    newColumns.splice(insertIndex, 0, draggedColumn);
    
    // Update display_order
    newColumns.forEach((col, index) => {
      col.display_order = index;
    });

    updatePreferences({
      ...preferences,
      columns: newColumns
    });

    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  // Handle drag end
  const handleDragEnd = () => {
    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  // Toggle column visibility
  const toggleColumnVisibility = (index: number) => {
    const newColumns = [...preferences.columns];
    newColumns[index].is_visible = !newColumns[index].is_visible;
    
    updatePreferences({
      ...preferences,
      columns: newColumns
    });
  };

  // Update column display name
  const updateColumnDisplayName = (index: number, displayName: string) => {
    const newColumns = [...preferences.columns];
    newColumns[index].display_name = displayName;
    
    updatePreferences({
      ...preferences,
      columns: newColumns
    });
  };

  // Update column format
  const updateColumnFormat = (index: number, formatType: ColumnFormat) => {
    const newColumns = [...preferences.columns];
    newColumns[index].format_type = formatType;
    
    updatePreferences({
      ...preferences,
      columns: newColumns
    });
  };

  // Update column precision
  const updateColumnPrecision = (index: number, precision: number) => {
    const newColumns = [...preferences.columns];
    newColumns[index].precision = Math.max(0, Math.min(10, precision)); // Clamp between 0-10
    
    updatePreferences({
      ...preferences,
      columns: newColumns
    });
  };

  // Update column rounding
  const updateColumnRounding = (index: number, useRounding: boolean) => {
    const newColumns = [...preferences.columns];
    newColumns[index].use_rounding = useRounding;
    
    updatePreferences({
      ...preferences,
      columns: newColumns
    });
  };

  // Add or remove column sort
  const toggleColumnSort = (columnId: string) => {
    const sortInfo = getColumnSortInfo(preferences, columnId);
    
    if (sortInfo.isSorted) {
      // If already sorted, remove sort
      const updatedPreferences = removeColumnSort(preferences, columnId);
      updatePreferences(updatedPreferences);
    } else {
      // Otherwise, add sort (default to ascending)
      const updatedPreferences = addColumnSort(preferences, columnId, SortDirection.ASC);
      updatePreferences(updatedPreferences);
    }
  };

  // Update sort direction
  const changeSortDirection = (columnId: string) => {
    const sortInfo = getColumnSortInfo(preferences, columnId);
    if (sortInfo.isSorted) {
      const newDirection = sortInfo.direction === SortDirection.ASC ? SortDirection.DESC : SortDirection.ASC;
      const updatedPreferences = updateColumnSortDirection(preferences, columnId, newDirection);
      updatePreferences(updatedPreferences);
    }
  };

  return (
    <div className="column-management">
      <div className="d-flex align-items-center justify-content-between mb-3">
        <h6 className="mb-0">Column Management</h6>
        <small className="text-muted">
          Drag to reorder • Click eye to show/hide • Adjust formatting
        </small>
      </div>

      {/* Column List */}
      <div className="column-list">
        {preferences.columns.map((column, index) => {
          const isDragging = draggedIndex === index;
          const isDragOver = dragOverIndex === index;
          const isDefaultColumn = ['deal_number', 'tranche_id', 'cycle_code'].includes(column.column_id);
          const sortInfo = getColumnSortInfo(preferences, column.column_id);
          
          return (
            <div
              key={`${column.column_id}-${index}`}
              className={`card mb-2 column-item ${isDragging ? 'dragging' : ''} ${isDragOver ? 'drag-over' : ''}`}
              draggable
              onDragStart={(e) => handleDragStart(e, index)}
              onDragOver={(e) => handleDragOver(e, index)}
              onDrop={(e) => handleDrop(e, index)}
              onDragEnd={handleDragEnd}
              style={{
                opacity: isDragging ? 0.5 : 1,
                border: isDragOver ? '2px dashed #007bff' : undefined,
                cursor: 'move'
              }}
            >
              <div className="card-body py-2">
                <div className="row align-items-center">
                  {/* Drag Handle */}
                  <div className="col-auto">
                    <GripVertical size={16} className="text-muted drag-handle" />
                  </div>

                  {/* Column Info */}
                  <div className="col">
                    <div className="row align-items-center">
                      {/* Column Name - Fixed width */}
                      <div className="col-md-3">
                        <input
                          type="text"
                          className="form-control form-control-sm"
                          value={column.display_name}
                          onChange={(e) => updateColumnDisplayName(index, e.target.value)}
                          placeholder="Column name"
                        />
                        {isDefaultColumn && (
                          <small className="text-muted">Default column</small>
                        )}
                      </div>
                      
                      {/* Format Selection - Fixed width */}
                      <div className="col-md-2">
                        <select
                          className="form-select form-select-sm"
                          value={column.format_type}
                          onChange={(e) => updateColumnFormat(index, e.target.value as ColumnFormat)}
                        >
                          {Object.values(ColumnFormat).map(format => (
                            <option key={format} value={format}>
                              {getColumnFormatLabel(format)}
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* Precision and Rounding Controls - Fixed width with min-height for alignment */}
                      <div className="col-md-2" style={{ minHeight: '58px' }}>
                        {(column.format_type === ColumnFormat.CURRENCY || 
                          column.format_type === ColumnFormat.PERCENTAGE || 
                          column.format_type === ColumnFormat.NUMBER) ? (
                          <div className="row g-1">
                            <div className="col-7">
                              <input
                                type="number"
                                className="form-control form-control-sm"
                                value={column.precision || 2}
                                onChange={(e) => updateColumnPrecision(index, parseInt(e.target.value) || 0)}
                                min="0"
                                max="10"
                                title="Decimal places"
                                style={{ fontSize: '0.75rem' }}
                              />
                              <small className="text-muted">Precision</small>
                            </div>
                            <div className="col-5">
                              <div className="form-check form-check-sm">
                                <input
                                  className="form-check-input"
                                  type="checkbox"
                                  checked={column.use_rounding !== false}
                                  onChange={(e) => updateColumnRounding(index, e.target.checked)}
                                  title="Round vs Truncate"
                                />
                                <small className="text-muted">Round</small>
                              </div>
                            </div>
                          </div>
                        ) : (
                          <div className="d-flex align-items-center justify-content-center h-100">
                            <small className="text-muted">—</small>
                          </div>
                        )}
                      </div>
                      
                      {/* Order Badge - Fixed width */}
                      <div className="col-md-1 text-center">
                        <span className="badge bg-secondary">
                          #{column.display_order + 1}
                        </span>
                      </div>
                      
                      {/* Visibility Toggle - Fixed width */}
                      <div className="col-md-1 text-center">
                        <button
                          type="button"
                          className={`btn btn-sm ${column.is_visible ? 'btn-success' : 'btn-outline-secondary'}`}
                          onClick={() => toggleColumnVisibility(index)}
                          title={column.is_visible ? 'Hide column' : 'Show column'}
                        >
                          {column.is_visible ? <Eye size={14} /> : <EyeOff size={14} />}
                        </button>
                      </div>
                      
                      {/* Sort Controls - Fixed width */}
                      <div className="col-md-2">
                        <div className="d-flex align-items-center gap-1">
                          <button
                            type="button"
                            className={`btn btn-sm ${sortInfo.isSorted ? 'btn-primary' : 'btn-outline-secondary'}`}
                            onClick={() => {
                              if (sortInfo.isSorted) {
                                if (sortInfo.direction === SortDirection.ASC) {
                                  changeSortDirection(column.column_id);
                                } else {
                                  toggleColumnSort(column.column_id);
                                }
                              } else {
                                toggleColumnSort(column.column_id);
                              }
                            }}
                            title={
                              sortInfo.isSorted 
                                ? (sortInfo.direction === SortDirection.ASC 
                                    ? 'Click to sort descending' 
                                    : 'Click to remove sort')
                                : 'Click to sort ascending'
                            }
                          >
                            {sortInfo.isSorted ? (
                              sortInfo.direction === SortDirection.ASC ? (
                                <ArrowUp size={14} />
                              ) : (
                                <ArrowDown size={14} />
                              )
                            ) : (
                              '⇅'
                            )}
                          </button>
                          
                          {sortInfo.isSorted && (
                            <span className="badge bg-info" style={{ fontSize: '0.7rem' }}>
                              {sortInfo.sortOrder !== undefined ? sortInfo.sortOrder + 1 : ''}
                            </span>
                          )}
                        </div>
                      </div>
                      
                      {/* Column ID - Remaining space */}
                      <div className="col-md-1">
                        <small className="text-muted text-truncate d-block" title={column.column_id}>
                          {column.column_id}
                        </small>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Sorting Summary */}
      {preferences.sort_config && preferences.sort_config.length > 0 && (
        <div className="mt-3 p-3 bg-primary bg-opacity-10 rounded">
          <h6 className="mb-2 text-primary">
            <i className="bi bi-sort-alpha-down me-2"></i>
            Sort Configuration
          </h6>
          <div className="d-flex flex-wrap gap-2">
            {preferences.sort_config
              .sort((a, b) => a.sort_order - b.sort_order)
              .map((sort, index) => {
                const column = preferences.columns.find(c => c.column_id === sort.column_id);
                return (
                  <span key={sort.column_id} className="badge bg-primary d-flex align-items-center gap-1">
                    {index + 1}. {column?.display_name || sort.column_id}
                    {sort.direction === SortDirection.ASC ? (
                      <ArrowUp size={12} />
                    ) : (
                      <ArrowDown size={12} />
                    )}
                    <button
                      type="button"
                      className="btn-close btn-close-white"
                      style={{ fontSize: '0.6rem' }}
                      onClick={() => {
                        const updatedPreferences = removeColumnSort(preferences, sort.column_id);
                        updatePreferences(updatedPreferences);
                      }}
                      title="Remove sort"
                    ></button>
                  </span>
                );
              })}
          </div>
          <small className="text-muted mt-2 d-block">
            Results will be sorted by these columns in order. Click the × to remove a sort.
          </small>
        </div>
      )}

      {/* Summary */}
      <div className="mt-3 p-3 bg-light rounded">
        <div className="row text-center">
          <div className="col-4">
            <strong>{preferences.columns.filter(c => c.is_visible).length}</strong>
            <br />
            <small className="text-muted">Visible Columns</small>
          </div>
          <div className="col-4">
            <strong>{preferences.columns.length}</strong>
            <br />
            <small className="text-muted">Total Columns</small>
          </div>
          <div className="col-4">
            <strong>{preferences.sort_config?.length || 0}</strong>
            <br />
            <small className="text-muted">Sort Columns</small>
          </div>
        </div>
      </div>

      <style>{`
        .column-item {
          transition: all 0.2s ease;
        }
        
        .column-item:hover {
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .column-item.dragging {
          transform: rotate(3deg);
        }
        
        .column-item.drag-over {
          transform: translateY(-2px);
        }
        
        .drag-handle {
          cursor: grab;
        }
        
        .drag-handle:active {
          cursor: grabbing;
        }
      `}</style>
    </div>
  );
};

export default ColumnManagement;