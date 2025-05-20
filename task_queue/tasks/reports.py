"""
Report execution tasks
"""

import os
import json
import logging
import datetime
from pathlib import Path
import requests

from celery import shared_task
from sqlalchemy.exc import SQLAlchemyError

from task_queue.config.celery_app import app
from task_queue.config.db import get_db_session

# Configure logging
logger = logging.getLogger('task_queue.tasks.reports')
logger.setLevel(logging.INFO)

# Ensure log directory exists
log_dir = Path(__file__).resolve().parent.parent / 'logs'
log_dir.mkdir(exist_ok=True)

# Add file handler for report tasks
file_handler = logging.FileHandler(log_dir / 'report_tasks.log')
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(file_handler)

@shared_task(bind=True, name='task_queue.tasks.reports.execute_report')
def execute_report(self, report_id, report_params, user_id=None):
    """
    Execute a report with the given parameters
    
    Args:
        report_id: The ID of the report to execute
        report_params: The parameters for the report execution
        user_id: The ID of the user who triggered the report (optional)
    
    Returns:
        dict: The report execution result
    """
    logger.info(f"Executing report {report_id} with params: {report_params}")
    
    try:
        # Get database session
        db = get_db_session()
        
        # Track the task start in the database
        task_id = self.request.id
        now = datetime.datetime.utcnow()
        
        db.execute(
            """
            INSERT INTO report_executions 
            (report_id, task_id, status, started_at, parameters, user_id) 
            VALUES (%s, %s, %s, %s, %s, %s)
            """, 
            (report_id, task_id, 'RUNNING', now, json.dumps(report_params), user_id)
        )
        db.commit()
        
        # Call the report generation API
        api_url = os.environ.get('VIBEZ_API_URL', 'http://localhost:5000')
        
        # Make the API call to the internal reporting endpoint
        response = requests.post(
            f"{api_url}/api/internal/reports/{report_id}/execute",
            json={
                'parameters': report_params,
                'task_id': task_id,
                'user_id': user_id
            },
            headers={'Content-Type': 'application/json'}
        )
        
        response.raise_for_status()
        result = response.json()
        
        # Update the execution status in the database
        db.execute(
            """
            UPDATE report_executions 
            SET status = %s, 
                completed_at = %s, 
                result_path = %s 
            WHERE task_id = %s
            """,
            ('COMPLETED', datetime.datetime.utcnow(), result.get('report_path'), task_id)
        )
        db.commit()
        
        logger.info(f"Report {report_id} execution completed successfully. Result: {result}")
        return result
        
    except requests.RequestException as e:
        logger.error(f"API request failed during report {report_id} execution: {str(e)}")
        _update_report_status(task_id, 'FAILED', error=str(e))
        raise
        
    except SQLAlchemyError as e:
        logger.error(f"Database error during report {report_id} execution: {str(e)}")
        raise
        
    except Exception as e:
        logger.exception(f"Unexpected error during report {report_id} execution: {str(e)}")
        _update_report_status(task_id, 'FAILED', error=str(e))
        raise
        
    finally:
        db.close()


@shared_task(name='task_queue.tasks.reports.schedule_daily_reports')
def schedule_daily_reports():
    """
    Schedule all daily reports that are due to be executed
    """
    logger.info("Scheduling daily reports")
    try:
        db = get_db_session()
        
        # Find all active daily scheduled reports
        scheduled_reports = db.execute(
            """
            SELECT id, report_id, parameters, user_id 
            FROM scheduled_reports 
            WHERE frequency = 'DAILY' 
            AND is_active = TRUE
            """
        ).fetchall()
        
        # Schedule each report as a task
        for report in scheduled_reports:
            execute_report.delay(
                report['report_id'], 
                json.loads(report['parameters']), 
                report['user_id']
            )
            
        logger.info(f"Scheduled {len(scheduled_reports)} daily reports")
        return {'scheduled': len(scheduled_reports)}
        
    except Exception as e:
        logger.exception(f"Error scheduling daily reports: {str(e)}")
        raise
        
    finally:
        db.close()


@shared_task(name='task_queue.tasks.reports.schedule_weekly_reports')
def schedule_weekly_reports():
    """
    Schedule all weekly reports that are due to be executed
    """
    logger.info("Scheduling weekly reports")
    try:
        db = get_db_session()
        today = datetime.datetime.utcnow().strftime('%A').upper()
        
        # Find all active weekly scheduled reports for today's day of week
        scheduled_reports = db.execute(
            """
            SELECT id, report_id, parameters, user_id 
            FROM scheduled_reports 
            WHERE frequency = 'WEEKLY' 
            AND day_of_week = %s
            AND is_active = TRUE
            """,
            (today,)
        ).fetchall()
        
        # Schedule each report as a task
        for report in scheduled_reports:
            execute_report.delay(
                report['report_id'], 
                json.loads(report['parameters']), 
                report['user_id']
            )
            
        logger.info(f"Scheduled {len(scheduled_reports)} weekly reports")
        return {'scheduled': len(scheduled_reports)}
        
    except Exception as e:
        logger.exception(f"Error scheduling weekly reports: {str(e)}")
        raise
        
    finally:
        db.close()


@shared_task(name='task_queue.tasks.reports.schedule_monthly_reports')
def schedule_monthly_reports():
    """
    Schedule all monthly reports that are due to be executed
    """
    logger.info("Scheduling monthly reports")
    try:
        db = get_db_session()
        today = datetime.datetime.utcnow().day
        
        # Find all active monthly scheduled reports for today's day of month
        scheduled_reports = db.execute(
            """
            SELECT id, report_id, parameters, user_id 
            FROM scheduled_reports 
            WHERE frequency = 'MONTHLY' 
            AND day_of_month = %s
            AND is_active = TRUE
            """,
            (today,)
        ).fetchall()
        
        # Schedule each report as a task
        for report in scheduled_reports:
            execute_report.delay(
                report['report_id'], 
                json.loads(report['parameters']), 
                report['user_id']
            )
            
        logger.info(f"Scheduled {len(scheduled_reports)} monthly reports")
        return {'scheduled': len(scheduled_reports)}
        
    except Exception as e:
        logger.exception(f"Error scheduling monthly reports: {str(e)}")
        raise
        
    finally:
        db.close()


def _update_report_status(task_id, status, error=None):
    """Helper function to update report execution status"""
    try:
        db = get_db_session()
        db.execute(
            """
            UPDATE report_executions 
            SET status = %s, 
                completed_at = %s, 
                error = %s 
            WHERE task_id = %s
            """,
            (status, datetime.datetime.utcnow(), error, task_id)
        )
        db.commit()
    except Exception as e:
        logger.error(f"Failed to update report status: {str(e)}")
    finally:
        db.close()
