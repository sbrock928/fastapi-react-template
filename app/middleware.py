import time
import json
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from sqlmodel import Session
from app.database import engine
from app.models.base import Log
from starlette.responses import StreamingResponse

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
        
        # Create a copy of the request body if needed
        request_body = None
        if method in ["POST", "PUT", "PATCH"]:
            try:
                # Get a copy of the body but don't consume it
                body_bytes = await request.body()
                # Create a new Request with the same body to allow FastAPI to read it again
                request._receive = receive_with_body(body_bytes)
                
                # Try to parse as JSON, or just store as string if that fails
                try:
                    body_str = body_bytes.decode()
                    request_body = body_str
                except:
                    request_body = str(body_bytes)
            except:
                request_body = "Could not capture request body"
        
        # Process the request and capture the response
        original_response = await call_next(request)
        
        # Skip logging for static files and swagger docs
        if path.startswith(("/static/", "/docs", "/openapi.json", "/redoc")):
            return original_response
        
        # Record end time
        end_time = time.time()
        processing_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Capture response info
        status_code = original_response.status_code
        
        # Try to capture response body for JSON responses
        response_body = None
        
        # Only attempt to capture response body for certain content types
        content_type = original_response.headers.get("content-type", "")
        if "application/json" in content_type:
            # Create a copy of the response to avoid interfering with it
            response_body = await capture_response_body(original_response)
        
        # Store log in the database asynchronously to avoid blocking
        try:
            with Session(engine) as session:
                log_entry = Log(
                    method=method,
                    path=path,
                    status_code=status_code,
                    client_ip=client_ip,
                    request_headers=headers_str,
                    request_body=request_body,
                    response_body=response_body,  # Now storing response body
                    processing_time=processing_time,
                    user_agent=user_agent
                )
                session.add(log_entry)
                session.commit()
        except Exception as e:
            # Log error but don't interrupt the response
            print(f"Error logging request: {str(e)}")
        
        return original_response

# Helper function to create a new _receive function that returns the saved body
def receive_with_body(body):
    async def new_receive():
        return {"type": "http.request", "body": body, "more_body": False}
    return new_receive

# Helper function to capture response body without disrupting the response
async def capture_response_body(response):
    try:
        # Handle different response types
        if hasattr(response, "body") and response.body:
            # For regular responses with a body attribute
            body_bytes = response.body
            try:
                return body_bytes.decode('utf-8')
            except UnicodeDecodeError:
                return str(body_bytes)
        elif isinstance(response, StreamingResponse):
            # Streaming responses are more complex - we may need to skip them
            return "StreamingResponse (body not captured)"
        else:
            return None
    except Exception as e:
        print(f"Error capturing response body: {str(e)}")
        return None