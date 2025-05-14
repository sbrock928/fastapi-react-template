from sqlalchemy.orm import Session
from sqlalchemy import select, text, func, or_, cast, String
from typing import List, Dict, Any, Optional
from app.logging.models import Log
from datetime import datetime, timedelta


class LogDAO:
    def __init__(self, session: Session):
        self.session = session

    async def get_logs(
        self,
        limit: int = 50,
        offset: int = 0,
        hours: int = 24,
        log_id: Optional[int] = None,
        status_min: Optional[int] = None,
        status_max: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[Log]:
        """Get logs with pagination and filtering"""
        if log_id:
            query = select(Log).where(Log.id == log_id)
        else:
            # Calculate the time threshold based on the hours parameter
            time_threshold = datetime.now() - timedelta(hours=hours)

            # Start with time filter
            query = select(Log).where(Log.timestamp >= time_threshold)

            # Add status code range filter if provided
            if status_min is not None:
                query = query.where(Log.status_code >= status_min)
            if status_max is not None:
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
                        cast(Log.status_code, String).ilike(search_term),
                        cast(Log.application_id, String).ilike(search_term),
                    )
                )

            # Add sorting and pagination
            query = query.order_by(Log.timestamp.desc()).offset(offset).limit(limit)

        result = self.session.execute(query).scalars().all()
        return result

    async def get_logs_count(
        self,
        hours: int = 24,
        status_min: Optional[int] = None,
        status_max: Optional[int] = None,
        search: Optional[str] = None,
    ) -> int:
        """Get total count of logs matching the filters"""
        # Calculate the time threshold based on the hours parameter
        time_threshold = datetime.now() - timedelta(hours=hours)

        # Start with time filter
        query = select(func.count(Log.id)).where(Log.timestamp >= time_threshold)

        # Add status code range filter if provided
        if status_min is not None:
            query = query.where(Log.status_code >= status_min)
        if status_max is not None:
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
                    cast(Log.status_code, String).ilike(search_term),
                    cast(Log.application_id, String).ilike(search_term),
                )
            )

        result = self.session.execute(query).scalar_one()
        return result

    async def get_status_distribution(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get distribution of logs by status code with time filter"""
        time_threshold = datetime.now() - timedelta(hours=hours)

        query = """
        SELECT status_code, COUNT(*) as count
        FROM log
        WHERE timestamp >= :time_threshold
        GROUP BY status_code
        ORDER BY status_code
        """

        result = self.session.execute(
            text(query).bindparams(time_threshold=time_threshold)
        ).all()

        return [{"status_code": row[0], "count": row[1]} for row in result]

    async def get_recent_logs(self, days: int = 7) -> List[Log]:
        """Get recent logs limited by days"""
        time_threshold = datetime.now() - timedelta(days=days)
        query = (
            select(Log)
            .where(Log.timestamp >= time_threshold)
            .order_by(Log.timestamp.desc())
            .limit(100)
        )

        result = self.session.execute(query).scalars().all()
        return result
