import { useEffect, useRef } from 'react';

export default function useModal(
  show: boolean,
  onHide: () => void
): React.RefObject<HTMLDivElement> {
  const modalRef = useRef<HTMLDivElement>(null);
  const bootstrapModalRef = useRef<any>(null);
  
  // Initialize the Bootstrap modal when the component mounts
  useEffect(() => {
    if (modalRef.current && window.bootstrap) {
      bootstrapModalRef.current = new window.bootstrap.Modal(modalRef.current);
      
      // Add event listener for when modal is hidden by Bootstrap
      modalRef.current.addEventListener('hidden.bs.modal', onHide);
    }
    
    // Cleanup when component unmounts
    return () => {
      if (bootstrapModalRef.current) {
        bootstrapModalRef.current.dispose();
      }
      
      if (modalRef.current) {
        modalRef.current.removeEventListener('hidden.bs.modal', onHide);
      }
    };
  }, [onHide]); // Only recreate when onHide function changes
  
  // Control modal visibility based on show prop
  useEffect(() => {
    if (!bootstrapModalRef.current) return;
    
    if (show) {
      bootstrapModalRef.current.show();
    } else {
      bootstrapModalRef.current.hide();
    }
  }, [show]);
  
  return modalRef;
}
