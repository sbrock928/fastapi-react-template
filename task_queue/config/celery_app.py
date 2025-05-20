"""
Celery configuration for Vibez task queue
"""

from celery import Celery
import os
from pathlib import Path

# Set the default Django settings module
os.environ.setdefault('PROJECT_ROOT', str(Path(__file__).resolve().parent.parent.parent))

# Create the Celery app
app = Celery('vibez_tasks')

# Load configuration from Python module
app.config_from_object('task_queue.config.celeryconfig')

# Auto-discover tasks from all registered apps
app.autodiscover_tasks(['task_queue.tasks'])

if __name__ == '__main__':
    app.start()
