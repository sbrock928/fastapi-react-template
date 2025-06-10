// frontend/features/calculations/components/SqlEditor.tsx
import React, { useState, useRef, useEffect } from 'react';

interface SqlEditorProps {
  value: string;
  onChange: (value: string) => void;
  groupLevel: string;
  disabled?: boolean;
  placeholder?: string;
  height?: string;
}

const SqlEditor: React.FC<SqlEditorProps> = ({
  value,
  onChange,
  groupLevel,
  disabled = false,
  placeholder = '',
  height = '300px'
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const highlightRef = useRef<HTMLDivElement>(null);
  const lineNumbersRef = useRef<HTMLDivElement>(null);
  const [focused, setFocused] = useState(false);

  // SQL keywords for highlighting
  const SQL_KEYWORDS = [
    'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER', 'ON',
    'GROUP', 'BY', 'ORDER', 'HAVING', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
    'AS', 'AND', 'OR', 'NOT', 'IN', 'LIKE', 'BETWEEN', 'IS', 'NULL', 'DISTINCT',
    'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'CAST', 'COALESCE', 'NULLIF'
  ];

  const FUNCTIONS = ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'CASE', 'CAST', 'COALESCE', 'NULLIF'];
  const TABLES = ['deal', 'tranche', 'tranchebal'];
  const COMMON_FIELDS = ['dl_nbr', 'tr_id', 'issr_cde', 'cdi_file_nme', 'tr_end_bal_amt', 'tr_pass_thru_rte'];

  // Highlight SQL syntax (without line numbers)
  const highlightSql = (sql: string): string => {
    if (!sql) return '';

    let highlighted = sql;

    // Escape HTML first
    highlighted = highlighted
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

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
  };

  const formatSql = () => {
    const formatted = value
      .replace(/\bSELECT\b/gi, '\nSELECT')
      .replace(/\bFROM\b/gi, '\nFROM')
      .replace(/\bWHERE\b/gi, '\nWHERE')
      .replace(/\bJOIN\b/gi, '\nJOIN')
      .replace(/\bGROUP BY\b/gi, '\nGROUP BY')
      .replace(/\bORDER BY\b/gi, '\nORDER BY')
      .replace(/\n\s*\n/g, '\n') // Remove extra blank lines
      .trim();
    onChange(formatted);
  };

  return (
    <div>
      {/* Global CSS for syntax highlighting */}
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
        `
      }} />
      
      <div className={`sql-editor-container ${focused ? 'focused' : ''} ${disabled ? 'disabled' : ''}`}>
        {/* Toolbar */}
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
          </div>
          <div className="sql-actions">
            <button
              className="sql-btn"
              type="button"
              onClick={formatSql}
              disabled={disabled || !value}
            >
              Format
            </button>
            <button
              className="sql-btn"
              type="button"
              onClick={() => onChange('')}
              disabled={disabled || !value}
            >
              Clear
            </button>
          </div>
        </div>

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

        {/* Footer with tips */}
        <div className="sql-toolbar">
          <div className="sql-status">
            <small className="text-muted">
              <i className="bi bi-lightbulb me-1"></i>
              Tips: Use Tab for indentation, Ctrl+A to select all, include required fields for {groupLevel} level
            </small>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SqlEditor;