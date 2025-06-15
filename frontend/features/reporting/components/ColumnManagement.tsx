import React, { useState, useCallback } from 'react';
import { Eye, EyeOff, GripVertical } from 'lucide-react';
import type { 
  ReportColumnPreferences,
  ReportCalculation,
  ReportScope
} from '@/types/reporting';
import { ColumnFormat, getColumnFormatLabel, getDefaultColumnPreferences } from '@/types/reporting';

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
                      <div className="col-md-4">
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
                      
                      <div className="col-md-3">
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
                      
                      <div className="col-md-2 text-center">
                        <span className="badge bg-secondary">
                          #{column.display_order + 1}
                        </span>
                      </div>
                      
                      <div className="col-md-2 text-center">
                        <button
                          type="button"
                          className={`btn btn-sm ${column.is_visible ? 'btn-success' : 'btn-outline-secondary'}`}
                          onClick={() => toggleColumnVisibility(index)}
                          title={column.is_visible ? 'Hide column' : 'Show column'}
                        >
                          {column.is_visible ? <Eye size={14} /> : <EyeOff size={14} />}
                        </button>
                      </div>
                      
                      <div className="col-md-1 text-center">
                        <small className="text-muted">
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

      {/* Summary */}
      <div className="mt-3 p-3 bg-light rounded">
        <div className="row text-center">
          <div className="col-6">
            <strong>{preferences.columns.filter(c => c.is_visible).length}</strong>
            <br />
            <small className="text-muted">Visible Columns</small>
          </div>
          <div className="col-6">
            <strong>{preferences.columns.length}</strong>
            <br />
            <small className="text-muted">Total Columns</small>
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