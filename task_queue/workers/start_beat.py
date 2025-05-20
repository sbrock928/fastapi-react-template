#!/usr/bin/env python
"""
Celery Beat scheduler starter script for Vibez task queue
"""

import os
import sys
import argparse
from pathlib import Path

# Ensure the task_queue package is in the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from celery.bin import beat
from task_queue.config.celery_app import app

def start_beat(loglevel='INFO'):
    """Start the Celery Beat scheduler"""
    print("Starting Celery Beat scheduler")
    
    beat_args = [
        'beat',
        '--app=task_queue.config.celery_app:app',
        f'--loglevel={loglevel}',
        '--schedule=celerybeat-schedule.db',  # Database file for the scheduler
    ]
    
    # Start the beat scheduler
    beat.beat(app=app).run_from_argv(['celery'] + beat_args)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Start Vibez Celery Beat scheduler')
    
    parser.add_argument(
        '--loglevel', 
        type=str, 
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Log level'
    )
    
    args = parser.parse_args()
    
    start_beat(loglevel=args.loglevel)
