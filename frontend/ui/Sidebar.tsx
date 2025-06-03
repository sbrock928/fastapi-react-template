import { Link, useLocation } from 'react-router-dom';

const Sidebar = () => {
  const location = useLocation();
  
  // Function to check if a route is active
  const isActive = (path: string) => location.pathname === path;
  
  return (
    <div className="bg-light border-right" id="sidebar-wrapper">
      <div className="list-group list-group-flush">
        <Link 
          to="/" 
          className={`list-group-item list-group-item-action d-flex align-items-center ${isActive('/') ? 'active' : ''}`}
        >
          <i className="bi bi-house-door me-3"></i>
          <span className="sidebar-text">Home</span>
        </Link>
        <Link 
          to="/resources" 
          className={`list-group-item list-group-item-action d-flex align-items-center ${isActive('/resources') ? 'active' : ''}`}
        >
          <i className="bi bi-people me-3"></i>
          <span className="sidebar-text">Resources</span>
        </Link>
        <Link 
          to="/calculations" 
          className={`list-group-item list-group-item-action d-flex align-items-center ${isActive('/calculations') ? 'active' : ''}`}
        >
          <i className="bi bi-calculator me-3"></i>
          <span className="sidebar-text">Calculations</span>
        </Link>

        <Link 
          to="/reporting" 
          className={`list-group-item list-group-item-action d-flex align-items-center ${isActive('/reporting') ? 'active' : ''}`}
        >
          <i className="bi bi-bar-chart me-3"></i>
          <span className="sidebar-text">Reporting</span>
        </Link>
        <Link 
          to="/documentation" 
          className={`list-group-item list-group-item-action d-flex align-items-center ${isActive('/documentation') ? 'active' : ''}`}
        >
          <i className="bi bi-file-earmark-text me-3"></i>
          <span className="sidebar-text">Documentation</span>
        </Link>
        <Link 
          to="/logs" 
          className={`list-group-item list-group-item-action d-flex align-items-center ${isActive('/logs') ? 'active' : ''}`}
        >
          <i className="bi bi-list-ul me-3"></i>
          <span className="sidebar-text">Logs</span>
        </Link>

      </div>
    </div>
  );
};

export default Sidebar;
