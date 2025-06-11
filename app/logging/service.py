# app/logging/service.py
"""Refactored service layer for the logging module using BaseService."""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from datetime import datetime, timedelta

from app.core.base_service import BaseService
from app.logging.models import Log
from app.logging.schemas import LogRead, LogCreate, LogBase
from app.logging.dao import LogDAO


class LogService(BaseService[Log, LogCreate, LogBase, LogRead]):
    """Refactored service for retrieving and analyzing log data using BaseService."""

    def __init__(self, log_dao: LogDAO):
        super().__init__(log_dao)
        
    # ===== BASE SERVICE IMPLEMENTATION =====
    
    def _to_response(self, record: Log) -> LogRead:
        """Convert database model to response schema."""
        return LogRead.model_validate(record)
    
    def _validate_create(self, create_data: LogCreate) -> None:
        """Validate log creation data."""
        # Basic validation - most validation is handled by Pydantic schemas
        if not create_data.method or not create_data.path:
            raise ValueError("Method and path are required for log entries")
    
    def _validate_delete(self, record: Log) -> None:
        """Validate log deletion - generally logs should not be deleted individually."""
        # Logs are typically only bulk deleted during cleanup
        # Individual deletions should be rare and carefully controlled
        pass
    
    # ===== SPECIALIZED LOGGING METHODS =====
    # These provide the core logging functionality
    
    def get_logs_with_filters(
        self,
        limit: int = 50,
        offset: int = 0,
        hours: int = 24,
        log_id: Optional[int] = None,
        status_min: Optional[int] = None,
        status_max: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[LogRead]:
        """Get logs with pagination and filtering."""
        try:
            logs = self.dao.get_logs_with_filters(
                limit=limit,
                offset=offset,
                hours=hours,
                log_id=log_id,
                status_min=status_min,
                status_max=status_max,
                search=search,
            )
            return [self._to_response(log) for log in logs]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching logs: {str(e)}") from e

    def get_logs_count_with_filters(
        self,
        hours: int = 24,
        status_min: Optional[int] = None,
        status_max: Optional[int] = None,
        search: Optional[str] = None,
    ) -> int:
        """Get total count of logs matching the filters."""
        try:
            return self.dao.count_logs_with_filters(
                hours=hours, 
                status_min=status_min, 
                status_max=status_max, 
                search=search
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error counting logs: {str(e)}") from e

    def get_status_distribution(self, hours: int = 24) -> Dict[str, Any]:
        """Get distribution of logs by status code with time filter."""
        try:
            distribution = self.dao.get_status_distribution(hours=hours)

            # Add status descriptions using business logic
            for item in distribution:
                item["description"] = self._get_status_description(item["status_code"])

            return {
                "status_distribution": distribution,
                "timestamp": datetime.now().isoformat(),
                "period_hours": hours,
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating status distribution: {str(e)}",
            ) from e

    def get_recent_activities(self, days: int = 7) -> Dict[str, Any]:
        """Get recent activities for the dashboard."""
        if days <= 0:
            raise HTTPException(status_code=400, detail="Days must be greater than 0")

        try:
            recent_logs = self.dao.get_recent_logs(days=days)
            return {
                "recent_logs": [self._format_log_for_display(log) for log in recent_logs],
                "days": days,
                "timestamp": datetime.now().isoformat(),
                "total_logs": len(recent_logs),
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error generating recent activities: {str(e)}"
            ) from e

    def get_error_logs(self, hours: int = 24, limit: int = 100) -> List[LogRead]:
        """Get error logs (4xx and 5xx status codes)."""
        try:
            logs = self.dao.get_logs_by_status_range(400, 599, limit)
            # Filter by time if needed
            if hours < 24 * 365:  # Only filter if not requesting all time
                time_threshold = datetime.now() - timedelta(hours=hours)
                logs = [log for log in logs if log.timestamp >= time_threshold]
            
            return [self._to_response(log) for log in logs]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching error logs: {str(e)}") from e

    def get_performance_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance metrics for the specified time period."""
        try:
            from datetime import timedelta
            time_threshold = datetime.now() - timedelta(hours=hours)
            end_time = datetime.now()
            
            logs = self.dao.get_logs_by_time_range(time_threshold, end_time)
            
            # Calculate metrics
            total_requests = len(logs)
            if total_requests == 0:
                return self._empty_metrics(hours)
            
            # Status code distribution
            status_counts = {}
            response_times = []
            
            for log in logs:
                status_code = log.status_code
                status_counts[status_code] = status_counts.get(status_code, 0) + 1
                
                if log.processing_time is not None:
                    response_times.append(log.processing_time)
            
            # Calculate response time statistics
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            min_response_time = min(response_times) if response_times else 0
            max_response_time = max(response_times) if response_times else 0
            
            # Count by status categories
            success_count = sum(count for status, count in status_counts.items() if 200 <= status < 300)
            error_count = sum(count for status, count in status_counts.items() if status >= 400)
            
            return {
                "period_hours": hours,
                "total_requests": total_requests,
                "success_count": success_count,
                "error_count": error_count,
                "success_rate": (success_count / total_requests * 100) if total_requests > 0 else 0,
                "error_rate": (error_count / total_requests * 100) if total_requests > 0 else 0,
                "avg_response_time_ms": avg_response_time,
                "min_response_time_ms": min_response_time,
                "max_response_time_ms": max_response_time,
                "status_distribution": status_counts,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error calculating performance metrics: {str(e)}"
            ) from e

    def cleanup_old_logs(self, days_to_keep: int = 90) -> Dict[str, Any]:
        """Clean up old logs with validation."""
        if days_to_keep < 1:
            raise HTTPException(status_code=400, detail="Days to keep must be at least 1")
        
        if days_to_keep > 3650:  # 10 years
            raise HTTPException(status_code=400, detail="Days to keep cannot exceed 10 years")
        
        try:
            deleted_count = self.dao.cleanup_old_logs(days_to_keep)
            return {
                "deleted_count": deleted_count,
                "days_kept": days_to_keep,
                "cleanup_timestamp": datetime.now().isoformat(),
                "message": f"Successfully deleted {deleted_count} log entries older than {days_to_keep} days"
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error during log cleanup: {str(e)}"
            ) from e

    # ===== HELPER METHODS =====
    # Private methods for business logic and formatting

    def _get_status_description(self, status_code: int) -> str:
        """Get human-readable description for HTTP status code."""
        if 200 <= status_code < 300:
            return "Success"
        elif 300 <= status_code < 400:
            return "Redirection"
        elif 400 <= status_code < 500:
            return "Client Error"
        elif 500 <= status_code < 600:
            return "Server Error"
        else:
            return "Unknown"

    def _format_log_for_display(self, log: Log) -> Dict[str, Any]:
        """Format a log object for dashboard display."""
        # Convert to LogRead schema first
        log_dict = self._to_response(log).model_dump()

        # Add computed fields for display
        log_dict["status_category"] = self._get_status_description(log.status_code)
        
        # Format response time for display
        if log.processing_time is not None:
            if log.processing_time < 1000:
                log_dict["response_time_display"] = f"{log.processing_time:.0f}ms"
            else:
                log_dict["response_time_display"] = f"{log.processing_time/1000:.2f}s"
        else:
            log_dict["response_time_display"] = "N/A"

        return log_dict

    def _empty_metrics(self, hours: int) -> Dict[str, Any]:
        """Return empty metrics structure when no logs found."""
        return {
            "period_hours": hours,
            "total_requests": 0,
            "success_count": 0,
            "error_count": 0,
            "success_rate": 0.0,
            "error_rate": 0.0,
            "avg_response_time_ms": 0.0,
            "min_response_time_ms": 0.0,
            "max_response_time_ms": 0.0,
            "status_distribution": {},
            "timestamp": datetime.now().isoformat(),
        }

    # ===== OVERRIDE BASE METHODS FOR LOGGING-SPECIFIC BEHAVIOR =====
    
    def get_all(self, skip: int = 0, limit: int = 100, **filters) -> List[LogRead]:
        """Override base method to add default time-based filtering."""
        # For logs, we typically want recent logs by default
        logs = self.dao.get_all(skip=skip, limit=limit, **filters)
        return [self._to_response(log) for log in logs]

    def create(self, create_data: LogCreate, **extra_data) -> LogRead:
        """Create a new log entry - typically used by middleware."""
        self._validate_create(create_data)
        
        # Convert schema to dict
        data = create_data.model_dump()
        data.update(extra_data)
        
        # Ensure timestamp is set
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now()
        
        # Create using DAO
        log = self.dao.create_log(**data)
        
        return self._to_response(log)

    # Note: Update and delete operations are rare for logs
    # We rely on base service implementations for those edge cases