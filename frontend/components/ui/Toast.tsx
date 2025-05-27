import React, { useCallback } from 'react';
import { Toast as ToastInterface, useToast } from '@/context/ToastContext';
import styles from '@/styles/components/Toast.module.css';

const Toast: React.FC = () => {
  const { toasts, removeToast } = useToast();

  // If no toasts, don't render anything
  if (toasts.length === 0) return null;

  // Handle toast close with proper event stopping
  const handleToastClose = useCallback((e: React.MouseEvent, id: string) => {
    // Prevent any default behavior
    e.preventDefault();
    // Stop event propagation to prevent interference with modals
    e.stopPropagation();
    removeToast(id);
  }, [removeToast]);

  // Create an isolated wrapper click handler
  const handleToastWrapperClick = useCallback((e: React.MouseEvent) => {
    // Prevent click events from bubbling through the toast container
    e.stopPropagation();
  }, []);

  return (
    <div 
      className={`toast-container position-fixed bottom-0 end-0 p-3 ${styles.toastContainer}`}
      onClick={handleToastWrapperClick}
    >
      {toasts.map((toast: ToastInterface) => (
        <div 
          key={toast.id}
          className={`toast show align-items-center text-white bg-${getToastClass(toast.type)} border-0 ${styles.toast}`} 
          role="alert" 
          aria-live="assertive" 
          aria-atomic="true"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="d-flex">
            <div className={`toast-body ${styles.toastBody}`}>
              {toast.message}
            </div>
            <button 
              type="button" 
              className={`btn-close btn-close-white me-2 m-auto ${styles.closeButton}`}
              aria-label="Close"
              onClick={(e) => handleToastClose(e, toast.id)}
              onMouseDown={(e) => e.stopPropagation()}
            ></button>
          </div>
        </div>
      ))}
    </div>
  );
};

// Helper function to get Bootstrap color class based on toast type
const getToastClass = (type: string): string => {
  switch (type) {
    case 'success':
      return 'success';
    case 'error':
      return 'danger';
    case 'warning':
      return 'warning';
    case 'info':
      return 'info';
    default:
      return 'primary';
  }
};

export default Toast;