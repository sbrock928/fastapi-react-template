#!/bin/bash
# Startup script for Vibez task queue on Unix-like systems
# This starts Redis, Celery workers, and Flower monitoring

echo "Starting Vibez Task Queue..."

# Check if Redis is installed and running
echo "Checking Redis..."
if ! redis-cli ping &>/dev/null; then
    echo "Redis is not running. Please start Redis first."
    echo "On Ubuntu/Debian: sudo service redis-server start"
    echo "On macOS with Homebrew: brew services start redis"
    exit 1
fi
echo "Redis is running."

# Set the path to the project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Set Python path to include project root
export PYTHONPATH=$PROJECT_ROOT

# Start Celery Beat scheduler in the background
echo "Starting Celery Beat scheduler..."
cd $PROJECT_ROOT && nohup python task_queue/workers/start_beat.py --loglevel=INFO > task_queue/logs/beat.log 2>&1 &
BEAT_PID=$!
echo $BEAT_PID > task_queue/logs/beat.pid

# Start worker for reports queue
echo "Starting worker for reports queue..."
cd $PROJECT_ROOT && nohup python task_queue/workers/start_worker.py --queue=reports --loglevel=INFO --concurrency=2 > task_queue/logs/worker_reports.log 2>&1 &
WORKER_REPORTS_PID=$!
echo $WORKER_REPORTS_PID > task_queue/logs/worker_reports.pid

# Start worker for notifications queue
echo "Starting worker for notifications queue..."
cd $PROJECT_ROOT && nohup python task_queue/workers/start_worker.py --queue=notifications --loglevel=INFO --concurrency=2 > task_queue/logs/worker_notifications.log 2>&1 &
WORKER_NOTIFICATIONS_PID=$!
echo $WORKER_NOTIFICATIONS_PID > task_queue/logs/worker_notifications.pid

# Start worker for default queue
echo "Starting worker for default queue..."
cd $PROJECT_ROOT && nohup python task_queue/workers/start_worker.py --queue=default --loglevel=INFO --concurrency=2 > task_queue/logs/worker_default.log 2>&1 &
WORKER_DEFAULT_PID=$!
echo $WORKER_DEFAULT_PID > task_queue/logs/worker_default.pid

# Start Flower monitoring
echo "Starting Flower monitoring..."
cd $PROJECT_ROOT && nohup python task_queue/workers/start_flower.py --port=5555 > task_queue/logs/flower.log 2>&1 &
FLOWER_PID=$!
echo $FLOWER_PID > task_queue/logs/flower.pid

echo "Vibez Task Queue started successfully!"
echo "Flower monitoring is available at http://localhost:5555"
echo "Log files are available in task_queue/logs/"
echo "To stop the services, run ./stop.sh"
