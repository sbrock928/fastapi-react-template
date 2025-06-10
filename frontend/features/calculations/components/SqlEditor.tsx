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

  // Highlight SQL syntax
  const highlightSql = (sql: string): string => {
    if (!sql) return '';

    let highlighted = sql;

    // Escape HTML
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

    // Add line numbers
    const lines = highlighted.split('\n');
    const numberedLines = lines.map((line, index) => 
      `<span class="line-number">${index + 1}</span>${line}`
    ).join('\n');

    return numberedLines;
  };

  // Sync scroll between textarea and highlight div
  const handleScroll = () => {
    if (textareaRef.current && highlightRef.current) {
      highlightRef.current.scrollTop = textareaRef.current.scrollTop;
      highlightRef.current.scrollLeft = textareaRef.current.scrollLeft;
    }
  };

  // Update highlighting when value changes
  useEffect(() => {
    if (highlightRef.current) {
      highlightRef.current.innerHTML = highlightSql(value);
    }
  }, [value]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.max(300, textareaRef.current.scrollHeight) + 'px';
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

  return (
    <div className="sql-editor-container">
      <style jsx>{`
        .sql-editor-container {
          position: relative;
          border: 2px solid #dee2e6;
          border-radius: 8px;
          overflow: hidden;
          background: #1e1e1e;
          font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
          font-size: 14px;
          line-height: 1.4;
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
        }

        .sql-textarea::placeholder {
          color: #6c757d;
        }

        /* Syntax highlighting styles */
        :global(.sql-keyword) {
          color: #569cd6;
          font-weight: bold;
        }

        :global(.sql-function) {
          color: #dcdcaa;
          font-weight: bold;
        }

        :global(.sql-table) {
          color: #4ec9b0;
          font-weight: bold;
        }

        :global(.sql-field) {
          color: #9cdcfe;
        }

        :global(.sql-string) {
          color: #ce9178;
        }

        :global(.sql-number) {
          color: #b5cea8;
        }

        :global(.sql-comment) {
          color: #6a9955;
          font-style: italic;
        }

        :global(.line-number) {
          color: #858585;
          margin-right: 12px;
          display: inline-block;
          width: 30px;
          text-align: right;
          user-select: none;
        }

        .sql-toolbar {
          background: #2d2d30;
          border-bottom: 1px solid #404040;
          padding: 8px 12px;
          display: flex;
          justify-content: between;
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
        }

        .sql-btn:hover {
          background: #1177bb;
        }

        .sql-btn:disabled {
          background: #505050;
          cursor: not-allowed;
        }
      `}</style>

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
            onClick={() => {
              const formatted = value
                .replace(/\bSELECT\b/gi, '\nSELECT')
                .replace(/\bFROM\b/gi, '\nFROM')
                .replace(/\bWHERE\b/gi, '\nWHERE')
                .replace(/\bJOIN\b/gi, '\nJOIN')
                .replace(/\bGROUP BY\b/gi, '\nGROUP BY')
                .replace(/\bORDER BY\b/gi, '\nORDER BY')
                .trim();
              onChange(formatted);
            }}
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
      <div className={`sql-editor-wrapper ${focused ? 'focused' : ''} ${disabled ? 'disabled' : ''}`}>
        <div
          ref={highlightRef}
          className="sql-highlight"
          dangerouslySetInnerHTML={{ __html: highlightSql(value) }}
        />
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
  );
};

export default SqlEditor;