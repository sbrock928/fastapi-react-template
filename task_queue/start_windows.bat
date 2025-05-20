@echo off
REM Startup script for Vibez task queue on Windows
REM This starts Redis, Celery workers, and Flower monitoring

echo Starting Vibez Task Queue...

REM Check if Redis is installed and running
echo Checking Redis...

REM Try to use redis-cli from the Redis install directory
SET REDIS_CLI="C:\Program Files\Redis\redis-cli.exe"

REM Check if the file exists
if exist %REDIS_CLI% (
    %REDIS_CLI% ping > nul 2>&1
) else (
    REM Try with just the command name (if it's in PATH)
    redis-cli ping > nul 2>&1
)

if %ERRORLEVEL% neq 0 (
    echo Redis is not running. Please start Redis first.
    echo You can download Redis for Windows from: https://github.com/microsoftarchive/redis/releases
    echo Then run: redis-server.exe
    echo Make sure Redis is running before trying again.
    exit /b 1
)
echo Redis is running.

REM Set the path to the project root
set PROJECT_ROOT=%~dp0..

REM Set Python path to include project root
set PYTHONPATH=%PROJECT_ROOT%

REM Start Celery Beat scheduler in the background
echo Starting Celery Beat scheduler...
start "Vibez Celery Beat" cmd /c "cd %PROJECT_ROOT% && python task_queue/workers/start_beat.py --loglevel=INFO"

REM Start worker for reports queue
echo Starting worker for reports queue...
start "Vibez Reports Worker" cmd /c "cd %PROJECT_ROOT% && python task_queue/workers/start_worker.py --queue=reports --loglevel=INFO --concurrency=2"

REM Start worker for notifications queue
echo Starting worker for notifications queue...
start "Vibez Notifications Worker" cmd /c "cd %PROJECT_ROOT% && python task_queue/workers/start_worker.py --queue=notifications --loglevel=INFO --concurrency=2"

REM Start worker for default queue
echo Starting worker for default queue...
start "Vibez Default Worker" cmd /c "cd %PROJECT_ROOT% && python task_queue/workers/start_worker.py --queue=default --loglevel=INFO --concurrency=2"

REM Start Flower monitoring
echo Starting Flower monitoring...
start "Vibez Flower Monitoring" cmd /c "cd %PROJECT_ROOT% && python task_queue/workers/start_flower.py --port=5555"

echo Vibez Task Queue started successfully!
echo Flower monitoring is available at http://localhost:5555
echo Press Ctrl+C in any window to stop a specific component
