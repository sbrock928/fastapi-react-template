from fastapi import FastAPI, Request, Depends, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select
import os
from datetime import datetime
import json
from app.logging.middleware import LoggingMiddleware  # Import the middleware


# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def create_app():

    app = FastAPI(
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )

    # Add request logger middleware
    app.add_middleware(LoggingMiddleware)
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, replace with specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Import and include routers
    from app.resources.router import router as resource_router
    from app.reporting.router import router as report_router
    from app.logging.router import router as log_router
    from app.user_guide.router import router as user_guide_router
    from app.database import get_session
    from app.resources.models import User, Employee, Subscriber
    from app.logging.models import Log

    # Include API routes
    app.include_router(resource_router, prefix="/api")
    app.include_router(report_router, prefix="/api")
    app.include_router(log_router, prefix="/api")
    app.include_router(user_guide_router)

    # Mount the built React assets from the new static directory
    app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

    # Serve the static files from the React build in the new static directory
    @app.get("/{full_path:path}")
    async def serve_react_app(request: Request, full_path: str):
        # If it's an API request, let it pass through to the API endpoints
        if full_path.startswith("api/"):
            return RedirectResponse(url=f"/api/{full_path[4:]}")

        # For all other routes, serve the React app's index.html from the new static directory
        with open("static/index.html", "r") as f:
            html_content = f.read()

        return HTMLResponse(content=html_content)

    return app, None
