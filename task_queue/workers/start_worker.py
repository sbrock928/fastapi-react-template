#!/usr/bin/env python
"""
Worker process starter script for Vibez task queue
"""

import os
import sys
import argparse
from pathlib import Path

# Ensure the task_queue package is in the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from celery.bin import worker
from task_queue.config.celery_app import app

def start_worker(queue='default', concurrency=None, loglevel='INFO'):
    """Start a Celery worker process"""
    print(f"Starting worker for queue: {queue}")
    
    worker_args = [
        'worker',
        '--app=task_queue.config.celery_app:app',
        f'--queues={queue}',
        f'--loglevel={loglevel}',
        '--hostname=%h_%n',  # Hostname format: hostname_queuename
    ]
    
    if concurrency:
        worker_args.append(f'--concurrency={concurrency}')
    
    # Start the worker
    worker.worker(app=app).run_from_argv(['celery'] + worker_args)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Start Vibez task worker')
    
    parser.add_argument(
        '--queue', 
        type=str, 
        default='default', 
        help='Queue to process (default, reports, notifications)'
    )
    
    parser.add_argument(
        '--concurrency', 
        type=int, 
        help='Number of worker processes'
    )
    
    parser.add_argument(
        '--loglevel', 
        type=str, 
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Log level'
    )
    
    args = parser.parse_args()
    
    start_worker(
        queue=args.queue,
        concurrency=args.concurrency,
        loglevel=args.loglevel
    )
