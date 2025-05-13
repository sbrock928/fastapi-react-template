import React, { createContext, useState, useContext, ReactNode } from 'react';

// Define the type for a single toast notification
export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
  duration?: number; // Duration in milliseconds
}

// Define the context interface
interface ToastContextProps {
  toasts: Toast[];
  showToast: (message: string, type: ToastType, duration?: number) => void;
  removeToast: (id: string) => void;
}

// Create the context with a default value
const ToastContext = createContext<ToastContextProps>({
  toasts: [],
  showToast: () => {},
  removeToast: () => {},
});

// Create a provider component
export const ToastProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = (message: string, type: ToastType, duration = 3000) => {
    const id = Math.random().toString(36).substring(2, 9);
    const newToast: Toast = {
      id,
      message,
      type,
      duration,
    };
    
    setToasts((prevToasts) => [...prevToasts, newToast]);

    // Auto-remove the toast after the specified duration
    if (duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }
  };

  const removeToast = (id: string) => {
    setToasts((prevToasts) => prevToasts.filter((toast) => toast.id !== id));
  };

  return (
    <ToastContext.Provider value={{ toasts, showToast, removeToast }}>
      {children}
    </ToastContext.Provider>
  );
};

// Create a custom hook for using the toast context - fix the named export for HMR
export function useToast() {
  return useContext(ToastContext);
}