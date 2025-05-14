#!/usr/bin/env python3
import uvicorn
from app.app import create_app
import os
import sys

# Get the application directory - differs between normal execution and PyInstaller
if getattr(sys, "frozen", False):
    # If the application is run as a bundle (PyInstaller executable)
    application_path = os.path.dirname(sys.executable)
    # Change working directory to executable location
    os.chdir(application_path)
else:
    # If running as a script
    application_path = os.path.dirname(os.path.abspath(__file__))

# Check if running in development mode
is_dev_mode = os.getenv("VIBEZ_DEV_MODE", "false").lower() == "true"
if is_dev_mode:
    print("Running in DEVELOPMENT mode with Jinja2 templates")
else:
    print("Running in PRODUCTION mode with React frontend")

# Create the FastAPI app
app = create_app()



if __name__ == "__main__":
    # In packaged mode, we don't want auto-reload and we need to be careful about host binding
    debug_mode = not getattr(sys, "frozen", False)

    # When packaged, don't use reload and use a more restrictive host
    host = "127.0.0.1" if getattr(sys, "frozen", False) else "0.0.0.0"
    reload_enabled = False if getattr(sys, "frozen", False) else True

    print(f"Starting Vibez application on {host}:8000")
    print(f"Debug mode: {debug_mode}")
    print(f"Application path: {application_path}")

    uvicorn.run("main:app", host=host, port=8000, reload=reload_enabled)
