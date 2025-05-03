#!/usr/bin/env python3
"""
Build script for creating a single executable file for the Vibez application.
This script uses PyInstaller to package the application and all its dependencies.
"""

import PyInstaller.__main__
import os
import shutil
import sys


def build_executable():
    # Define the name of the executable
    app_name = "Vibez"

    # Clean previous build artifacts if they exist
    for dir_name in ["build", "dist"]:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)

    if os.path.exists(f"{app_name}.spec"):
        os.remove(f"{app_name}.spec")

    # Define resource files that need to be included
    datas = [
        # Include templates directory
        ("app/templates", "app/templates"),
        # Include static directory
        ("app/static", "app/static"),
        # Include the database if it exists (for initial deployment)
        ("sql_app.db", ".") if os.path.exists("sql_app.db") else None,
    ]

    # Filter out None entries
    datas = [d for d in datas if d is not None]

    # Convert datas to PyInstaller format
    datas_args = []
    for src, dst in datas:
        datas_args.extend(["--add-data", f"{src}{os.pathsep}{dst}"])

    # Define hidden imports that might be needed
    hidden_imports = [
        "uvicorn.logging",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "email_validator",
    ]

    hidden_imports_args = []
    for imp in hidden_imports:
        hidden_imports_args.extend(["--hidden-import", imp])

    # Build the command line for PyInstaller
    pyinstaller_args = [
        "main.py",
        "--name",
        app_name,
        "--onefile",
        "--clean",
        "--noconfirm",
        # Windows specific - use this if building on Windows
        # '--icon', 'app/static/favicon.ico',
    ]

    # Add all the arguments together
    pyinstaller_args.extend(datas_args)
    pyinstaller_args.extend(hidden_imports_args)

    # Run PyInstaller
    print(f"Building {app_name} executable...")
    PyInstaller.__main__.run(pyinstaller_args)

    print(f"\nBuild completed. The executable is located in the 'dist' directory.")
    print(f"Run it with: ./dist/{app_name}")


if __name__ == "__main__":
    build_executable()
