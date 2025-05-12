import { Link, useLocation } from 'react-router-dom';

const Sidebar = () => {
  const location = useLocation();
  
  // Function to check if a route is active
  const isActive = (path: string) => location.pathname === path;
  
  return (
    <div className="bg-light border-right" id="sidebar-wrapper">
      <div className="sidebar-heading">Vibez Admin</div>
      <div className="list-group list-group-flush">
        <Link 
          to="/" 
          className={`list-group-item list-group-item-action ${isActive('/') ? 'active' : ''}`}
        >
          <i className="bi bi-speedometer2 me-2"></i>
          Dashboard
        </Link>
        <Link 
          to="/resources" 
          className={`list-group-item list-group-item-action ${isActive('/resources') ? 'active' : ''}`}
        >
          <i className="bi bi-people me-2"></i>
          Resources
        </Link>
        <Link 
          to="/reporting" 
          className={`list-group-item list-group-item-action ${isActive('/reporting') ? 'active' : ''}`}
        >
          <i className="bi bi-bar-chart me-2"></i>
          Reporting
        </Link>
        <Link 
          to="/logs" 
          className={`list-group-item list-group-item-action ${isActive('/logs') ? 'active' : ''}`}
        >
          <i className="bi bi-list-ul me-2"></i>
          Logs
        </Link>
        <Link 
          to="/documentation" 
          className={`list-group-item list-group-item-action ${isActive('/documentation') ? 'active' : ''}`}
        >
          <i className="bi bi-file-earmark-text me-2"></i>
          Documentation
        </Link>
      </div>
    </div>
  );
};

export default Sidebar;
