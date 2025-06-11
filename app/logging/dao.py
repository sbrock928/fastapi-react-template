# app/logging/dao.py
"""Refactored Data Access Objects for the logging module using BaseDAO."""

from sqlalchemy.orm import Session
from sqlalchemy import select, text, func, or_, cast, String, desc
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.core.base_dao import BaseDAO
from app.logging.models import Log


class LogDAO(BaseDAO[Log]):
    """Refactored DAO for Log operations using BaseDAO."""

    def __init__(self, db_session: Session):
        super().__init__(Log, db_session)

    # ===== SPECIALIZED LOGGING METHODS =====
    # These methods are domain-specific and can't be generalized in BaseDAO

    def get_logs_with_filters(
        self,
        limit: int = 50,
        offset: int = 0,
        hours: int = 24,
        log_id: Optional[int] = None,
        status_min: Optional[int] = None,
        status_max: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[Log]:
        """Get logs with advanced filtering - specialized method."""
        if log_id:
            # Use base DAO method for simple ID lookup
            log = self.get_by_id(log_id)
            return [log] if log else []

        # Calculate the time threshold based on the hours parameter
        time_threshold = datetime.now() - timedelta(hours=hours)

        # Start with time filter
        query = select(self.model).where(self.model.timestamp >= time_threshold)

        # Add status code range filter if provided
        if status_min is not None:
            query = query.where(self.model.status_code >= status_min)
        if status_max is not None:
            query = query.where(self.model.status_code <= status_max)

        # Apply search filter if provided
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    self.model.path.ilike(search_term),
                    self.model.method.ilike(search_term),
                    self.model.client_ip.ilike(search_term),
                    self.model.username.ilike(search_term),
                    self.model.hostname.ilike(search_term),
                    # Convert status_code to string for searching
                    cast(self.model.status_code, String).ilike(search_term),
                    cast(self.model.application_id, String).ilike(search_term),
                )
            )

        # Add sorting and pagination
        query = query.order_by(self.model.timestamp.desc()).offset(offset).limit(limit)

        result = self.db.execute(query).scalars().all()
        return list(result)

    def count_logs_with_filters(
        self,
        hours: int = 24,
        status_min: Optional[int] = None,
        status_max: Optional[int] = None,
        search: Optional[str] = None,
    ) -> int:
        """Get total count of logs matching the filters - specialized method."""
        # Calculate the time threshold based on the hours parameter
        time_threshold = datetime.now() - timedelta(hours=hours)

        # Start with time filter
        query = select(func.count()).select_from(self.model).where(self.model.timestamp >= time_threshold)

        # Add status code range filter if provided
        if status_min is not None:
            query = query.where(self.model.status_code >= status_min)
        if status_max is not None:
            query = query.where(self.model.status_code <= status_max)

        # Apply search filter if provided
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    self.model.path.ilike(search_term),
                    self.model.method.ilike(search_term),
                    self.model.client_ip.ilike(search_term),
                    self.model.username.ilike(search_term),
                    self.model.hostname.ilike(search_term),
                    # Convert status_code to string for searching
                    cast(self.model.status_code, String).ilike(search_term),
                    cast(self.model.application_id, String).ilike(search_term),
                )
            )

        result = self.db.execute(query).scalar_one()
        return result

    def get_status_distribution(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get distribution of logs by status code with time filter - specialized method."""
        time_threshold = datetime.now() - timedelta(hours=hours)

        query = """
        SELECT status_code, COUNT(*) as count
        FROM log
        WHERE timestamp >= :time_threshold
        GROUP BY status_code
        ORDER BY status_code
        """

        result = self.db.execute(text(query).bindparams(time_threshold=time_threshold)).all()

        return [{"status_code": row[0], "count": row[1]} for row in result]

    def get_recent_logs(self, days: int = 7, limit: int = 100) -> List[Log]:
        """Get recent logs limited by days - specialized method."""
        time_threshold = datetime.now() - timedelta(days=days)
        query = (
            select(self.model)
            .where(self.model.timestamp >= time_threshold)
            .order_by(desc(self.model.timestamp))
            .limit(limit)
        )

        result = self.db.execute(query).scalars().all()
        return list(result)

    def get_logs_by_status_range(self, status_min: int, status_max: int, limit: int = 100) -> List[Log]:
        """Get logs within a status code range - specialized method."""
        query = (
            select(self.model)
            .where(self.model.status_code.between(status_min, status_max))
            .order_by(desc(self.model.timestamp))
            .limit(limit)
        )

        result = self.db.execute(query).scalars().all()
        return list(result)

    def get_logs_by_time_range(self, start_time: datetime, end_time: datetime) -> List[Log]:
        """Get logs within a specific time range - specialized method."""
        query = (
            select(self.model)
            .where(self.model.timestamp.between(start_time, end_time))
            .order_by(desc(self.model.timestamp))
        )

        result = self.db.execute(query).scalars().all()
        return list(result)

    def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        """Clean up old logs - specialized method."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Count logs to be deleted
        count_query = select(func.count()).select_from(self.model).where(
            self.model.timestamp < cutoff_date
        )
        count_to_delete = self.db.execute(count_query).scalar()
        
        # Delete old logs
        delete_query = self.model.__table__.delete().where(
            self.model.timestamp < cutoff_date
        )
        self.db.execute(delete_query)
        self.db.commit()
        
        return count_to_delete

    # ===== ENHANCED BASE DAO METHODS =====
    # Override base methods to add logging-specific optimizations

    def get_all(self, skip: int = 0, limit: int = 100, **filters) -> List[Log]:
        """Override base method to add default ordering by timestamp."""
        query = select(self.model)
        
        # Apply filters
        if filters:
            filter_conditions = []
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    filter_conditions.append(getattr(self.model, key) == value)
            if filter_conditions:
                from sqlalchemy import and_
                query = query.where(and_(*filter_conditions))
        
        # Add default ordering by timestamp (most recent first)
        query = query.order_by(desc(self.model.timestamp)).offset(skip).limit(limit)
        result = self.db.execute(query)
        return list(result.scalars().all())

    def create_log(self, **log_data) -> Log:
        """Create a new log entry - specialized wrapper around base create."""
        # Ensure timestamp is set if not provided
        if 'timestamp' not in log_data:
            log_data['timestamp'] = datetime.now()
        
        return self.create(**log_data)

    # Note: We don't typically update or delete individual logs,
    # so we can rely on base DAO methods for those rare cases