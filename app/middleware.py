import time
import json
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from sqlmodel import Session
from app.database import engine
from app.models.base import Log

class RequestLoggerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        # Start timer
        start_time = time.time()
        
        # Collect request information
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # Get request headers
        headers = dict(request.headers.items())
        headers_str = json.dumps(headers)
        
        # Try to get request body
        request_body = None
        if method in ["POST", "PUT", "PATCH"]:
            try:
                # We need to use a copy because once the body is read, it can't be read again
                body_bytes = await request.body()
                request.scope["_body"] = body_bytes  # Save for later use by request handlers
                
                # Try to parse as JSON, or just store as string if that fails
                try:
                    body_str = body_bytes.decode()
                    request_body = body_str
                except:
                    request_body = str(body_bytes)
            except:
                request_body = "Could not capture request body"
        
        # Process the request
        response = await call_next(request)
        
        # Skip logging for static files and swagger docs
        if path.startswith(("/static/", "/docs", "/openapi.json", "/redoc")):
            return response
        
        # Record end time
        end_time = time.time()
        processing_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Capture response info
        status_code = response.status_code
        
        # We can't easily capture the response body without interfering with streaming responses
        # For simplicity, we'll just capture the status code for now
        
        # Store log in the database
        with Session(engine) as session:
            log_entry = Log(
                method=method,
                path=path,
                status_code=status_code,
                client_ip=client_ip,
                request_headers=headers_str,
                request_body=request_body,
                response_body=None,  # Not capturing response body for simplicity
                processing_time=processing_time,
                user_agent=user_agent
            )
            session.add(log_entry)
            session.commit()
        
        return response