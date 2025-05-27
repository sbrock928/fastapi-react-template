import { Link } from 'react-router-dom';
import styles from '@/styles/pages/Dashboard.module.css';

const Dashboard = () => {
  return (
    <div className={styles.dashboardContainer}>
      <h1 className={styles.dashboardTitle}>Welcome to Vibez + Hype</h1>
      
      <div className={styles.dashboardGrid}>
        <div className={styles.dashboardCard}>
          <div className="d-flex align-items-center">
            <div className={`${styles.icon} ${styles.blue}`}>
              <i className="bi bi-people fs-1"></i>
            </div>
            <div>
              <h5>Resources</h5>
              <p className="mb-0">Manage users, departments, and other resources</p>
            </div>
          </div>
          <Link to="/resources" className={`${styles.dashboardButton} ${styles.blue}`}>
            Manage Resources
          </Link>
        </div>

        <div className={styles.dashboardCard}>
          <div className="d-flex align-items-center">
            <div className={`${styles.icon} ${styles.blue}`}>
              <i className="bi bi-bar-chart fs-1"></i>
            </div>
            <div>
              <h5>Reporting</h5>
              <p className="mb-0">Generate and view reports</p>
            </div>
          </div>
          <Link to="/reporting" className={`${styles.dashboardButton} ${styles.blue}`}>
            View Reports
          </Link>
        </div>

        <div className={styles.dashboardCard}>
          <div className="d-flex align-items-center">
            <div className={`${styles.icon} ${styles.cyan}`}>
              <i className="bi bi-list-ul fs-1"></i>
            </div>
            <div>
              <h5>Logs</h5>
              <p className="mb-0">View application logs and activity</p>
            </div>
          </div>
          <Link to="/logs" className={`${styles.dashboardButton} ${styles.cyan}`}>
            View Logs
          </Link>
        </div>

        <div className={styles.dashboardCard}>
          <div className="d-flex align-items-center">
            <div className={`${styles.icon} ${styles.yellow}`}>
              <i className="bi bi-file-earmark-text fs-1"></i>
            </div>
            <div>
              <h5>Documentation</h5>
              <p className="mb-0">API documentation and guides</p>
            </div>
          </div>
          <Link to="/documentation" className={`${styles.dashboardButton} ${styles.yellow}`}>
            View Docs
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
