import { Link } from 'react-router-dom';

const Dashboard = () => {
  return (
    <div>
      <h1>Dashboard</h1>
      <p>Welcome to the Vibez admin dashboard.</p>
      
      <div className="row mt-4">
        <div className="col-md-4 mb-4">
          <div className="card">
            <div className="card-header bg-primary text-white">
              <h5 className="card-title mb-0">Resources</h5>
            </div>
            <div className="card-body">
              <p className="card-text">Manage users, employees, and subscribers in the system.</p>
              <a href="/resources" className="btn btn-primary">Go to Resources</a>
            </div>
          </div>
        </div>
        
        <div className="col-md-4 mb-4">
          <div className="card">
            <div className="card-header bg-success text-white">
              <h5 className="card-title mb-0">Reporting</h5>
            </div>
            <div className="card-body">
              <p className="card-text">View reports and analytics about system usage.</p>
              <a href="/reporting" className="btn btn-success">Go to Reporting</a>
            </div>
          </div>
        </div>
        
        <div className="col-md-4 mb-4">
          <div className="card">
            <div className="card-header bg-info text-white">
              <h5 className="card-title mb-0">Logs</h5>
            </div>
            <div className="card-body">
              <p className="card-text">Review system logs and API request history.</p>
              <a href="/logs" className="btn btn-info">View Logs</a>
            </div>
          </div>
        </div>

        {/* Documentation Card */}
        <div className="col-xl-3 col-md-6 mb-4">
          <div className="card border-left-info shadow h-100 py-2">
            <div className="card-body">
              <div className="row no-gutters align-items-center">
                <div className="col mr-2">
                  <div className="text-xs font-weight-bold text-info text-uppercase mb-1">
                    Documentation
                  </div>
                  <div className="h5 mb-0 font-weight-bold text-gray-800">API Docs</div>
                </div>
                <div className="col-auto">
                  <i className="bi bi-file-earmark-text fa-2x text-gray-300"></i>
                </div>
              </div>
            </div>
            <div className="card-footer bg-transparent border-0 text-end">
              <Link to="/documentation" className="btn btn-sm btn-info">
                View Docs <i className="bi bi-arrow-right"></i>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
