#!/usr/bin/env python3
"""
Script to run mypy on the Vibez codebase with a focus on gradual adoption.
"""
import subprocess
import os
import sys
import argparse


def run_mypy(module_path=None, report_file=None, check_mode=False):
    """Run mypy on the codebase with specified options"""
    print("Running mypy type checking on the Vibez codebase...")
    
    # Get the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Set the target path (default to app directory)
    target_path = f"{project_root}/{module_path}" if module_path else f"{project_root}/app"
    
    # Basic command
    mypy_cmd = ["mypy"]
    
    # Add options based on check mode
    if check_mode:
        # Strict mode for checking
        mypy_cmd.extend(["--disallow-untyped-defs", "--disallow-incomplete-defs"])
    else:
        # Gradual adoption mode - less strict
        mypy_cmd.extend(["--ignore-missing-imports", "--follow-imports=silent"])
    
    # Add target path
    mypy_cmd.append(target_path)
    
    try:
        if report_file:
            # Run mypy and save output to report file
            with open(report_file, 'w') as f:
                result = subprocess.run(
                    mypy_cmd,
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                f.write(result.stdout)
                print(f"Mypy report saved to {report_file}")
                return 0 if result.returncode == 0 else 1
        else:
            # Run mypy and display output
            result = subprocess.run(mypy_cmd, check=False)
            return result.returncode
    except Exception as e:
        print(f"Error running mypy: {e}")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run mypy type checking on the Vibez codebase")
    parser.add_argument("--module", help="Specific module to check (e.g., 'app/resources')")
    parser.add_argument("--report", help="Generate a report file with mypy output")
    parser.add_argument("--strict", action="store_true", help="Run in strict mode with all type checking enabled")
    
    args = parser.parse_args()
    
    sys.exit(run_mypy(
        module_path=args.module,
        report_file=args.report,
        check_mode=args.strict
    ))