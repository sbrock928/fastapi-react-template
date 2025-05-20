# Vibez Task Queue Setup

This document provides instructions for setting up and running the Celery task queue for the Vibez application.

## Prerequisites

- Docker Desktop installed and running
- Python 3.9+ installed (for local development)
- Node.js 18+ installed (for frontend development)

## Project Structure

The task queue system consists of:

1. **Redis**: Message broker for Celery
2. **Celery Beat**: Scheduler for periodic tasks
3. **Celery Workers**: Multiple workers for different task types:
   - Reports worker
   - Notifications worker  
   - Default worker
4. **Flower**: Monitoring dashboard for Celery

## Quick Start with Docker Compose

### 1. Start Docker Desktop

Make sure Docker Desktop is running. Look for the Docker icon in your system tray or start it from the Start Menu.

### 2. Run the Docker Compose Stack

```powershell
# Navigate to your project directory
cd 'C:\Users\steph\OneDrive\Documents\Python Projects\Vibez'

# Start all services
docker compose up -d

# To see logs in real-time
docker compose logs -f
```

### 3. Access the Services

- **Flower monitoring dashboard**: http://localhost:5555
- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:5173

## Managing the Task Queue

### Checking Service Status

```powershell
# Check all running containers
docker compose ps

# Check logs for a specific service
docker compose logs redis
docker compose logs celery-worker-reports
docker compose logs celery-beat
docker compose logs flower
```

### Stopping the Services

```powershell
# Stop all services
docker compose down

# Stop all services and remove volumes
docker compose down -v
```

## Troubleshooting

### Docker Connection Issues

If you see an error like `error during connect: ...`, make sure Docker Desktop is running.

```powershell
# Check Docker is running
docker info
```

### Redis Connection Issues

If Celery workers can't connect to Redis:

```powershell
# Check if Redis container is running
docker compose ps redis

# Check Redis logs
docker compose logs redis
```

### Worker Issues

```powershell
# Check worker logs
docker compose logs celery-worker-default
docker compose logs celery-worker-reports
docker compose logs celery-worker-notifications
```

### Service Dependencies

The services are configured with appropriate dependencies and health checks:
- Redis must be healthy before workers start
- Workers must be started before Flower
- Backend should be running for the task queue to work correctly

## Configuration Details

### Docker Compose Configuration

The `docker-compose.yml` file defines all services:

- **Redis**: Uses the official Redis image with data persistence
- **Celery Beat**: Schedules periodic tasks
- **Celery Workers**: Processes tasks from specific queues
- **Flower**: Monitors the Celery cluster
- **Backend**: FastAPI application
- **Frontend**: React application

### Celery Configuration

The Celery configuration is in `task_queue/config/celeryconfig.py`:

- Redis broker/backend URLs
- Task routing to specific queues
- Periodic task schedules
- Worker settings and concurrency

### Environment Variables

Each service uses environment variables for configuration:
- `CELERY_BROKER_URL`: Redis connection string
- `CELERY_RESULT_BACKEND`: Redis connection for storing task results
- `VIBEZ_API_URL`: URL for the backend API

## Local Development

If you prefer to run components separately during development:

### Redis

```powershell
# Start Redis only
docker compose up -d redis
```

### Backend

```powershell
# Start the backend API
cd 'C:\Users\steph\OneDrive\Documents\Python Projects\Vibez'
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```powershell
# Start the frontend dev server
cd 'C:\Users\steph\OneDrive\Documents\Python Projects\Vibez'
npm run dev
```

### Celery Workers (Local)

```powershell
# Start a Celery worker
cd 'C:\Users\steph\OneDrive\Documents\Python Projects\Vibez'
python task_queue/workers/start_worker.py --queue=default --loglevel=INFO
```

## Task Types and Queues

The application uses different queues for different types of tasks:

1. **reports**: For report generation and scheduling tasks
2. **notifications**: For sending notifications to users
3. **default**: For general-purpose tasks

Each queue has a dedicated worker to ensure optimal resource allocation and priority handling.

## Monitoring with Flower

Flower provides a web-based UI for monitoring Celery tasks:

- View active, scheduled, and completed tasks
- Monitor worker status and resource usage
- Cancel or revoke tasks
- View task details and execution history

Access Flower at http://localhost:5555 when the Docker Compose stack is running.

## Notes on Production Deployment

For production environments, consider:

1. Using a production-grade Redis setup with replication
2. Implementing proper authentication for Flower
3. Adding log rotation for container logs
4. Scaling workers based on workload
5. Setting up monitoring and alerts
