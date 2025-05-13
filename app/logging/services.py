from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from sqlmodel import Session, select
from app.logging.models import Log
from app.logging.dao import LogDAO
from datetime import datetime, timedelta
from sqlalchemy import or_, String

class LogService:
    def __init__(self, session: Session):
        self.session = session
        self.log_dao = LogDAO(session)

    async def get_logs(
        self, 
        limit: int = 50, 
        offset: int = 0, 
        hours: int = 24, 
        log_id: Optional[int] = None,
        status_min: Optional[int] = None,
        status_max: Optional[int] = None,
        search: Optional[str] = None
    ) -> List[Log]:
        """Get logs with pagination and filtering"""
        # Start with a base query
        query = select(Log)
        
        # Apply filters
        time_limit = datetime.now() - timedelta(hours=hours)
        query = query.where(Log.timestamp >= time_limit)
        
        if log_id:
            query = query.where(Log.id == log_id)
        
        if status_min:
            query = query.where(Log.status_code >= status_min)
        
        if status_max:
            query = query.where(Log.status_code <= status_max)
            
        # Apply search filter if provided
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Log.path.ilike(search_term),
                    Log.method.ilike(search_term),
                    Log.client_ip.ilike(search_term),
                    Log.username.ilike(search_term),
                    Log.hostname.ilike(search_term),
                    # Convert status_code to string for searching
                    Log.status_code.cast(String).ilike(search_term),
                    Log.application_id.cast(String).ilike(search_term),
                )
            )
        
        # Apply ordering and pagination
        query = query.order_by(Log.timestamp.desc())
        query = query.offset(offset).limit(limit)
        
        # Execute query
        result = self.session.exec(query).all()
        return result

    async def get_logs_count(
        self,
        hours: int = 24,
        status_min: Optional[int] = None,
        status_max: Optional[int] = None,
        search: Optional[str] = None
    ) -> int:
        """Get total count of logs matching the filters"""
        # Start with a base query
        from sqlalchemy import func
        query = select(func.count()).select_from(Log)
        
        # Apply filters
        time_limit = datetime.now() - timedelta(hours=hours)
        query = query.where(Log.timestamp >= time_limit)
        
        if status_min:
            query = query.where(Log.status_code >= status_min)
        
        if status_max:
            query = query.where(Log.status_code <= status_max)
            
        # Apply search filter if provided
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Log.path.ilike(search_term),
                    Log.method.ilike(search_term),
                    Log.client_ip.ilike(search_term),
                    Log.username.ilike(search_term),
                    Log.hostname.ilike(search_term),
                    # Convert status_code to string for searching
                    Log.status_code.cast(String).ilike(search_term),
                    Log.application_id.cast(String).ilike(search_term),
                )
            )
        
        # Execute query
        count = self.session.exec(query).one()
        return count

    async def get_status_distribution(self, hours: int = 24) -> Dict[str, Any]:
        """Get distribution of logs by status code with time filter"""
        try:
            distribution = await self.log_dao.get_status_distribution(hours=hours)
            
            # Add status descriptions
            for item in distribution:
                status_code = item["status_code"]
                if 200 <= status_code < 300:
                    item["description"] = "Success"
                elif 300 <= status_code < 400:
                    item["description"] = "Redirection"
                elif 400 <= status_code < 500:
                    item["description"] = "Client Error"
                elif 500 <= status_code < 600:
                    item["description"] = "Server Error"
                else:
                    item["description"] = "Unknown"

            return {
                "status_distribution": distribution,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            import traceback
            print(f"Error generating status distribution: {str(e)}")
            print(traceback.format_exc())
            raise HTTPException(
                status_code=500,
                detail=f"Error generating status distribution: {str(e)}",
            )

    async def get_recent_activities(self, days: int = 7) -> Dict[str, Any]:
        """Get recent activities for the dashboard"""
        if days <= 0:
            raise HTTPException(status_code=400, detail="Days must be greater than 0")

        try:
            recent_logs = await self.log_dao.get_recent_logs(days=days)
            return {
                "recent_logs": [self._format_log(log) for log in recent_logs],
                "days": days,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error generating recent activities: {str(e)}"
            )

    def _format_log(self, log: Log) -> Dict[str, Any]:
        """Format a log object for API response"""
        # Handle both older and newer pydantic versions
        try:
            log_dict = log.dict()
        except AttributeError:
            log_dict = log.model_dump()

        # Add status category
        status_code = log_dict.get("status_code", 0)
        if 200 <= status_code < 300:
            log_dict["status_category"] = "Success"
        elif 300 <= status_code < 400:
            log_dict["status_category"] = "Redirection"
        elif 400 <= status_code < 500:
            log_dict["status_category"] = "Client Error"
        elif 500 <= status_code < 600:
            log_dict["status_category"] = "Server Error"
        else:
            log_dict["status_category"] = "Unknown"

        return log_dict
