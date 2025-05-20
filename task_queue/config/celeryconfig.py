"""
Celery configuration settings
"""
import os

# Broker settings - using Redis in Docker
broker_url = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
result_backend = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')

# Task serialization format
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'UTC'
enable_utc = True

# Worker settings
worker_concurrency = 4  # Number of worker processes
worker_max_tasks_per_child = 100  # Maximum number of tasks a worker process executes before it's replaced

# Task routing
task_routes = {
    'task_queue.tasks.reports.*': {'queue': 'reports'},
    'task_queue.tasks.notifications.*': {'queue': 'notifications'},
}

# Task default rate limits
task_default_rate_limit = '10/m'  # 10 tasks per minute

# Beat schedule settings for periodic tasks
beat_schedule = {
    'daily-report-scheduler': {
        'task': 'task_queue.tasks.reports.schedule_daily_reports',
        'schedule': 3600.0 * 24,  # Execute once per day (seconds)
        'args': (),
    },
    'weekly-report-scheduler': {
        'task': 'task_queue.tasks.reports.schedule_weekly_reports',
        'schedule': 3600.0 * 24 * 7,  # Execute once per week (seconds)
        'args': (),
    },
    'monthly-report-scheduler': {
        'task': 'task_queue.tasks.reports.schedule_monthly_reports',
        'schedule': 3600.0 * 24 * 30,  # Execute approximately once per month (seconds)
        'args': (),
    },
}

# Task monitoring
task_send_sent_event = True  # Required for task monitoring tools like Flower
task_track_started = True
worker_send_task_events = True

# Task time limits
task_time_limit = 3600  # Hard time limit in seconds
task_soft_time_limit = 3000  # Soft time limit

# Task result settings
result_expires = 60 * 60 * 24 * 7  # Results expire in 1 week