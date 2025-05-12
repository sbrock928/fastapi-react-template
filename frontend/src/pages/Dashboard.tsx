const Dashboard = () => {
  return (
    <div>
      <h1>Dashboard</h1>
      <p>Welcome to the Vibes + Hype application dashboard.</p>
      
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
      </div>
    </div>
  )
}

export default Dashboard
