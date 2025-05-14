import { useEffect, useRef, useCallback } from 'react';
import type { Modal } from 'bootstrap';

// Using the existing Window interface from vite-env.d.ts
// No need to redeclare it here

export default function useModal(
  show: boolean,
  onHide: () => void
): { modalRef: React.RefObject<HTMLDivElement>, closeModal: () => void } {
  const modalRef = useRef<HTMLDivElement>(null);
  const bootstrapModalRef = useRef<Modal | null>(null);
  const initialized = useRef<boolean>(false);
  
  // Function to explicitly close the modal - this is what we'll expose
  const closeModal = useCallback(() => {
    if (bootstrapModalRef.current) {
      try {
        bootstrapModalRef.current.hide();
        // Also call onHide directly to ensure React state is updated
        onHide();
      } catch (error) {
        console.error('Error closing modal:', error);
      }
    }
  }, [onHide]);
  
  // Initialize the Bootstrap modal when the component mounts
  useEffect(() => {
    // Initialize modal function
    const initializeModal = () => {
      if (!modalRef.current) return;
      
      try {
        // Ensure Bootstrap is loaded
        if (!window.bootstrap || !window.bootstrap.Modal) {
          console.warn('Bootstrap not found in window object - waiting for it to be available');
          // Wait for Bootstrap to be available
          setTimeout(initializeModal, 100);
          return;
        }
        
        // Initialize modal after a small delay to ensure DOM is ready
        setTimeout(() => {
          if (modalRef.current && window.bootstrap && !initialized.current) {
            bootstrapModalRef.current = new window.bootstrap.Modal(modalRef.current, {
              backdrop: 'static',  // Prevents closing when clicking outside
              keyboard: false      // Prevents closing with Escape key
            });
            
            // Add event listener for when modal is hidden by Bootstrap
            modalRef.current.addEventListener('hidden.bs.modal', onHide);
            
            initialized.current = true;
            
            // Show modal if needed
            if (show && bootstrapModalRef.current) {
              bootstrapModalRef.current.show();
            }
          }
        }, 50);
      } catch (error) {
        console.error('Failed to initialize Bootstrap modal:', error);
      }
    };
    
    initializeModal();
    
    // Cleanup when component unmounts
    return () => {
      if (bootstrapModalRef.current) {
        try {
          bootstrapModalRef.current.dispose();
        } catch (e) {
          console.warn('Error disposing modal:', e);
        }
      }
      
      if (modalRef.current) {
        modalRef.current.removeEventListener('hidden.bs.modal', onHide);
      }
      
      initialized.current = false;
    };
  }, [onHide, show]);
  
  // Control modal visibility based on show prop
  useEffect(() => {
    if (!bootstrapModalRef.current || !initialized.current) return;
    
    try {
      if (show) {
        bootstrapModalRef.current.show();
      } else {
        bootstrapModalRef.current.hide();
      }
    } catch (error) {
      console.error('Error controlling modal visibility:', error);
    }
  }, [show]);
  
  return { modalRef, closeModal };
}
