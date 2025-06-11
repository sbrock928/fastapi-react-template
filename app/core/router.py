# app/core/router.py
"""
Updated module for registering routes in the FastAPI application.
"""

from fastapi import FastAPI

from app.reporting.router import router as report_router
from app.logging.router import router as log_router
from app.documentation.router import router as documentation_router
from app.calculations.router import router as calculation_router
from app.datawarehouse.router import router as datawarehouse_router  # NEW


def register_routes(app: FastAPI) -> None:
    """
    Registers all the routes for the FastAPI application.

    Args:
        app (FastAPI): The FastAPI application instance.
    """
    # Include API routes
    app.include_router(report_router, prefix="/api")
    app.include_router(log_router, prefix="/api")
    app.include_router(documentation_router, prefix="/api")
    app.include_router(calculation_router, prefix="/api")
    app.include_router(datawarehouse_router, prefix="/api")  # NEW