/**
 * Updates a URL parameter without refreshing the page
 */
export const updateUrlParam = (key: string, value: string): void => {
  const url = new URL(window.location.href);
  url.searchParams.set(key, value);
  window.history.pushState({}, '', url.toString());
};

/**
 * Gets a URL parameter by name
 */
export const getUrlParam = (key: string): string | null => {
  const params = new URLSearchParams(window.location.search);
  return params.get(key);
};

/**
 * Gets a URL parameter as an integer
 */
export const getUrlParamAsInt = (key: string, defaultValue: number): number => {
  const param = getUrlParam(key);
  if (param) {
    const value = parseInt(param);
    return !isNaN(value) && value > 0 ? value : defaultValue;
  }
  return defaultValue;
};
