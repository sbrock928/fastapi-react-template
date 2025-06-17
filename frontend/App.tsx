import { useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import { ToastProvider, ReportProvider, CycleProvider, ModalProvider, useModal } from './context'
import { Sidebar, TopNavigation, Toast, Dashboard } from './ui'
import Logs from './features/logging/Logs'
import Documentation from './features/documentation'
import Reporting from './features/reporting'
import CalculationBuilder from './features/calculations'
import CDIVariableModal from './features/calculations/components/CDIVariableModal'
import ExecutionLogsModal from './features/reporting/components/ExecutionLogsModal'
import { useToast } from './context/ToastContext'
import './index.css'  // Import the new layout styles

// Global Modal Component - renders at the highest level
const GlobalModals = () => {
  const { 
    showCDIModal, 
    editingCDIVariable, 
    cdiModalMode, 
    closeCDIModal, 
    onCDIVariableSaved,
    showExecutionLogsModal,
    executionLogsReportId,
    executionLogsReportName,
    closeExecutionLogsModal
  } = useModal();
  const { showToast } = useToast();

  const handleCDIVariableSaved = () => {
    onCDIVariableSaved?.();
    closeCDIModal();
    showToast(
      cdiModalMode === 'create' ? 'CDI variable created successfully!' : 'CDI variable updated successfully!',
      'success'
    );
  };

  return (
    <>
      {/* CDI Variable Modal - Rendered at the absolute top level */}
      <CDIVariableModal
        isOpen={showCDIModal}
        editingVariable={editingCDIVariable}
        mode={cdiModalMode}
        onClose={closeCDIModal}
        onSave={handleCDIVariableSaved}
      />
      
      {/* Execution Logs Modal - Rendered at the absolute top level */}
      {showExecutionLogsModal && executionLogsReportId && (
        <ExecutionLogsModal
          reportId={executionLogsReportId}
          reportName={executionLogsReportName}
          isOpen={showExecutionLogsModal}
          onClose={closeExecutionLogsModal}
        />
      )}
    </>
  );
};

function App() {
  // Toggle sidebar collapsed state
  const toggleSidebar = () => {
    document.body.classList.toggle('sidebar-collapsed');
  }

  // Add a listener for screen size changes
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 768) {
        // Default to expanded on larger screens
        document.body.classList.remove('sidebar-collapsed');
      } else {
        // Default to collapsed on smaller screens
        document.body.classList.add('sidebar-collapsed');
      }
    };

    // Set initial state
    handleResize();
    
    // Listen for window resize
    window.addEventListener('resize', handleResize);
    
    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return (
    <ToastProvider>
      <ReportProvider>
        <CycleProvider>
          <ModalProvider>
            <div className="app-container">
              {/* Fixed top navigation */}
              <TopNavigation />
              
              {/* Main content area with sidebar and page content */}
              <div className="content-container">
                <Sidebar />
                
                <div id="page-content-wrapper">
                  <div className="container-fluid p-4">
                    <Routes>
                      <Route path="/" element={<Dashboard />} />
                      <Route path="/calculations" element={<CalculationBuilder />} />
                      <Route path="/reporting" element={<Reporting />} />
                      <Route path="/logs" element={<Logs />} />
                      <Route path="/documentation" element={<Documentation />} />
                    </Routes>
                  </div>
                </div>
              </div>
              
              {/* Sidebar toggle button at bottom of screen */}
              <div className="sidebar-toggle-btn d-none d-md-flex" onClick={toggleSidebar}>
                <i className="bi bi-arrows-angle-expand"></i>
              </div>

              {/* Toast notifications */}
              <Toast />
            </div>

            {/* Global Modals - Rendered at the absolute top level */}
            <GlobalModals />
          </ModalProvider>
        </CycleProvider>
      </ReportProvider>
    </ToastProvider>
  )
}

export default App
