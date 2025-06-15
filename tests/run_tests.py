"""
Test runner script for the FastAPI React Template test suite.
Provides easy commands to run different test categories and generate coverage reports.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle output"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode == 0

def main():
    """Main test runner"""
    # Change to project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    if len(sys.argv) < 2:
        print("Usage: python tests/run_tests.py [command]")
        print("\nAvailable commands:")
        print("  all          - Run all tests")
        print("  unit         - Run unit tests only") 
        print("  functional   - Run functional tests only")
        print("  api          - Run API tests only")
        print("  coverage     - Run tests with coverage report")
        print("  reporting    - Run reporting module tests only")
        print("  calculations - Run calculations module tests only")
        print("  install      - Install test dependencies")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "install":
        success = run_command(
            "pip install pytest pytest-asyncio pytest-cov httpx",
            "Installing test dependencies"
        )
        if success:
            print("\n✅ Test dependencies installed successfully!")
        else:
            print("\n❌ Failed to install test dependencies")
            sys.exit(1)
    
    elif command == "all":
        success = run_command(
            "python -m pytest tests/ -v",
            "Running all tests"
        )
        
    elif command == "unit":
        success = run_command(
            "python -m pytest tests/unit/ -v",
            "Running unit tests"
        )
        
    elif command == "functional":
        success = run_command(
            "python -m pytest tests/functional/ -v",
            "Running functional tests"
        )
        
    elif command == "api":
        success = run_command(
            "python -m pytest tests/functional/test_*_api.py -v",
            "Running API tests"
        )
        
    elif command == "coverage":
        success = run_command(
            "python -m pytest tests/ --cov=app --cov-report=html --cov-report=term-missing -v",
            "Running tests with coverage report"
        )
        if success:
            print("\n📊 Coverage report generated in htmlcov/index.html")
            
    elif command == "reporting":
        success = run_command(
            "python -m pytest tests/ -k 'reporting' -v",
            "Running reporting module tests"
        )
        
    elif command == "calculations":
        success = run_command(
            "python -m pytest tests/ -k 'calculation' -v",
            "Running calculations module tests"
        )
        
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
    
    if success:
        print("\n✅ Tests completed successfully!")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()