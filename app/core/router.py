"""
Module for registering routes in the FastAPI application.
"""

from fastapi import FastAPI

from app.resources.router import router as resource_router
from app.reporting.router import router as report_router
from app.logging.router import router as log_router
from app.documentation.router import router as documentation_router


def register_routes(app: FastAPI) -> None:
    """
    Registers all the routes for the FastAPI application.

    Args:
        app (FastAPI): The FastAPI application instance.
    """
    # Include API routes
    app.include_router(resource_router, prefix="/api")
    app.include_router(report_router, prefix="/api")
    app.include_router(log_router, prefix="/api")
    app.include_router(documentation_router, prefix="/api")
