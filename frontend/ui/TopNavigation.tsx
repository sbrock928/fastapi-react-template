import viteLogo from '../assets/vite.svg';
import styles from '../styles/ui/TopNavigation.module.css';

const TopNavigation = () => {
  return (
    <nav className={`navbar navbar-expand-lg navbar-dark border-bottom top-navbar ${styles.topNavbar}`}>
      <div className="container-fluid">
        <a className={`navbar-brand ${styles.navbarBrand}`} href="/">
          <img src={viteLogo} alt="Vibez Logo" className={`me-2 ${styles.logo}`} />
        </a>
        <div className="ms-auto d-flex">
          <span className={`navbar-text ${styles.navbarText}`}>
            Welcome to Vibes + Hype
          </span>
        </div>
      </div>
    </nav>
  )
}

export default TopNavigation
