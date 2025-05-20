# Vibez Task Queue

This directory contains the Celery task queue implementation for the Vibez application, which handles asynchronous report execution and scheduling.

## Structure

```
task_queue/
  ├── config/           # Configuration files
  │   ├── celery_app.py # Main Celery app configuration
  │   ├── celeryconfig.py # Celery settings
  │   ├── db.py         # Database connection utilities
  │   └── schema.sql    # SQL schema for task queue tables
  ├── tasks/            # Task definitions
  │   ├── reports.py    # Report execution tasks
  │   └── notifications.py # Notification tasks
  ├── workers/          # Worker scripts
  │   ├── start_worker.py  # Worker starter
  │   ├── start_beat.py    # Beat scheduler starter
  │   ├── start_flower.py  # Flower monitoring starter
  │   └── start_all.py     # Script to start all components
  └── logs/             # Log files
```

## Requirements

- Python 3.8+
- Redis server (used as the message broker)
- Dependencies listed in `requirements.txt`

## Setup

1. Install the required packages:

   ```bash
   pip install -r task_queue/requirements.txt
   ```

2. Make sure Redis is installed and running:

   - **Windows**: Download from [GitHub](https://github.com/microsoftarchive/redis/releases) and start `redis-server.exe`
   - **macOS**: `brew install redis` then `brew services start redis`
   - **Linux**: `sudo apt install redis-server` then `sudo systemctl start redis`

3. Create the necessary database tables:

   ```bash
   psql -U your_username -d your_database -f task_queue/config/schema.sql
   ```

## Starting the Task Queue

### On Windows

Run the provided batch script:

```cmd
task_queue\start_windows.bat
```

### On Unix-like systems (Linux/macOS)

Run the provided shell script:

```bash
chmod +x task_queue/start.sh
./task_queue/start.sh
```

Alternatively, you can use Docker Compose:

```bash
cd task_queue
docker-compose up -d
```

## Stopping the Task Queue

### On Windows

Run the provided batch script:

```cmd
task_queue\stop_windows.bat
```

### On Unix-like systems (Linux/macOS)

Run the provided shell script:

```bash
chmod +x task_queue/stop.sh
./task_queue/stop.sh
```

If using Docker Compose:

```bash
cd task_queue
docker-compose down
```

## Monitoring

The task queue includes the Flower monitoring tool, which provides a web UI for monitoring tasks, workers, and queues.

Access the Flower dashboard at: [http://localhost:5555](http://localhost:5555)

## Components

### Celery App

The main Celery application is defined in `config/celery_app.py`. This is the entry point for all Celery operations.

### Tasks

- **Report Tasks**: Defined in `tasks/reports.py`, these tasks handle asynchronous report generation.
- **Notification Tasks**: Defined in `tasks/notifications.py`, these tasks send notifications about report completion.

### Workers

- **Report Workers**: Process tasks in the `reports` queue.
- **Notification Workers**: Process tasks in the `notifications` queue.
- **Default Workers**: Process tasks in the default queue.

### Scheduler

Celery Beat is used to schedule periodic tasks, such as daily, weekly, or monthly reports.

## Usage in Code

To execute a report asynchronously:

```python
from task_queue.tasks.reports import execute_report

# Submit a report execution task
task = execute_report.delay(report_id, parameters, user_id)

# Get the task ID for status tracking
task_id = task.id
```

## API Endpoints

The following endpoints are available for interacting with the task queue:

- `POST /reports/execute-async/{report_id}`: Execute a report asynchronously
- `GET /reports/executions`: Get report execution history
- `GET /reports/executions/{execution_id}`: Get details of a specific execution
- `POST /reports/schedules`: Create a new scheduled report
- `GET /reports/schedules`: Get all scheduled reports
- `GET /reports/schedules/{report_id}`: Get a specific scheduled report
- `PUT /reports/schedules/{report_id}`: Update a scheduled report
- `DELETE /reports/schedules/{report_id}`: Delete a scheduled report
