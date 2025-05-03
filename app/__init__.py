from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlmodel import Session, select
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
    app = FastAPI()

    # # Add request logger middleware
    app.add_middleware(LoggingMiddleware)

    # Mount static files
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    # Setup templates
    templates = Jinja2Templates(directory="app/templates")

    # Root route - redirect to home page
    @app.get("/")
    async def root(request: Request):
        return templates.TemplateResponse("home.html", {"request": request})

    # Import and include routers
    from app.resources.router import router as resource_router
    from app.reporting.router import router as report_router
    from app.logging.router import router as log_router
    from app.database import get_session
    from app.resources.models import User, Employee, Subscriber
    from app.logging.models import Log

    # Only include API routes, not page routes
    app.include_router(resource_router)
    app.include_router(report_router)
    app.include_router(log_router)

    # Combined resources route with dynamic model-based tables
    @app.get("/resources", response_class=HTMLResponse)
    async def resources_page(request: Request, session: Session = Depends(get_session)):
        # Fetch all users, employees and subscribers
        users = session.exec(select(User)).all()
        employees = session.exec(select(Employee)).all()
        subscribers = session.exec(select(Subscriber)).all()

        # Convert SQLModel objects to dictionaries for JSON serialization
        # Handle both older and newer Pydantic versions (dict vs model_dump)
        users_data = []
        employees_data = []
        subscribers_data = []

        for user in users:
            try:
                users_data.append(user.dict())
            except AttributeError:
                users_data.append(user.model_dump())

        for employee in employees:
            try:
                employees_data.append(employee.dict())
            except AttributeError:
                employees_data.append(employee.model_dump())

        for subscriber in subscribers:
            try:
                subscriber_dict = subscriber.dict()
            except AttributeError:
                subscriber_dict = subscriber.model_dump()
            # Convert to JSON and back to handle datetime serialization
            subscriber_json = json.dumps(subscriber_dict, cls=DateTimeEncoder)
            subscribers_data.append(json.loads(subscriber_json))

        # Get initial resource type from URL param, if provided
        resource_type = request.query_params.get("type", "users")
        # Validate resource type
        if resource_type not in ["users", "employees", "subscribers"]:
            resource_type = "users"

        return templates.TemplateResponse(
            "resources.html",
            {
                "request": request,
                "users": users_data,
                "employees": employees_data,
                "subscribers": subscribers_data,
                "initial_resource_type": resource_type,
            },
        )

    # Reporting page route
    @app.get("/reporting", response_class=HTMLResponse)
    async def reporting_page(request: Request):
        return templates.TemplateResponse("reporting.html", {"request": request})

    # Documentation page route
    @app.get("/documentation", response_class=HTMLResponse)
    async def documentation_page(request: Request):
        return templates.TemplateResponse("documentation.html", {"request": request})

    # Logs page route
    @app.get("/logs", response_class=HTMLResponse)
    async def logs_page(request: Request):
        return templates.TemplateResponse("logs.html", {"request": request})

    return app, templates
