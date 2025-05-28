import { Link } from 'react-router-dom';
import styles from '@/styles/pages/Dashboard.module.css';

const Dashboard = () => {
  return (
    <div className={styles.dashboardContainer}>
      <h1 className={styles.dashboardTitle}>Welcome to Vibez + Hype</h1>
      
      <div className={styles.dashboardGrid}>
        <div className={styles.dashboardCard}>
          <div className={styles.cardHeader}>
            <div className={`${styles.icon} ${styles.blue}`}>
              <i className="bi bi-people fs-1"></i>
            </div>
            <div className={styles.cardContent}>
              <h5 className={styles.cardTitle}>Resources</h5>
              <p className={styles.cardDescription}>Manage users, departments, and other resources</p>
            </div>
          </div>
          <Link to="/resources" className={`${styles.dashboardButton} ${styles.blue}`}>
            Manage Resources
          </Link>
        </div>

        <div className={styles.dashboardCard}>
          <div className={styles.cardHeader}>
            <div className={`${styles.icon} ${styles.blue}`}>
              <i className="bi bi-bar-chart fs-1"></i>
            </div>
            <div className={styles.cardContent}>
              <h5 className={styles.cardTitle}>Reporting</h5>
              <p className={styles.cardDescription}>Generate and view reports</p>
            </div>
          </div>
          <Link to="/reporting" className={`${styles.dashboardButton} ${styles.blue}`}>
            View Reports
          </Link>
        </div>

        <div className={styles.dashboardCard}>
          <div className={styles.cardHeader}>
            <div className={`${styles.icon} ${styles.cyan}`}>
              <i className="bi bi-list-ul fs-1"></i>
            </div>
            <div className={styles.cardContent}>
              <h5 className={styles.cardTitle}>Logs</h5>
              <p className={styles.cardDescription}>View application logs and activity</p>
            </div>
          </div>
          <Link to="/logs" className={`${styles.dashboardButton} ${styles.cyan}`}>
            View Logs
          </Link>
        </div>

        <div className={styles.dashboardCard}>
          <div className={styles.cardHeader}>
            <div className={`${styles.icon} ${styles.yellow}`}>
              <i className="bi bi-file-earmark-text fs-1"></i>
            </div>
            <div className={styles.cardContent}>
              <h5 className={styles.cardTitle}>Documentation</h5>
              <p className={styles.cardDescription}>API documentation and guides</p>
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
