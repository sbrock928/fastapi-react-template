#!/bin/bash
# Stop script for Vibez task queue on Unix-like systems

echo "Stopping Vibez Task Queue..."

# Directory containing PID files
LOGS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../task_queue/logs" && pwd)"

# Function to stop a process using its PID file
stop_process() {
    PID_FILE="$LOGS_DIR/$1.pid"
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        echo "Stopping $1 (PID: $PID)..."
        
        if kill -0 $PID 2>/dev/null; then
            kill -TERM $PID
            sleep 2
            if kill -0 $PID 2>/dev/null; then
                echo "Force killing $1..."
                kill -9 $PID 2>/dev/null || true
            fi
            echo "$1 stopped."
        else
            echo "$1 was not running."
        fi
        
        rm -f "$PID_FILE"
    else
        echo "No PID file found for $1."
    fi
}

# Stop all components
stop_process "flower"
stop_process "worker_default"
stop_process "worker_notifications"
stop_process "worker_reports"
stop_process "beat"

echo "All Vibez Task Queue components have been stopped."
