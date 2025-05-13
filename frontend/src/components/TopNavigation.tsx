const TopNavigation = () => {
  return (
    <nav className="navbar navbar-expand-lg navbar-dark border-bottom top-navbar" style={{ backgroundColor: '#93186C' }}>
      <div className="container-fluid">
        <a className="navbar-brand" href="/">
          <i className="bi bi-soundwave me-2"></i>
          Vibez Admin
        </a>
        <div className="ms-auto d-flex">
          <span className="navbar-text text-white">
            Welcome to Vibes + Hype
          </span>
        </div>
      </div>
    </nav>
  )
}

export default TopNavigation
