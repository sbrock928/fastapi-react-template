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

  // CSS styles as a constant object
  const styles = {
    container: {
      position: 'relative' as const,
      border: '2px solid #dee2e6',
      borderRadius: '8px',
      overflow: 'hidden' as const,
      background: '#1e1e1e',
      fontFamily: '"Consolas", "Monaco", "Courier New", monospace',
      fontSize: '14px',
      lineHeight: 1.4,
      ...(focused && {
        borderColor: '#0d6efd',
        boxShadow: '0 0 0 0.2rem rgba(13, 110, 253, 0.25)'
      }),
      ...(disabled && {
        opacity: 0.6,
        pointerEvents: 'none' as const
      })
    },
    wrapper: {
      position: 'relative' as const,
      height: height
    },
    highlight: {
      position: 'absolute' as const,
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      padding: '12px',
      margin: 0,
      border: 'none',
      background: 'transparent',
      color: 'transparent',
      whiteSpace: 'pre-wrap' as const,
      wordWrap: 'break-word' as const,
      overflow: 'auto' as const,
      pointerEvents: 'none' as const,
      fontFamily: 'inherit',
      fontSize: 'inherit',
      lineHeight: 'inherit'
    },
    textarea: {
      position: 'absolute' as const,
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      width: '100%',
      height: '100%',
      padding: '12px',
      margin: 0,
      border: 'none',
      background: 'transparent',
      color: '#d4d4d4',
      whiteSpace: 'pre-wrap' as const,
      wordWrap: 'break-word' as const,
      overflow: 'auto' as const,
      resize: 'none' as const,
      outline: 'none',
      fontFamily: 'inherit',
      fontSize: 'inherit',
      lineHeight: 'inherit'
    },
    toolbar: {
      background: '#2d2d30',
      borderBottom: '1px solid #404040',
      padding: '8px 12px',
      display: 'flex',
      justifyContent: 'space-between' as const,
      alignItems: 'center',
      color: '#cccccc',
      fontSize: '12px'
    },
    status: {
      display: 'flex',
      alignItems: 'center',
      gap: '12px'
    },
    actions: {
      display: 'flex',
      gap: '8px'
    },
    btn: {
      background: '#0e639c',
      border: 'none',
      color: 'white',
      padding: '4px 8px',
      borderRadius: '4px',
      cursor: 'pointer',
      fontSize: '11px'
    },
    btnHover: {
      background: '#1177bb'
    },
    btnDisabled: {
      background: '#505050',
      cursor: 'not-allowed'
    }
  };

  return (
    <div>
      {/* Global CSS for syntax highlighting */}
      <style dangerouslySetInnerHTML={{
        __html: `
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
          .line-number {
            color: #858585;
            margin-right: 12px;
            display: inline-block;
            width: 30px;
            text-align: right;
            user-select: none;
          }
        `
      }} />
      
      <div style={styles.container}>
        {/* Toolbar */}
        <div style={styles.toolbar}>
          <div style={styles.status}>
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
          <div style={styles.actions}>
            <button
              style={{
                ...styles.btn,
                ...(disabled || !value ? styles.btnDisabled : {})
              }}
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
              style={{
                ...styles.btn,
                ...(disabled || !value ? styles.btnDisabled : {})
              }}
              type="button"
              onClick={() => onChange('')}
              disabled={disabled || !value}
            >
              Clear
            </button>
          </div>
        </div>

        {/* Editor */}
        <div style={styles.wrapper}>
          <div
            ref={highlightRef}
            style={styles.highlight}
            dangerouslySetInnerHTML={{ __html: highlightSql(value) }}
          />
          <textarea
            ref={textareaRef}
            style={styles.textarea}
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
        <div style={styles.toolbar}>
          <div style={styles.status}>
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