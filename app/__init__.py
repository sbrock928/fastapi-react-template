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
    from app.database import get_session
    from app.models.base import User, Employee
    
    # Only include API routes, not page routes
    app.include_router(user_router, prefix="/users")
    app.include_router(employee_router, prefix="/employees")
    
    # Combined resources route
    @app.get("/resources", response_class=HTMLResponse)
    async def resources_page(request: Request, session: Session = Depends(get_session)):
        users = session.exec(select(User)).all()
        employees = session.exec(select(Employee)).all()
        return templates.TemplateResponse(
            "resources.html",
            {"request": request, "users": users, "employees": employees}
        )
    
    return app, templates