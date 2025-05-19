from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.logging.models import Log
from app.logging.schemas import LogRead, LogBase, LogCreate
from app.logging.dao import LogDAO
from datetime import datetime, timedelta


class LogService:
    def __init__(self, log_dao: LogDAO):
        self.dao = log_dao

    async def get_logs(
        self,
        limit: int = 50,
        offset: int = 0,
        hours: int = 24,
        log_id: Optional[int] = None,
        status_min: Optional[int] = None,
        status_max: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[LogRead]:
        """Get logs with pagination and filtering"""
        try:
            logs = await self.dao.get_logs(
                limit=limit,
                offset=offset,
                hours=hours,
                log_id=log_id,
                status_min=status_min,
                status_max=status_max,
                search=search,
            )
            # Convert SQLAlchemy models to Pydantic models directly using Pydantic's from_orm
            return [LogRead.model_validate(log) for log in logs]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching logs: {str(e)}")

    async def get_logs_count(
        self,
        hours: int = 24,
        status_min: Optional[int] = None,
        status_max: Optional[int] = None,
        search: Optional[str] = None,
    ) -> int:
        """Get total count of logs matching the filters"""
        try:
            return await self.dao.get_logs_count(
                hours=hours, status_min=status_min, status_max=status_max, search=search
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error counting logs: {str(e)}")

    async def get_status_distribution(self, hours: int = 24) -> Dict[str, Any]:
        """Get distribution of logs by status code with time filter"""
        try:
            distribution = await self.dao.get_status_distribution(hours=hours)

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
            raise HTTPException(
                status_code=500,
                detail=f"Error generating status distribution: {str(e)}",
            )

    async def get_recent_activities(self, days: int = 7) -> Dict[str, Any]:
        """Get recent activities for the dashboard"""
        if days <= 0:
            raise HTTPException(status_code=400, detail="Days must be greater than 0")

        try:
            recent_logs = await self.dao.get_recent_logs(days=days)
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
        # Convert directly from SQLAlchemy model to dictionary using Pydantic
        log_dict = LogRead.model_validate(log).model_dump()

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
