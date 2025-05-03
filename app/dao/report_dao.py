from sqlmodel import Session, select, func
from typing import List, Dict, Any
from app.models.base import User, Employee, Log
from datetime import datetime, timedelta

class ReportDAO:
    def __init__(self, session: Session):
        self.session = session
    
    async def get_user_count(self) -> int:
        """Get total count of users"""
        return self.session.exec(select(func.count()).select_from(User)).one()
    
    async def get_employee_count(self) -> int:
        """Get total count of employees"""
        return self.session.exec(select(func.count()).select_from(Employee)).one()
    
    async def get_log_count(self) -> int:
        """Get total count of logs"""
        return self.session.exec(select(func.count()).select_from(Log)).one()
    
    async def get_recent_logs(self, days: int = 7, limit: int = 10) -> List[Log]:
        """Get recent logs from the past X days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        query = select(Log).where(Log.timestamp >= cutoff_date).order_by(Log.timestamp.desc()).limit(limit)
        return self.session.exec(query).all()
    
    async def get_status_distribution(self) -> List[Dict[str, Any]]:
        """Get distribution of logs by status code"""
        query = select(Log.status_code, func.count(Log.id).label("count")).group_by(Log.status_code)
        results = self.session.exec(query).all()
        return [{"status_code": status_code, "count": count} for status_code, count in results]