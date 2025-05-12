import { useEffect, useState } from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import TopNavigation from './components/TopNavigation'
import Dashboard from './pages/Dashboard'
import Resources from './pages/Resources'
import Reporting from './pages/Reporting'
import Logs from './pages/Logs'
import Documentation from './pages/Documentation'
import './index.css'  // Import the new layout styles

function App() {
  const [sidebarToggled, setSidebarToggled] = useState(true)
  const location = useLocation()

  // Toggle sidebar
  const toggleSidebar = () => {
    setSidebarToggled(!sidebarToggled)
  }

  // Reset sidebar toggle when changing routes on mobile
  useEffect(() => {
    if (window.innerWidth < 768) {
      setSidebarToggled(false)
    }
  }, [location.pathname])

  return (
    <div className={`d-flex ${sidebarToggled ? 'toggled' : ''}`} id="wrapper">
      <Sidebar />
      
      <div id="page-content-wrapper">
        <TopNavigation toggleSidebar={toggleSidebar} />
        
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
  )
}

export default App
