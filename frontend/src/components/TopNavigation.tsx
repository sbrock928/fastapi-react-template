interface TopNavigationProps {
  toggleSidebar: () => void;
}

const TopNavigation = ({ toggleSidebar }: TopNavigationProps) => {
  return (
    <nav className="navbar navbar-expand-lg navbar-light bg-light border-bottom">
      <div className="container-fluid">
        <button className="btn btn-primary" id="sidebarToggle" onClick={toggleSidebar}>
          <i className="bi bi-list"></i>
        </button>
        <div className="ms-auto d-flex">
          <span className="navbar-text">
            Welcome to Vibes + Hype
          </span>
        </div>
      </div>
    </nav>
  )
}

export default TopNavigation
