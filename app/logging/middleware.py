import time
import json
import os
import getpass
import platform
import socket
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable, Awaitable, List, Dict, Any

from datetime import datetime
from starlette.background import BackgroundTask
from sqlmodel import Session
from app.logging.models import Log  # Adjust import as needed
from app.database import SessionLocal  # Your session generator
import time
import os

# Import APPLICATION_ID from environment variables
from dotenv import load_dotenv

load_dotenv()

APPLICATION_ID = os.environ.get("APPLICATION_ID", "Unknown")


class LoggingMiddleware(BaseHTTPMiddleware):
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
        except Exception:
            self.username = "unknown_user"

        # Get the computer hostname
        try:
            self.hostname = socket.gethostname() or platform.node() or "unknown_host"
        except Exception:
            self.hostname = "unknown_host"

        # Store the application ID from environment
        self.application_id = APPLICATION_ID

        print(
            f"Logging middleware initialized with username: {self.username} on host: {self.hostname}, App ID: {self.application_id}"
        )

    async def dispatch(self, request: Request, call_next: Callable):
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

        # Reconstruct stream
        async def receive() -> dict:
            return {"type": "http.request", "body": body_bytes}

        request = Request(request.scope, receive=receive)

        # --- Proceed with response ---
        response = await call_next(request)

        # Capture response body
        response_body = b""
        if isinstance(response, Response):
            async for chunk in response.body_iterator:
                response_body += chunk
            new_response = Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
        else:
            original_body_iterator = response.body_iterator

            async def buffered_body():
                nonlocal response_body
                async for chunk in original_body_iterator:
                    response_body += chunk
                    yield chunk

            response.body_iterator = buffered_body()
            new_response = response

        # --- End timer ---
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000

        # Determine if we should log the response body
        # Only log HTML response bodies for error responses (status >= 400)
        should_log_body = True
        is_html = False
        content_type = new_response.headers.get("content-type", "")
        if "text/html" in content_type:
            is_html = True
            if new_response.status_code < 400:  # Not an error response
                should_log_body = False

        # --- Log to DB (in background) ---
        def log_to_db():
            with SessionLocal() as session:
                # Determine the response body to log
                body_to_log = ""
                if should_log_body:
                    body_to_log = response_body.decode("utf-8", errors="ignore")
                elif is_html:
                    body_to_log = "[HTML content not logged for successful response]"
                else:
                    body_to_log = response_body.decode("utf-8", errors="ignore")

                log = Log(
                    timestamp=datetime.now(),
                    method=request.method,
                    path=str(request.url.path),
                    status_code=new_response.status_code,
                    client_ip=request.client.host if request.client else None,
                    request_headers=json.dumps(dict(request.headers)),
                    request_body=request_body,
                    response_body=body_to_log,
                    processing_time=duration_ms,
                    user_agent=request.headers.get("user-agent"),
                    username=self.username,  # Changed from server_username to username
                    hostname=self.hostname,  # Added hostname
                    application_id=self.application_id,  # Added application_id
                )
                session.add(log)
                session.commit()

        # Attach as background task
        new_response.background = new_response.background or BackgroundTask(log_to_db)

        return new_response
