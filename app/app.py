"""FastAPI application entry point for the Vibez application."""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from app.logging.middleware import LoggingMiddleware
from app.core.router import register_routes
from app.core.database import init_db
from typing import Any
from fastapi.exceptions import ResponseValidationError, RequestValidationError
from app.logging.exception_handlers import (
    response_validation_exception_handler,
    request_validation_exception_handler,
    general_exception_handler,
    http_exception_handler,
)


def create_app() -> FastAPI:

    app = FastAPI(docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json")
    init_db()

    # Add request logger middleware
    app.add_middleware(LoggingMiddleware)

    # Register the custom handler -- capture 500 response validation errors (these aren't captured by middleware)
    app.add_exception_handler(ResponseValidationError, response_validation_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, replace with specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Import and include routers
    register_routes(app)

    # Mount the built React assets from the new static directory
    app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

    # Serve the static files from the React build in the new static directory
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str) -> Any:
        # If it's an API request, let it pass through to the API endpoints
        if full_path.startswith("api/"):
            return RedirectResponse(url=f"/api/{full_path[4:]}")

        # For all other routes, serve the React app's index.html from the new static directory
        with open("static/index.html", "r", encoding="utf-8") as f:
            html_content = f.read()

        return HTMLResponse(content=html_content)

    return app
