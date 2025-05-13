FROM python:3.12-slim

WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend code
COPY app/ ./app/
COPY main.py .
# Copy the static directory
COPY static/ ./static/

# Set environment variable for development mode
ENV VIBEZ_DEV_MODE=true

# Expose the port
EXPOSE 8000

# Command to run the application
CMD ["python", "main.py"]