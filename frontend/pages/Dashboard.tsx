import { Link } from 'react-router-dom';

const Dashboard = () => {
  return (
    <div className="dashboard-container">

      
<div className="dashboard-grid">
  <div className="dashboard-card">
    <i className="bi bi-people icon blue"></i>
    <h3>Manage Resources</h3>
    <p>Efficiently manage users and employees from a single dashboard.</p>
    <Link to="/resources" className="dashboard-button blue">Go to Resources</Link>
  </div>

  <div className="dashboard-card">
    <i className="bi bi-bar-chart icon green"></i>
    <h3>Reporting</h3>
    <p>Generate and export SQL reports with customizable parameters.</p>
    <Link to="/reporting" className="dashboard-button green">Go to Reporting</Link>
  </div>

  <div className="dashboard-card">
    <i className="bi bi-file-earmark-text icon cyan"></i>
    <h3>Documentation</h3>
    <p>Access interactive API documentation and explore available endpoints.</p>
    <Link to="/documentation" className="dashboard-button cyan">View Documentation</Link>
  </div>

  <div className="dashboard-card">
    <i className="bi bi-list-ul icon yellow"></i>
    <h3>System Logs</h3>
    <p>Monitor all application requests, responses, and performance metrics.</p>
    <Link to="/logs" className="dashboard-button yellow">View Logs</Link>
  </div>
</div>
    </div>
  );
};

export default Dashboard;
