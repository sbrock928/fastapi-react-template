// SQL formatting utility
export const formatSQL = (sql: string): string => {
  if (!sql) return '';
  
  // Basic SQL formatter - adds proper line breaks and indentation
  let formatted = sql
    // Add line breaks before major keywords
    .replace(/\bWITH\b/gi, '\nWITH')
    .replace(/\bSELECT\b/gi, '\nSELECT')
    .replace(/\bFROM\b/gi, '\nFROM')
    .replace(/\bLEFT OUTER JOIN\b/gi, '\n  LEFT OUTER JOIN')
    .replace(/\bINNER JOIN\b/gi, '\n  INNER JOIN')
    .replace(/\bJOIN\b/gi, '\n  JOIN')
    .replace(/\bWHERE\b/gi, '\nWHERE')
    .replace(/\bGROUP BY\b/gi, '\nGROUP BY')
    .replace(/\bORDER BY\b/gi, '\nORDER BY')
    .replace(/\bHAVING\b/gi, '\nHAVING')
    .replace(/\bUNION\b/gi, '\nUNION')
    // Handle CTEs properly
    .replace(/\),\s*(\w+)\s+AS\s*\(/gi, '),\n\n$1 AS (')
    .replace(/\bAS\s*\(/gi, ' AS (\n  ')
    .replace(/\)\s*SELECT\b/gi, '\n)\nSELECT')
    // Add proper spacing around operators - use word boundaries to avoid matching within words
    .replace(/\s*=\s*/g, ' = ')
    .replace(/\s+\bAND\b\s+/gi, ' AND ')
    .replace(/\s+\bOR\b\s+/gi, ' OR ')
    .replace(/\s+\bON\b\s+/gi, ' ON ')
    // Clean up excessive whitespace
    .replace(/\n\s*\n\s*\n/g, '\n\n')
    .replace(/^\s+/gm, (match) => '  '.repeat(Math.floor(match.length / 2)))
    .trim();

  return formatted;
};

// SQL syntax highlighting utility
export const highlightSQL = (sql: string): string => {
  if (!sql) return '';
  
  const keywords = [
    'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 
    'LEFT OUTER JOIN', 'RIGHT OUTER JOIN', 'FULL OUTER JOIN', 'ON', 'AND', 'OR', 
    'GROUP BY', 'ORDER BY', 'HAVING', 'WITH', 'AS', 'DISTINCT', 'COUNT', 'SUM', 
    'AVG', 'MIN', 'MAX', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'IN', 'NOT', 
    'NULL', 'IS', 'LIKE', 'BETWEEN', 'EXISTS', 'UNION', 'ALL'
  ];
  
  let highlighted = sql;
  
  // Highlight SQL keywords
  keywords.forEach(keyword => {
    const regex = new RegExp(`\\b${keyword}\\b`, 'gi');
    highlighted = highlighted.replace(regex, `<span class="sql-keyword">${keyword}</span>`);
  });
  
  // Highlight strings (single quotes)
  highlighted = highlighted.replace(/'([^']*)'/g, '<span class="sql-string">\'$1\'</span>');
  
  // Highlight numbers
  highlighted = highlighted.replace(/\b(\d+\.?\d*)\b/g, '<span class="sql-number">$1</span>');
  
  // Highlight comments
  highlighted = highlighted.replace(/--.*$/gm, '<span class="sql-comment">$&</span>');
  
  return highlighted;
};