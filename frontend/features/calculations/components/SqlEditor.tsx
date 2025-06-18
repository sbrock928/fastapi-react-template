// frontend/features/calculations/components/SqlEditor.tsx
import React, { useState, useRef, useEffect } from 'react';
import { getSqlTemplateWithPlaceholders, getAvailablePlaceholders } from '../utils/calculationUtils';

interface SqlEditorProps {
  value: string;
  onChange: (value: string) => void;
  groupLevel: string;
  disabled?: boolean;
  placeholder?: string;
  height?: string;
  resultColumnName?: string;
  onValidate?: (sql: string) => void;
  validationResult?: any;
}

const SqlEditor: React.FC<SqlEditorProps> = ({
  value,
  onChange,
  groupLevel,
  disabled = false,
  placeholder = '',
  height = '300px',
  resultColumnName = 'result_column',
  onValidate,
  validationResult
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const highlightRef = useRef<HTMLDivElement>(null);
  const lineNumbersRef = useRef<HTMLDivElement>(null);
  const [focused, setFocused] = useState(false);
  const [showPlaceholderHelp, setShowPlaceholderHelp] = useState(false);

  // Enhanced SQL keywords for highlighting - includes placeholders
  const SQL_KEYWORDS = [
    'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER', 'ON',
    'GROUP', 'BY', 'ORDER', 'HAVING', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
    'AS', 'AND', 'OR', 'NOT', 'IN', 'LIKE', 'BETWEEN', 'IS', 'NULL', 'DISTINCT',
    'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'CAST', 'COALESCE', 'NULLIF',
    'WITH', 'RECURSIVE', 'UNION', 'ALL', 'EXCEPT', 'INTERSECT', 'EXISTS',
    'ROW_NUMBER', 'RANK', 'DENSE_RANK', 'LEAD', 'LAG', 'FIRST_VALUE', 'LAST_VALUE',
    'PARTITION', 'OVER', 'WINDOW', 'RANGE', 'ROWS', 'PRECEDING', 'FOLLOWING', 'UNBOUNDED'
  ];

  const FUNCTIONS = ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'CASE', 'CAST', 'COALESCE', 'NULLIF', 'ROW_NUMBER', 'RANK', 'DENSE_RANK', 'LEAD', 'LAG', 'FIRST_VALUE', 'LAST_VALUE', 'STDDEV', 'VARIANCE', 'NTILE'];
  const TABLES = ['deal', 'tranche', 'tranchebal', 'deal_cdi_var_rpt'];
  const COMMON_FIELDS = ['dl_nbr', 'tr_id', 'issr_cde', 'cdi_file_nme', 'CDB_cdi_file_nme', 'tr_cusip_id', 'tr_end_bal_amt', 'tr_pass_thru_rte', 'cycle_cde', 'dl_cdi_var_nme', 'dl_cdi_var_value'];

  // Get available placeholders
  const availablePlaceholders = getAvailablePlaceholders();

  // Enhanced highlighting with placeholder support
  const highlightSql = (sql: string): string => {
    if (!sql) return '';

    let highlighted = sql;

    // Escape HTML first
    highlighted = highlighted
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Highlight placeholders first (before other patterns)
    highlighted = highlighted.replace(/\{([^}]+)\}/g, (match, placeholder) => {
      const isValid = Object.keys(availablePlaceholders).includes(placeholder);
      const className = isValid ? 'sql-placeholder' : 'sql-placeholder-invalid';
      return `<span class="${className}" title="${isValid ? availablePlaceholders[placeholder] : 'Invalid placeholder'}">${match}</span>`;
    });

    // Highlight CTE names (identifiers followed by AS)
    highlighted = highlighted.replace(/\b(\w+)\s+AS\s*\(/gi, '<span class="sql-cte">$1</span> <span class="sql-keyword">AS</span> (');

    // Highlight SQL keywords
    SQL_KEYWORDS.forEach(keyword => {
      const regex = new RegExp(`\\b${keyword}\\b`, 'gi');
      highlighted = highlighted.replace(regex, `<span class="sql-keyword">${keyword.toUpperCase()}</span>`);
    });

    // Highlight functions
    FUNCTIONS.forEach(func => {
      const regex = new RegExp(`\\b${func}\\s*\\(`, 'gi');
      highlighted = highlighted.replace(regex, (match) => 
        `<span class="sql-function">${match.slice(0, -1).toUpperCase()}</span>(`
      );
    });

    // Highlight table names
    TABLES.forEach(table => {
      const regex = new RegExp(`\\b${table}\\b`, 'gi');
      highlighted = highlighted.replace(regex, `<span class="sql-table">${table}</span>`);
    });

    // Highlight common field names
    COMMON_FIELDS.forEach(field => {
      const regex = new RegExp(`\\b${field}\\b`, 'gi');
      highlighted = highlighted.replace(regex, `<span class="sql-field">${field}</span>`);
    });

    // Highlight strings
    highlighted = highlighted.replace(/'([^']*)'/g, '<span class="sql-string">\'$1\'</span>');

    // Highlight numbers
    highlighted = highlighted.replace(/\b\d+\b/g, '<span class="sql-number">$&</span>');

    // Highlight comments
    highlighted = highlighted.replace(/--.*$/gm, '<span class="sql-comment">$&</span>');
    highlighted = highlighted.replace(/\/\*[\s\S]*?\*\//g, '<span class="sql-comment">$&</span>');

    return highlighted;
  };

  // Generate line numbers separately
  const generateLineNumbers = (text: string): string => {
    const lines = text.split('\n');
    return lines.map((_, index) => index + 1).join('\n');
  };

  // Sync scroll between all elements
  const handleScroll = () => {
    if (textareaRef.current && highlightRef.current && lineNumbersRef.current) {
      const scrollTop = textareaRef.current.scrollTop;
      const scrollLeft = textareaRef.current.scrollLeft;
      
      highlightRef.current.scrollTop = scrollTop;
      highlightRef.current.scrollLeft = scrollLeft;
      lineNumbersRef.current.scrollTop = scrollTop;
    }
  };

  // Update highlighting when value changes
  useEffect(() => {
    if (highlightRef.current) {
      highlightRef.current.innerHTML = highlightSql(value);
    }
    if (lineNumbersRef.current) {
      lineNumbersRef.current.textContent = generateLineNumbers(value);
    }
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Tab key support
    if (e.key === 'Tab') {
      e.preventDefault();
      const start = e.currentTarget.selectionStart;
      const end = e.currentTarget.selectionEnd;
      const newValue = value.substring(0, start) + '    ' + value.substring(end);
      onChange(newValue);
      
      // Set cursor position after the inserted tab
      setTimeout(() => {
        if (textareaRef.current) {
          textareaRef.current.selectionStart = textareaRef.current.selectionEnd = start + 4;
        }
      }, 0);
    }

    // Ctrl+Space for placeholder suggestions
    if (e.key === ' ' && e.ctrlKey) {
      e.preventDefault();
      setShowPlaceholderHelp(true);
    }

    // Auto-close braces for placeholders
    if (e.key === '{') {
      const start = e.currentTarget.selectionStart;
      const end = e.currentTarget.selectionEnd;
      const newValue = value.substring(0, start) + '{}' + value.substring(end);
      onChange(newValue);
      
      setTimeout(() => {
        if (textareaRef.current) {
          textareaRef.current.selectionStart = textareaRef.current.selectionEnd = start + 1;
        }
      }, 0);
      e.preventDefault();
    }
  };

  // Insert placeholder at cursor position
  const insertPlaceholder = (placeholderName: string) => {
    if (!textareaRef.current) return;
    
    const start = textareaRef.current.selectionStart;
    const end = textareaRef.current.selectionEnd;
    const placeholder = `{${placeholderName}}`;
    const newValue = value.substring(0, start) + placeholder + value.substring(end);
    onChange(newValue);
    
    setTimeout(() => {
      if (textareaRef.current) {
        const newPosition = start + placeholder.length;
        textareaRef.current.selectionStart = textareaRef.current.selectionEnd = newPosition;
        textareaRef.current.focus();
      }
    }, 0);
    
    setShowPlaceholderHelp(false);
  };

  // Insert template SQL
  const insertTemplate = () => {
    const template = getSqlTemplateWithPlaceholders(groupLevel, resultColumnName);
    onChange(template);
    setShowPlaceholderHelp(false);
  };

  // Enhanced formatting with placeholder awareness
  const formatSql = () => {
    if (!value.trim()) return;
    
    let formatted = value;
    
    // Preserve placeholders during formatting
    const placeholders: { [key: string]: string } = {};
    let placeholderIndex = 0;
    
    // Extract placeholders
    formatted = formatted.replace(/\{[^}]+\}/g, (match) => {
      const key = `__PLACEHOLDER_${placeholderIndex++}__`;
      placeholders[key] = match;
      return key;
    });
    
    // Remove extra whitespace and normalize
    formatted = formatted.replace(/\s+/g, ' ').trim();
    
    // Add line breaks before major keywords
    formatted = formatted
      .replace(/\bSELECT\b/gi, '\nSELECT')
      .replace(/\bFROM\b/gi, '\nFROM')
      .replace(/\bWHERE\b/gi, '\nWHERE')
      .replace(/\bINNER\s+JOIN\b/gi, '\n    INNER JOIN')
      .replace(/\bLEFT\s+JOIN\b/gi, '\n    LEFT JOIN')
      .replace(/\bRIGHT\s+JOIN\b/gi, '\n    RIGHT JOIN')
      .replace(/\bJOIN\b/gi, '\n    JOIN')
      .replace(/\bGROUP\s+BY\b/gi, '\nGROUP BY')
      .replace(/\bORDER\s+BY\b/gi, '\nORDER BY')
      .replace(/\bHAVING\b/gi, '\nHAVING')
      .replace(/\bUNION\b/gi, '\nUNION')
      .replace(/\bWITH\b/gi, '\nWITH')
      .replace(/\bCASE\b/gi, '\n        CASE')
      .replace(/\bWHEN\b/gi, '\n            WHEN')
      .replace(/\bTHEN\b/gi, ' THEN')
      .replace(/\bELSE\b/gi, '\n            ELSE')
      .replace(/\bEND\b/gi, '\n        END');
    
    // Handle SELECT column formatting
    formatted = formatted.replace(/SELECT\s+/gi, 'SELECT\n    ');
    
    // Format commas in SELECT and other clauses
    formatted = formatted.replace(/,(?!\s*\n)/g, ',\n    ');
    
    // Clean up AND/OR operators
    formatted = formatted
      .replace(/\s+AND\s+/gi, '\n    AND ')
      .replace(/\s+OR\s+/gi, '\n    OR ');
    
    // Add proper indentation for ON clauses
    formatted = formatted.replace(/\bON\b/gi, '\n        ON');
    
    // Fix spacing around operators
    formatted = formatted
      .replace(/\s*=\s*/g, ' = ')
      .replace(/\s*<>\s*/g, ' <> ')
      .replace(/\s*!=\s*/g, ' != ')
      .replace(/\s*<=\s*/g, ' <= ')
      .replace(/\s*>=\s*/g, ' >= ')
      .replace(/\s*<\s*/g, ' < ')
      .replace(/\s*>\s*/g, ' > ');
    
    // Clean up parentheses spacing
    formatted = formatted
      .replace(/\(\s+/g, '(')
      .replace(/\s+\)/g, ')')
      .replace(/,\s*\)/g, ')');
    
    // Handle IN clauses
    formatted = formatted.replace(/\bIN\s*\(/gi, ' IN (');
    
    // Remove excessive blank lines and clean up
    formatted = formatted
      .replace(/\n\s*\n\s*\n/g, '\n\n')
      .replace(/^\n+/, '')
      .replace(/\n+$/, '')
      .split('\n')
      .map(line => line.trimEnd())
      .join('\n');
    
    // Restore placeholders
    Object.keys(placeholders).forEach(key => {
      formatted = formatted.replace(new RegExp(key, 'g'), placeholders[key]);
    });
    
    onChange(formatted);
  };

  return (
    <div>
      {/* Enhanced CSS for syntax highlighting with placeholder support */}
      <style dangerouslySetInnerHTML={{
        __html: `
          .sql-editor-container {
            position: relative;
            border: 2px solid #dee2e6;
            border-radius: 8px;
            overflow: hidden;
            background: #1e1e1e;
            font-family: "Consolas", "Monaco", "Courier New", monospace;
            font-size: 14px;
            line-height: 1.4;
            transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
          }
          .sql-editor-container.focused {
            border-color: #0d6efd;
            box-shadow: 0 0 0 0.2rem rgba(13, 110, 253, 0.25);
          }
          .sql-editor-container.disabled {
            opacity: 0.6;
            pointer-events: none;
          }
          .sql-editor-wrapper {
            position: relative;
            height: ${height};
            display: flex;
          }
          .sql-line-numbers {
            position: absolute;
            top: 0;
            left: 0;
            width: 50px;
            height: 100%;
            padding: 12px 8px;
            background: #252526;
            color: #858585;
            font-size: 12px;
            line-height: 1.4;
            text-align: right;
            user-select: none;
            overflow: hidden;
            white-space: pre;
            border-right: 1px solid #404040;
            z-index: 1;
          }
          .sql-content-area {
            position: relative;
            flex: 1;
            margin-left: 50px;
          }
          .sql-highlight {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            padding: 12px;
            margin: 0;
            border: none;
            background: transparent;
            color: transparent;
            white-space: pre-wrap;
            word-wrap: break-word;
            overflow: auto;
            pointer-events: none;
            font-family: inherit;
            font-size: inherit;
            line-height: inherit;
            z-index: 1;
          }
          .sql-textarea {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            width: 100%;
            height: 100%;
            padding: 12px;
            margin: 0;
            border: none;
            background: transparent;
            color: #d4d4d4;
            white-space: pre-wrap;
            word-wrap: break-word;
            overflow: auto;
            resize: none;
            outline: none;
            font-family: inherit;
            font-size: inherit;
            line-height: inherit;
            z-index: 2;
          }
          .sql-textarea::placeholder {
            color: #6a6a6a;
          }
          .sql-toolbar {
            background: #2d2d30;
            border-bottom: 1px solid #404040;
            padding: 8px 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: #cccccc;
            font-size: 12px;
          }
          .sql-status {
            display: flex;
            align-items: center;
            gap: 12px;
          }
          .sql-actions {
            display: flex;
            gap: 8px;
          }
          .sql-btn {
            background: #0e639c;
            border: none;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 11px;
            transition: background-color 0.15s ease;
          }
          .sql-btn:hover:not(:disabled) {
            background: #1177bb;
          }
          .sql-btn:disabled {
            background: #505050;
            cursor: not-allowed;
          }
          .sql-btn.success {
            background: #198754;
          }
          .sql-btn.success:hover:not(:disabled) {
            background: #157347;
          }
          .sql-keyword {
            color: #569cd6;
            font-weight: bold;
          }
          .sql-function {
            color: #dcdcaa;
            font-weight: bold;
          }
          .sql-table {
            color: #4ec9b0;
            font-weight: bold;
          }
          .sql-field {
            color: #9cdcfe;
          }
          .sql-string {
            color: #ce9178;
          }
          .sql-number {
            color: #b5cea8;
          }
          .sql-comment {
            color: #6a9955;
            font-style: italic;
          }
          .sql-cte {
            color: #c586c0;
            font-weight: bold;
            text-decoration: underline;
          }
          .sql-placeholder {
            color: #ff79c6;
            background: rgba(255, 121, 198, 0.1);
            padding: 1px 2px;
            border-radius: 2px;
            font-weight: bold;
            cursor: help;
          }
          .sql-placeholder-invalid {
            color: #ff5555;
            background: rgba(255, 85, 85, 0.1);
            padding: 1px 2px;
            border-radius: 2px;
            font-weight: bold;
            text-decoration: underline wavy;
          }
          .placeholder-help {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: #2d2d30;
            border: 1px solid #404040;
            border-radius: 4px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
            z-index: 1000;
            max-height: 300px;
            overflow-y: auto;
          }
          .placeholder-item {
            padding: 8px 12px;
            cursor: pointer;
            border-bottom: 1px solid #404040;
            color: #cccccc;
          }
          .placeholder-item:hover {
            background: #404040;
          }
          .placeholder-item:last-child {
            border-bottom: none;
          }
          .placeholder-name {
            color: #ff79c6;
            font-weight: bold;
            font-family: monospace;
          }
          .placeholder-desc {
            color: #999;
            font-size: 11px;
            margin-top: 2px;
          }
        `
      }} />
      
      <div className={`sql-editor-container ${focused ? 'focused' : ''} ${disabled ? 'disabled' : ''}`} style={{ position: 'relative' }}>
        {/* Enhanced Toolbar */}
        <div className="sql-toolbar">
          <div className="sql-status">
            <span>SQL Editor</span>
            <span className="text-muted">•</span>
            <span>Target: {groupLevel} Level</span>
            {value && (
              <>
                <span className="text-muted">•</span>
                <span>{value.split('\n').length} lines</span>
              </>
            )}
            {validationResult && (
              <>
                <span className="text-muted">•</span>
                <span className={validationResult.is_valid ? 'text-success' : 'text-danger'}>
                  {validationResult.is_valid ? '✓ Valid' : '✗ Invalid'}
                </span>
              </>
            )}
          </div>
          <div className="sql-actions">
            <button
              className="sql-btn"
              type="button"
              onClick={() => setShowPlaceholderHelp(!showPlaceholderHelp)}
              disabled={disabled}
              title="Show available placeholders (Ctrl+Space)"
            >
              <i className="bi bi-braces"></i> Placeholders
            </button>
            <button
              className="sql-btn success"
              type="button"
              onClick={insertTemplate}
              disabled={disabled}
              title="Insert template SQL with placeholders"
            >
              <i className="bi bi-code-square"></i> Template
            </button>
            <button
              className="sql-btn"
              type="button"
              onClick={formatSql}
              disabled={disabled || !value}
            >
              <i className="bi bi-code"></i> Format
            </button>
            {onValidate && (
              <button
                className="sql-btn"
                type="button"
                onClick={() => onValidate(value)}
                disabled={disabled || !value}
              >
                <i className="bi bi-check-circle"></i> Validate
              </button>
            )}
            <button
              className="sql-btn"
              type="button"
              onClick={() => onChange('')}
              disabled={disabled || !value}
            >
              <i className="bi bi-trash"></i> Clear
            </button>
          </div>
        </div>

        {/* Placeholder Help Panel */}
        {showPlaceholderHelp && (
          <div className="placeholder-help">
            <div className="placeholder-item" style={{ background: '#404040', fontWeight: 'bold' }}>
              <div style={{ color: '#ff79c6' }}>Available SQL Placeholders</div>
              <div style={{ color: '#999', fontSize: '10px' }}>Click to insert, or use Ctrl+Space</div>
            </div>
            {Object.entries(availablePlaceholders).map(([name, description]) => (
              <div
                key={name}
                className="placeholder-item"
                onClick={() => insertPlaceholder(name)}
              >
                <div className="placeholder-name">{`{${name}}`}</div>
                <div className="placeholder-desc">{description}</div>
              </div>
            ))}
            <div className="placeholder-item" style={{ background: '#2d4a3e' }}>
              <div style={{ color: '#4ec9b0', fontWeight: 'bold' }}>
                <i className="bi bi-lightbulb me-1"></i>
                Pro Tip
              </div>
              <div style={{ color: '#999', fontSize: '10px' }}>
                These placeholders will be replaced with actual values when the report runs.
                Use {`{deal_tranche_filter}`} for comprehensive filtering.
              </div>
            </div>
          </div>
        )}

        {/* Editor */}
        <div className="sql-editor-wrapper">
          {/* Line Numbers */}
          <div
            ref={lineNumbersRef}
            className="sql-line-numbers"
          >
            {generateLineNumbers(value)}
          </div>

          {/* Content Area */}
          <div className="sql-content-area">
            {/* Syntax Highlighting Layer */}
            <div
              ref={highlightRef}
              className="sql-highlight"
              dangerouslySetInnerHTML={{ __html: highlightSql(value) }}
            />
            
            {/* Input Layer */}
            <textarea
              ref={textareaRef}
              className="sql-textarea"
              value={value}
              onChange={(e) => onChange(e.target.value)}
              onScroll={handleScroll}
              onFocus={() => setFocused(true)}
              onBlur={() => setFocused(false)}
              onKeyDown={handleKeyDown}
              disabled={disabled}
              placeholder={placeholder}
              spellCheck={false}
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="off"
            />
          </div>
        </div>

        {/* Enhanced Footer with placeholder usage */}
        <div className="sql-toolbar">
          <div className="sql-status">
            <small className="text-muted">
              <i className="bi bi-lightbulb me-1"></i>
              Tips: Use Tab for indentation, {`{placeholders}`} for dynamic values, Ctrl+Space for placeholder help
            </small>
          </div>
          <div className="sql-actions">
            {value && (
              <small className="text-muted">
                Placeholders used: {(value.match(/\{[^}]+\}/g) || []).length}
              </small>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SqlEditor;