#!/usr/bin/env python
"""
Flower monitoring tool starter script for Vibez task queue
"""

import os
import sys
import argparse
from pathlib import Path

# Ensure the task_queue package is in the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

def start_flower(port=5555, address='0.0.0.0', broker=None):
    """Start the Flower monitoring tool"""
    print(f"Starting Flower monitoring tool on {address}:{port}")
    
    # Build command arguments
    flower_args = ['celery', 'flower', '--app=task_queue.config.celery_app:app']
    
    if port:
        flower_args.append(f'--port={port}')
        
    if address:
        flower_args.append(f'--address={address}')
        
    if broker:
        flower_args.append(f'--broker={broker}')
    
    # Convert to space-separated string
    command = ' '.join(flower_args)
    
    # Execute the command
    os.system(command)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Start Flower monitoring tool for Vibez task queue')
    
    parser.add_argument(
        '--port', 
        type=int, 
        default=5555,
        help='Port to run the Flower web server on'
    )
    
    parser.add_argument(
        '--address', 
        type=str, 
        default='0.0.0.0',
        help='Address to bind the Flower web server to'
    )
    
    parser.add_argument(
        '--broker', 
        type=str,
        help='Broker URL (defaults to the one in celeryconfig.py)'
    )
    
    args = parser.parse_args()
    
    start_flower(
        port=args.port,
        address=args.address,
        broker=args.broker
    )
