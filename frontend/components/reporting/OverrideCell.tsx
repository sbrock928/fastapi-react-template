import React, { useState, useRef, useEffect } from 'react';
import type { Tranche, OverrideableColumn } from '@/types';

interface OverrideCellProps {
  tranche: Tranche;
  column: OverrideableColumn;
  currentValue: any;
  overrideValue: any;
  onOverrideChange: (
    trancheId: number, 
    columnName: string, 
    value: any, 
    notes?: string
  ) => void;
  formatValue: (value: any, dataType: string) => string;
}

const OverrideCell: React.FC<OverrideCellProps> = ({
  tranche,
  column,
  currentValue,
  overrideValue,
  onOverrideChange,
  formatValue
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [tempValue, setTempValue] = useState('');
  const [showValuePicker, setShowValuePicker] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  
  const hasOverride = overrideValue !== null && overrideValue !== undefined && overrideValue !== '';
  const displayValue = hasOverride ? overrideValue : currentValue;

  // Focus input when editing starts
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleStartEdit = () => {
    const valueToEdit = hasOverride ? overrideValue : currentValue;
    setTempValue(String(valueToEdit || ''));
    setIsEditing(true);
  };

  const handleSave = () => {
    const trimmedValue = tempValue.trim();
    
    if (trimmedValue === '') {
      // Clear override if empty
      onOverrideChange(tranche.id, column.key, null);
    } else {
      // Parse value based on data type
      let parsedValue: any = trimmedValue;
      
      try {
        switch (column.data_type) {
          case 'number':
            parsedValue = parseFloat(trimmedValue);
            if (isNaN(parsedValue)) {
              throw new Error('Invalid number');
            }
            break;
          case 'currency':
            // Remove currency symbols and parse
            const cleanedValue = trimmedValue.replace(/[$,\s]/g, '');
            parsedValue = parseFloat(cleanedValue);
            if (isNaN(parsedValue)) {
              throw new Error('Invalid currency value');
            }
            break;
          case 'percentage':
            // Handle both 0.05 and 5% formats
            let percentValue = trimmedValue.replace(/[%\s]/g, '');
            parsedValue = parseFloat(percentValue);
            if (isNaN(parsedValue)) {
              throw new Error('Invalid percentage');
            }
            // Convert to decimal if it looks like a percentage (> 1)
            if (parsedValue > 1 && !trimmedValue.includes('.')) {
              parsedValue = parsedValue / 100;
            }
            break;
          default:
            // String value - keep as is
            parsedValue = trimmedValue;
        }
        
        onOverrideChange(tranche.id, column.key, parsedValue);
      } catch (error) {
        console.error('Error parsing value:', error);
        // Keep the original value if parsing fails
        setTempValue(String(displayValue || ''));
        return;
      }
    }
    
    setIsEditing(false);
  };

  const handleCancel = () => {
    setTempValue(String(displayValue || ''));
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSave();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      handleCancel();
    }
  };

  const handleClearOverride = (e: React.MouseEvent) => {
    e.stopPropagation();
    onOverrideChange(tranche.id, column.key, null);
  };

  const getValuePickerOptions = (): Array<{label: string, value: any}> => {
    switch (column.key) {
      case 'credit_rating':
        return [
          { label: 'AAA', value: 'AAA' },
          { label: 'AA+', value: 'AA+' },
          { label: 'AA', value: 'AA' },
          { label: 'AA-', value: 'AA-' },
          { label: 'A+', value: 'A+' },
          { label: 'A', value: 'A' },
          { label: 'A-', value: 'A-' },
          { label: 'BBB+', value: 'BBB+' },
          { label: 'BBB', value: 'BBB' },
          { label: 'BBB-', value: 'BBB-' }
        ];
      case 'subordination_level':
        return [
          { label: 'Senior (1)', value: 1 },
          { label: 'Mezzanine (2)', value: 2 },
          { label: 'Subordinate (3)', value: 3 }
        ];
      case 'override_type':
        return [
          { label: 'Manual', value: 'manual' },
          { label: 'Calculated', value: 'calculated' },
          { label: 'Mapped', value: 'mapped' }
        ];
      default:
        return [];
    }
  };

  const valuePickerOptions = getValuePickerOptions();
  const showPickerButton = valuePickerOptions.length > 0;

  const getInputType = (): string => {
    switch (column.data_type) {
      case 'number':
      case 'currency':
      case 'percentage':
        return 'number';
      default:
        return 'text';
    }
  };

  const getInputStep = (): string | undefined => {
    switch (column.data_type) {
      case 'currency':
        return '0.01';
      case 'percentage':
        return '0.0001';
      case 'number':
        return column.key.includes('priority') || column.key.includes('level') ? '1' : '0.01';
      default:
        return undefined;
    }
  };

  return (
    <div className="position-relative">
      {isEditing ? (
        <div className="d-flex align-items-center">
          <div className="flex-grow-1">
            <input
              ref={inputRef}
              type={getInputType()}
              step={getInputStep()}
              className="form-control form-control-sm"
              value={tempValue}
              onChange={(e) => setTempValue(e.target.value)}
              onBlur={handleSave}
              onKeyDown={handleKeyDown}
              placeholder={`Enter ${column.data_type} value`}
            />
          </div>
          
          {showPickerButton && (
            <div className="dropdown ms-1">
              <button
                className="btn btn-sm btn-outline-secondary dropdown-toggle"
                type="button"
                onClick={() => setShowValuePicker(!showValuePicker)}
                title="Quick select"
              >
                <i className="bi bi-chevron-down"></i>
              </button>
              {showValuePicker && (
                <div className="dropdown-menu show position-absolute" style={{ zIndex: 1050 }}>
                  {valuePickerOptions.map((option, index) => (
                    <button
                      key={index}
                      className="dropdown-item"
                      type="button"
                      onClick={() => {
                        setTempValue(String(option.value));
                        setShowValuePicker(false);
                        setTimeout(() => handleSave(), 100);
                      }}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
          
          <div className="ms-1">
            <button 
              className="btn btn-sm btn-outline-success"
              onClick={handleSave}
              title="Save"
            >
              <i className="bi bi-check"></i>
            </button>
            <button 
              className="btn btn-sm btn-outline-secondary ms-1"
              onClick={handleCancel}
              title="Cancel"
            >
              <i className="bi bi-x"></i>
            </button>
          </div>
        </div>
      ) : (
        <div 
          className={`p-2 rounded cursor-pointer ${
            hasOverride 
              ? 'bg-warning bg-opacity-25 border border-warning' 
              : 'hover:bg-light'
          }`}
          onClick={handleStartEdit}
          title={hasOverride ? 'Click to edit override' : 'Click to set override'}
        >
          <div className="d-flex justify-content-between align-items-center">
            <div className="flex-grow-1">
              <div className={hasOverride ? 'fw-bold' : ''}>
                {formatValue(displayValue, column.data_type)}
              </div>
              {hasOverride && currentValue !== null && currentValue !== undefined && (
                <div className="small text-muted">
                  Original: {formatValue(currentValue, column.data_type)}
                </div>
              )}
            </div>
            
            <div className="d-flex align-items-center ms-2">
              {hasOverride && (
                <>
                  <span 
                    className="badge bg-warning text-dark me-1" 
                    style={{ fontSize: '0.6rem' }}
                    title="This value has been overridden"
                  >
                    Override
                  </span>
                  <button 
                    className="btn btn-xs btn-outline-danger p-0"
                    style={{ fontSize: '0.7rem', width: '16px', height: '16px' }}
                    onClick={handleClearOverride}
                    title="Clear override"
                  >
                    <i className="bi bi-x"></i>
                  </button>
                </>
              )}
              {!hasOverride && (
                <i 
                  className="bi bi-pencil text-muted" 
                  style={{ fontSize: '0.8rem' }}
                  title="Click to override"
                ></i>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OverrideCell;