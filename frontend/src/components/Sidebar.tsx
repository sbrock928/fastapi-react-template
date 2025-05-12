import { NavLink } from 'react-router-dom'

const Sidebar = () => {
  return (
    <div className="bg-dark text-white" id="sidebar-wrapper">
      <div className="sidebar-heading p-3">
        <h3>Vibes + Hype</h3>
      </div>
      <div className="list-group list-group-flush">
        <div className="sidebar">
          <ul className="nav flex-column">
            <li className="nav-item">
              <NavLink className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`} to="/">
                <i className="bi bi-house-door"></i> Dashboard
              </NavLink>
            </li>
            <li className="nav-item">
              <NavLink className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`} to="/resources">
                <i className="bi bi-people"></i> Resources
              </NavLink>
            </li>
            <li className="nav-item">
              <NavLink className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`} to="/reporting">
                <i className="bi bi-bar-chart"></i> Reporting
              </NavLink>
            </li>
            <li className="nav-item">
              <NavLink className={({isActive}) => `nav-link ${isActive ? 'active' : ''}`} to="/logs">
                <i className="bi bi-journal-text"></i> Logs
              </NavLink>
            </li>
          </ul>
        </div>
      </div>
    </div>
  )
}

export default Sidebar
