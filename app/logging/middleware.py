"""Middleware for logging HTTP requests and responses with detailed information."""

import time
import json
import os
import getpass
import platform
import socket
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable, AsyncIterator

from datetime import datetime
from starlette.background import BackgroundTask
from app.logging.models import Log
from app.core.database import SessionLocal

# Import APPLICATION_ID from environment variables
from dotenv import load_dotenv

load_dotenv()

APPLICATION_ID = os.environ.get("APPLICATION_ID", "Unknown")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs HTTP requests and responses to the database."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        # Get the current username when middleware is initialized
        try:
            # Try multiple methods to get the username for cross-platform support
            self.username = (
                os.environ.get("USER")
                or os.environ.get("USERNAME")
                or getpass.getuser()
                or "unknown_user"
            )
        except Exception:  # pylint: disable=broad-except
            self.username = "unknown_user"

        # Get the computer hostname
        try:
            self.hostname = socket.gethostname() or platform.node() or "unknown_host"
        except Exception:  # pylint: disable=broad-except
            self.hostname = "unknown_host"

        # Store the application ID from environment
        self.application_id = APPLICATION_ID

        print(
            f"Logging middleware initialized with username: {self.username} on host: "
            f"{self.hostname}, App ID: {self.application_id}"
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Define paths that should be excluded from logging
        excluded_paths = ["/api/logs", "/static", "/logs"]

        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in excluded_paths):
            return await call_next(request)

        # --- Start timer ---
        start_time = time.time()

        # --- Read request body ---
        body_bytes = await request.body()
        request_body = body_bytes.decode("utf-8", errors="ignore")

        # Store request body in request state for exception handlers
        request.state.body = request_body

        # Reconstruct stream
        async def receive() -> dict:
            return {"type": "http.request", "body": body_bytes}

        request = Request(request.scope, receive=receive)

        # Make sure the body is still available in the new request object
        request.state.body = request_body

        # --- Proceed with original response ---
        response = await call_next(request)

        # --- End timer ---
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000

        # Capture response information
        status_code = response.status_code
        headers = response.headers
        content_type = headers.get("content-type", "")
        is_html = "text/html" in content_type

        # Create a new response with captured body
        response_body = b""

        # Handle different response types to capture body
        if isinstance(response, Response) and hasattr(response, "body"):
            # Standard Response with body attribute
            response_body = response.body
            new_response = response
        elif hasattr(response, "body_iterator"):
            # It's a StreamingResponse
            # We need to consume the iterator to get the full body
            original_iterator = response.body_iterator

            # Create a buffer to store the chunks
            chunks = []

            # Define a new iterator that collects chunks
            async def buffer_iterator() -> AsyncIterator[bytes]:
                nonlocal response_body
                async for chunk in original_iterator:
                    chunks.append(chunk)
                    yield chunk

                # Combine all chunks into a single response body
                response_body = b"".join(chunks)

            # Replace the body_iterator with our buffering iterator
            response.body_iterator = buffer_iterator()
            new_response = response
        else:
            # Unknown response type - use as is
            new_response = response

        # --- Log to DB (in background) ---
        def log_to_db() -> None:
            with SessionLocal() as session:
                # Determine the response body to log
                body_to_log = ""
                if response_body:
                    body_to_log = response_body.decode("utf-8", errors="ignore")
                elif is_html:
                    body_to_log = "[HTML content not logged for successful response]"
                else:
                    body_to_log = "[Response body not available]"

                # Create a SQLAlchemy Log object
                log = Log(
                    timestamp=datetime.now(),
                    method=request.method,
                    path=str(request.url.path),
                    status_code=status_code,
                    client_ip=request.client.host if request.client else None,
                    request_headers=json.dumps(dict(request.headers)),
                    request_body=request_body,
                    response_body=body_to_log,
                    processing_time=duration_ms,  # type: ignore
                    user_agent=request.headers.get("user-agent"),
                    username=self.username,
                    hostname=self.hostname,
                    application_id=self.application_id,
                )
                session.add(log)
                session.commit()

        # Attach as background task
        new_response.background = getattr(new_response, "background", None) or BackgroundTask(
            log_to_db
        )

        return new_response
