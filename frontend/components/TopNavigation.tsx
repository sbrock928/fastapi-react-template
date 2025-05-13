const TopNavigation = () => {
  return (
    <nav className="navbar navbar-expand-lg navbar-dark border-bottom top-navbar" style={{ backgroundColor: '#93186C' }}>
      <div className="container-fluid">
        <a className="navbar-brand d-flex align-items-center" href="/">
          <img src="/vite.svg" alt="Vibez Logo" className="me-2" style={{ height: "24px" }} />
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
