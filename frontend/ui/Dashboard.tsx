import { Link } from 'react-router-dom';
import styles from '@/styles/pages/Dashboard.module.css';

const Dashboard = () => {
  return (
    <div className={styles.dashboardContainer}>
      <h1 className={styles.dashboardTitle}>Welcome to Vibez + Hype</h1>
      
      <div className={styles.dashboardGrid}>
        <div className={styles.dashboardCard}>
          <div className={styles.cardHeader}>
            <div className={`${styles.icon} ${styles.green}`}>
              <i className="bi bi-calculator fs-1"></i>
            </div>
            <div className={styles.cardContent}>
              <h5 className={styles.cardTitle}>Calculations</h5>
              <p className={styles.cardDescription}>Build and manage calculation formulas</p>
            </div>
          </div>
          <Link to="/calculations" className={`${styles.dashboardButton} ${styles.green}`}>
            Manage Calculations
          </Link>
        </div>

        <div className={styles.dashboardCard}>
          <div className={styles.cardHeader}>
            <div className={`${styles.icon} ${styles.purple}`}>
              <i className="bi bi-bar-chart fs-1"></i>
            </div>
            <div className={styles.cardContent}>
              <h5 className={styles.cardTitle}>Reporting</h5>
              <p className={styles.cardDescription}>Generate reports and analyze data</p>
            </div>
          </div>
          <Link to="/reporting" className={`${styles.dashboardButton} ${styles.purple}`}>
            Create Reports
          </Link>
        </div>

        <div className={styles.dashboardCard}>
          <div className={styles.cardHeader}>
            <div className={`${styles.icon} ${styles.orange}`}>
              <i className="bi bi-file-earmark-text fs-1"></i>
            </div>
            <div className={styles.cardContent}>
              <h5 className={styles.cardTitle}>Documentation</h5>
              <p className={styles.cardDescription}>View guides and API documentation</p>
            </div>
          </div>
          <Link to="/documentation" className={`${styles.dashboardButton} ${styles.orange}`}>
            View Documentation
          </Link>
        </div>

        <div className={styles.dashboardCard}>
          <div className={styles.cardHeader}>
            <div className={`${styles.icon} ${styles.red}`}>
              <i className="bi bi-list-ul fs-1"></i>
            </div>
            <div className={styles.cardContent}>
              <h5 className={styles.cardTitle}>System Logs</h5>
              <p className={styles.cardDescription}>Monitor system activity and errors</p>
            </div>
          </div>
          <Link to="/logs" className={`${styles.dashboardButton} ${styles.red}`}>
            View Logs
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
