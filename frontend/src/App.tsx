import { useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import TopNavigation from './components/TopNavigation'
import Toast from './components/Toast'
import Dashboard from './pages/Dashboard'
import Resources from './pages/Resources'
import Reporting from './pages/Reporting'
import Logs from './pages/Logs'
import Documentation from './pages/Documentation'
import { ToastProvider } from './context/ToastContext'
import './index.css'  // Import the new layout styles

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
                <Route path="/resources" element={<Resources />} />
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
    </ToastProvider>
  )
}

export default App
