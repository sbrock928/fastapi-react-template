#!/usr/bin/env python3
"""
Script to run black on the Vibez codebase.
"""
import subprocess
import os
import sys

def run_black():
    """Run black on the codebase"""
    print("Running black on the Vibez codebase...")
    
    # Get the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Run black on the app directory
    try:
        subprocess.run(
            ["black", f"{project_root}/app"], 
            check=True
        )
        print("Black formatting completed successfully!")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Error running black: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(run_black())
