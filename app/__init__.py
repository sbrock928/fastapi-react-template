from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlmodel import Session, select
import os

def create_app():
    app = FastAPI()
    
    # Mount static files
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    
    # Setup templates
    templates = Jinja2Templates(directory="app/templates")
    
    # Root route - redirect to home page
    @app.get("/")
    async def root(request: Request):
        return templates.TemplateResponse("home.html", {"request": request})
    
    # Import and include routers
    from app.api.user_router import router as user_router
    from app.api.employee_router import router as employee_router
    from app.api.report_router import router as report_router
    from app.database import get_session
    from app.models.base import User, Employee
    
    # Only include API routes, not page routes
    app.include_router(user_router)
    app.include_router(employee_router)
    app.include_router(report_router)
    
    # Combined resources route with dynamic model-based tables
    @app.get("/resources", response_class=HTMLResponse)
    async def resources_page(request: Request, session: Session = Depends(get_session)):
        # Fetch all users and employees
        users = session.exec(select(User)).all()
        employees = session.exec(select(Employee)).all()
        
        # Convert SQLModel objects to dictionaries for JSON serialization
        # Handle both older and newer Pydantic versions (dict vs model_dump)
        users_data = []
        employees_data = []
        
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
        
        return templates.TemplateResponse(
            "resources.html",
            {
                "request": request, 
                "users": users_data, 
                "employees": employees_data
            }
        )
    
    # Reporting page route
    @app.get("/reporting", response_class=HTMLResponse)
    async def reporting_page(request: Request):
        return templates.TemplateResponse("reporting.html", {"request": request})
    
    return app, templates