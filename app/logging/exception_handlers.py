# app/logging/exception_handlers.py

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import ResponseValidationError, RequestValidationError
from app.logging.models import Log
from app.core.database import SessionLocal
from datetime import datetime
import json
import os
import socket
import getpass
import platform
import traceback
from dotenv import load_dotenv

load_dotenv()

APPLICATION_ID = os.environ.get("APPLICATION_ID", "Unknown")
USERNAME = os.environ.get("USER") or os.environ.get("USERNAME") or getpass.getuser() or "unknown_user"
HOSTNAME = socket.gethostname() or platform.node() or "unknown_host"

def safe_json_dumps(obj):
    def default(o):
        if isinstance(o, (datetime, Exception)):
            return str(o)
        elif hasattr(o, '__dict__'):
            return str(o)
        return str(o)
    return json.dumps(obj, indent=2, default=default)

def get_request_body_safely(request: Request) -> str:
    """Safely get request body, handling cases where it's already been consumed"""
    try:
        # Try to get the body from the request scope if middleware stored it
        if hasattr(request.state, 'body'):
            return request.state.body
        
        # If that's not available, try to read from the request
        # This will only work if the body hasn't been consumed yet
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context but can't await here
            return "Request body already consumed"
        else:
            # Fallback - this probably won't work in most cases
            return "Unable to read request body"
    except Exception:
        return "Unable to read request body"

async def general_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions and log them to database"""
    error_traceback = traceback.format_exc()
    
    with SessionLocal() as session:
        try:
            # Get request body safely without trying to await in sync context
            request_body = get_request_body_safely(request)
            
            log = Log(
                timestamp=datetime.now(),
                method=request.method,
                path=str(request.url.path),
                status_code=500,
                client_ip=request.client.host if request.client else None,
                request_headers=json.dumps(dict(request.headers)),
                request_body=request_body,
                response_body=safe_json_dumps({
                    "error": str(exc),
                    "type": type(exc).__name__,
                    "traceback": error_traceback
                }),
                processing_time=None,
                user_agent=request.headers.get("user-agent"),
                username=USERNAME,
                hostname=HOSTNAME,
                application_id=APPLICATION_ID,
            )
            session.add(log)
            session.commit()
        except Exception as log_error:
            print(f"Error logging exception: {log_error}")

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

async def response_validation_exception_handler(request: Request, exc: ResponseValidationError):
    with SessionLocal() as session:
        log = Log(
            timestamp=datetime.now(),
            method=request.method,
            path=str(request.url.path),
            status_code=500,
            client_ip=request.client.host if request.client else None,
            request_headers=json.dumps(dict(request.headers)),
            request_body=get_request_body_safely(request),
            response_body=safe_json_dumps(exc.errors()),
            processing_time=None,
            user_agent=request.headers.get("user-agent"),
            username=USERNAME,
            hostname=HOSTNAME,
            application_id=APPLICATION_ID,
        )
        session.add(log)
        session.commit()

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error: Response validation failed."},
    )

async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    with SessionLocal() as session:
        try:
            # Get request body safely
            request_body = get_request_body_safely(request)
            
            log = Log(
                timestamp=datetime.now(),
                method=request.method,
                path=str(request.url.path),
                status_code=422,
                client_ip=request.client.host if request.client else None,
                request_headers=json.dumps(dict(request.headers)),
                request_body=request_body,
                response_body=safe_json_dumps(exc.errors()),
                processing_time=None,
                user_agent=request.headers.get("user-agent"),
                username=USERNAME,
                hostname=HOSTNAME,
                application_id=APPLICATION_ID,
            )
            session.add(log)
            session.commit()
        except Exception as log_error:
            print(f"Error logging validation exception: {log_error}")

    # Convert errors to a safe format for JSON response
    def convert_error(error):
        if isinstance(error, dict):
            return {k: convert_error(v) for k, v in error.items()}
        elif isinstance(error, list):
            return [convert_error(item) for item in error]
        else:
            return str(error)

    safe_errors = convert_error(exc.errors())

    return JSONResponse(
        status_code=422,
        content={"detail": safe_errors},
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions and log 4xx/5xx errors"""
    # Log 4xx and 5xx errors
    if exc.status_code >= 400:
        with SessionLocal() as session:
            try:
                # Get request body safely
                request_body = get_request_body_safely(request)
                
                log = Log(
                    timestamp=datetime.now(),
                    method=request.method,
                    path=str(request.url.path),
                    status_code=exc.status_code,
                    client_ip=request.client.host if request.client else None,
                    request_headers=json.dumps(dict(request.headers)),
                    request_body=request_body,
                    response_body=safe_json_dumps({
                        "detail": exc.detail,
                        "headers": getattr(exc, 'headers', None)
                    }),
                    processing_time=None,
                    user_agent=request.headers.get("user-agent"),
                    username=USERNAME,
                    hostname=HOSTNAME,
                    application_id=APPLICATION_ID,
                )
                session.add(log)
                session.commit()
            except Exception as log_error:
                print(f"Error logging HTTP exception: {log_error}")

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, 'headers', None)
    )
