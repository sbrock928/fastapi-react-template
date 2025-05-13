/**
 * Formats a date string to a localized date string
 */
export const formatDate = (dateStr: string): string => {
  if (!dateStr) return '';
  
  try {
    const date = new Date(dateStr);
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    }).format(date);
  } catch (error) {
    console.error('Error formatting date:', error);
    return dateStr;
  }
};

/**
 * Formats a date string to a localized date and time string
 */
export const formatDateTime = (dateStr: string): string => {
  if (!dateStr) return '';
  
  try {
    const date = new Date(dateStr);
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).format(date);
  } catch (error) {
    console.error('Error formatting date time:', error);
    return dateStr;
  }
};

/**
 * Formats a JSON string to a pretty-printed string
 */
export const formatJsonString = (jsonString: string | undefined): string => {
  if (!jsonString) return '';
  
  try {
    const parsed = JSON.parse(jsonString);
    return JSON.stringify(parsed, null, 2);
  } catch {
    return jsonString;
  }
};

/**
 * Formats a number to a localized string
 */
export const formatNumber = (value: number): string => {
  return value?.toLocaleString() || '0';
};

/**
 * Formats a number as a percentage
 */
export const formatPercentage = (value: number): string => {
  return `${(value * 100).toFixed(2)}%`;
};
