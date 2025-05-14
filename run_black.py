#!/usr/bin/env python3
"""
Script to run black and mypy on the Vibez codebase.
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

def run_mypy():
    """Run mypy on the codebase"""
    print("Running mypy on the Vibez codebase...")
    
    # Get the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Run mypy on the app directory
    try:
        subprocess.run(
            ["mypy", f"{project_root}/app"], 
            check=True
        )
        print("Mypy type checking completed successfully!")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Error running mypy: {e}")
        return 1

if __name__ == "__main__":
    black_result = run_black()
    mypy_result = run_mypy()
    sys.exit(black_result or mypy_result)  # Exit with error if either tool failed
