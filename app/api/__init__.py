from app.api.user_router import router as user_router
from app.api.employee_router import router as employee_router
from app.api.report_router import router as report_router

__all__ = ['user_router', 'employee_router', 'report_router']