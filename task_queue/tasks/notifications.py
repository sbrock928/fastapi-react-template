"""
Notification tasks for Vibez reports
"""

import logging
from pathlib import Path
import datetime
import json
import requests

from celery import shared_task

from task_queue.config.db import get_db_session

# Configure logging
logger = logging.getLogger('task_queue.tasks.notifications')
logger.setLevel(logging.INFO)

# Ensure log directory exists
log_dir = Path(__file__).resolve().parent.parent / 'logs'
log_dir.mkdir(exist_ok=True)

# Add file handler for notification tasks
file_handler = logging.FileHandler(log_dir / 'notification_tasks.log')
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(file_handler)

@shared_task(name='task_queue.tasks.notifications.send_report_completion_notification')
def send_report_completion_notification(report_execution_id):
    """
    Send a notification to the user that a report has been completed
    
    Args:
        report_execution_id: The ID of the report execution
    """
    logger.info(f"Sending report completion notification for execution {report_execution_id}")
    
    db = None
    try:
        db = get_db_session()
        
        # Get the report execution details
        execution = db.execute(
            """
            SELECT re.id, re.report_id, re.status, re.result_path, 
                   re.user_id, r.name as report_name
            FROM report_executions re
            JOIN reports r ON re.report_id = r.id
            WHERE re.id = %s
            """,
            (report_execution_id,)
        ).fetchone()
        
        if not execution:
            logger.error(f"Report execution {report_execution_id} not found")
            return {'status': 'error', 'message': 'Report execution not found'}
        
        # Get the user's notification preferences
        user = db.execute(
            """
            SELECT email, email_notifications_enabled, 
                   system_notifications_enabled
            FROM users
            WHERE id = %s
            """,
            (execution['user_id'],)
        ).fetchone()
        
        if not user:
            logger.error(f"User {execution['user_id']} not found")
            return {'status': 'error', 'message': 'User not found'}
        
        notification_sent = False
        
        # Send email notification if enabled
        if user['email_notifications_enabled'] and user['email']:
            _send_email_notification(
                user['email'],
                execution['report_name'],
                execution['status'],
                execution['result_path']
            )
            notification_sent = True
        
        # Send system notification if enabled
        if user['system_notifications_enabled']:
            _send_system_notification(
                execution['user_id'],
                execution['report_name'],
                execution['status'],
                execution['result_path']
            )
            notification_sent = True
        
        # Record the notification in the database
        if notification_sent:
            db.execute(
                """
                INSERT INTO notifications 
                (user_id, type, message, created_at, reference_id) 
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    execution['user_id'],
                    'REPORT_COMPLETION',
                    f"Report '{execution['report_name']}' completed with status: {execution['status']}",
                    datetime.datetime.utcnow(),
                    report_execution_id
                )
            )
            db.commit()
        
        logger.info(f"Notification for report execution {report_execution_id} sent successfully")
        return {'status': 'success', 'notification_sent': notification_sent}
        
    except Exception as e:
        logger.exception(f"Error sending notification for report execution {report_execution_id}: {str(e)}")
        if db:
            db.rollback()
        return {'status': 'error', 'message': str(e)}
        
    finally:
        if db:
            db.close()


def _send_email_notification(email, report_name, status, result_path):
    """
    Send an email notification
    
    Args:
        email: The recipient's email address
        report_name: The name of the report
        status: The status of the report execution
        result_path: The path to the report result file
    """
    logger.info(f"Sending email notification to {email} for report '{report_name}'")
    
    # In a production environment, you would integrate with an email service
    # For now, we'll just log the notification
    logger.info(f"EMAIL: To: {email}, Subject: Report '{report_name}' {status}")
    logger.info(f"EMAIL BODY: Your report '{report_name}' has been completed with status: {status}.")
    
    if status == 'COMPLETED' and result_path:
        logger.info(f"EMAIL BODY: You can download the report at: {result_path}")


def _send_system_notification(user_id, report_name, status, result_path):
    """
    Send a system notification
    
    Args:
        user_id: The ID of the user
        report_name: The name of the report
        status: The status of the report execution
        result_path: The path to the report result file
    """
    logger.info(f"Sending system notification to user {user_id} for report '{report_name}'")
    
    # In a real implementation, this would notify the frontend via WebSockets or similar
    notification = {
        'user_id': user_id,
        'type': 'REPORT_COMPLETION',
        'title': f"Report '{report_name}' {status.lower()}",
        'message': f"Your report '{report_name}' has been completed with status: {status}.",
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'data': {
            'report_name': report_name,
            'status': status,
            'result_path': result_path
        }
    }
    
    # In a production environment, you would push this notification to the user
    # For now, we'll just log the notification
    logger.info(f"SYSTEM NOTIFICATION: {json.dumps(notification)}")
