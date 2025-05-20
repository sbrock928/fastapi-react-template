#!/usr/bin/env python
"""
Script to start all components of the Vibez task queue
"""

import os
import sys
import time
import argparse
import subprocess
import signal
from pathlib import Path

# Ensure the task_queue package is in the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Track all processes we start
PROCESSES = []

def signal_handler(sig, frame):
    """Handle termination signals and stop all child processes"""
    print("\nShutting down all processes...")
    for process in PROCESSES:
        if process.poll() is None:  # Process is still running
            process.terminate()
            
    print("All processes terminated. Exiting.")
    sys.exit(0)

def start_all(loglevel='INFO', concurrency=None, flower_port=5555):
    """Start all components of the task queue"""
    print("Starting Vibez Task Queue System")
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Path to this file's directory
    workers_dir = Path(__file__).resolve().parent
    
    # Start the Redis server if needed (not on Windows as it's usually installed separately)
    if os.name != 'nt':
        try:
            redis_process = subprocess.Popen(
                ['redis-server'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            PROCESSES.append(redis_process)
            print("Started Redis server")
        except Exception as e:
            print(f"Failed to start Redis server: {e}")
            print("Make sure Redis is installed and in your PATH")
            print("Continuing anyway, assuming Redis is running elsewhere...")
    else:
        print("On Windows, please make sure Redis server is running separately")
    
    # Start Celery Beat scheduler
    beat_process = subprocess.Popen(
        [
            sys.executable, str(workers_dir / 'start_beat.py'),
            f'--loglevel={loglevel}'
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    PROCESSES.append(beat_process)
    print("Started Celery Beat scheduler")
    
    # Start worker for the reports queue
    reports_worker_args = [
        sys.executable, str(workers_dir / 'start_worker.py'),
        '--queue=reports',
        f'--loglevel={loglevel}'
    ]
    if concurrency:
        reports_worker_args.append(f'--concurrency={concurrency}')
        
    reports_worker_process = subprocess.Popen(
        reports_worker_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    PROCESSES.append(reports_worker_process)
    print("Started worker for reports queue")
    
    # Start worker for the notifications queue
    notif_worker_args = [
        sys.executable, str(workers_dir / 'start_worker.py'),
        '--queue=notifications',
        f'--loglevel={loglevel}'
    ]
    if concurrency:
        notif_worker_args.append(f'--concurrency={concurrency}')
        
    notif_worker_process = subprocess.Popen(
        notif_worker_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    PROCESSES.append(notif_worker_process)
    print("Started worker for notifications queue")
    
    # Start worker for the default queue
    default_worker_args = [
        sys.executable, str(workers_dir / 'start_worker.py'),
        '--queue=default',
        f'--loglevel={loglevel}'
    ]
    if concurrency:
        default_worker_args.append(f'--concurrency={concurrency}')
        
    default_worker_process = subprocess.Popen(
        default_worker_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    PROCESSES.append(default_worker_process)
    print("Started worker for default queue")
    
    # Start Flower monitoring
    flower_process = subprocess.Popen(
        [
            sys.executable, str(workers_dir / 'start_flower.py'),
            f'--port={flower_port}'
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    PROCESSES.append(flower_process)
    print(f"Started Flower monitoring tool on port {flower_port}")
    
    print("\nVibez Task Queue System is now running")
    print("Press Ctrl+C to stop all processes")
    
    # Keep the script alive to allow for Ctrl+C to terminate all processes
    try:
        while True:
            # Check if any process has terminated unexpectedly
            for i, process in enumerate(list(PROCESSES)):
                if process.poll() is not None:  # Process has terminated
                    print(f"Process {i} terminated with exit code {process.poll()}")
                    PROCESSES.remove(process)
                    
            if not PROCESSES:
                print("All processes have terminated. Exiting.")
                return
                
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Start all Vibez task queue components')
    
    parser.add_argument(
        '--loglevel', 
        type=str, 
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Log level for all components'
    )
    
    parser.add_argument(
        '--concurrency', 
        type=int, 
        help='Number of worker processes for each queue'
    )
    
    parser.add_argument(
        '--flower-port', 
        type=int, 
        default=5555,
        help='Port for Flower monitoring tool'
    )
    
    args = parser.parse_args()
    
    start_all(
        loglevel=args.loglevel,
        concurrency=args.concurrency,
        flower_port=args.flower_port
    )
