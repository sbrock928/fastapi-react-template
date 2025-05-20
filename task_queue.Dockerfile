# Base image
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY task_queue/requirements.txt /app/task_queue/
RUN pip install --no-cache-dir -r task_queue/requirements.txt

# Copy the application code
COPY . /app/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV VIBEZ_API_URL=http://backend:8000

# Create log directory
RUN mkdir -p /app/task_queue/logs && \
    chmod -R 777 /app/task_queue/logs

# Set the working directory to the project root
WORKDIR /app

# Default command (can be overridden by docker-compose)
CMD ["python", "task_queue/workers/start_all.py"]
