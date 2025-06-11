# app/logging/router.py
"""Refactored API router for the logging module using BaseService architecture."""

from fastapi import APIRouter, Depends, Query, Response, HTTPException, Body
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.core.dependencies import SessionDep
from app.logging.schemas import LogRead
from app.logging.service import LogService
from app.logging.dao import LogDAO


router = APIRouter(
    prefix="/logs",
    tags=["logs"],
)


# ===== DEPENDENCY INJECTION =====

def get_log_dao(session: SessionDep) -> LogDAO:
    """Get LogDAO instance."""
    return LogDAO(session)


def get_log_service(log_dao: LogDAO = Depends(get_log_dao)) -> LogService:
    """Get LogService instance."""
    return LogService(log_dao)


# ===== CORE LOG RETRIEVAL ENDPOINTS =====

@router.get("/", response_model=List[LogRead])
def get_logs(
    response: Response,
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    log_id: Optional[int] = Query(None, description="Specific log ID to retrieve"),
    status_min: Optional[int] = Query(None, ge=100, le=599, description="Minimum status code"),
    status_max: Optional[int] = Query(None, ge=100, le=599, description="Maximum status code"),
    search: Optional[str] = Query(None, description="Search term for filtering logs"),
    log_service: LogService = Depends(get_log_service),
) -> List[LogRead]:
    """Get logs with pagination and filtering using BaseService."""
    
    # Validate status code range
    if status_min is not None and status_max is not None and status_min > status_max:
        raise HTTPException(status_code=400, detail="status_min cannot be greater than status_max")
    
    logs = log_service.get_logs_with_filters(
        limit=limit,
        offset=offset,
        hours=hours,
        log_id=log_id,
        status_min=status_min,
        status_max=status_max,
        search=search,
    )

    # Get total count for pagination headers
    total_count = log_service.get_logs_count_with_filters(
        hours=hours, 
        status_min=status_min, 
        status_max=status_max, 
        search=search
    )

    # Set pagination headers
    response.headers["X-Total-Count"] = str(total_count)
    response.headers["X-Page-Size"] = str(limit)
    response.headers["X-Page-Offset"] = str(offset)

    return logs


@router.get("/recent", response_model=List[LogRead])
def get_recent_logs(
    limit: int = Query(100, ge=1, le=500, description="Maximum number of recent logs"),
    log_service: LogService = Depends(get_log_service),
) -> List[LogRead]:
    """Get recent logs using BaseService get_all method."""
    return log_service.get_all(skip=0, limit=limit)


@router.get("/errors", response_model=List[LogRead])
def get_error_logs(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of error logs"),
    log_service: LogService = Depends(get_log_service),
) -> List[LogRead]:
    """Get error logs (4xx and 5xx status codes)."""
    return log_service.get_error_logs(hours=hours, limit=limit)


# ===== ANALYTICS AND DISTRIBUTION ENDPOINTS =====

@router.get("/status-distribution", response_model=Dict[str, Any])
def get_status_distribution(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    log_service: LogService = Depends(get_log_service),
) -> Dict[str, Any]:
    """Get distribution of logs by status code."""
    return log_service.get_status_distribution(hours=hours)


@router.get("/performance-metrics", response_model=Dict[str, Any])
def get_performance_metrics(
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    log_service: LogService = Depends(get_log_service),
) -> Dict[str, Any]:
    """Get performance metrics for the specified time period."""
    return log_service.get_performance_metrics(hours=hours)


@router.get("/recent-activities", response_model=Dict[str, Any])
def get_recent_activities(
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze"),
    log_service: LogService = Depends(get_log_service),
) -> Dict[str, Any]:
    """Get recent activities for the dashboard."""
    return log_service.get_recent_activities(days=days)


# ===== ADVANCED ANALYTICS ENDPOINTS =====

@router.get("/dashboard", response_model=Dict[str, Any])
def get_dashboard_data(
    hours: int = Query(24, ge=1, le=168, description="Time window for dashboard data"),
    log_service: LogService = Depends(get_log_service),
) -> Dict[str, Any]:
    """Get comprehensive dashboard data combining multiple metrics."""
    try:
        # Get various metrics for dashboard
        status_distribution = log_service.get_status_distribution(hours=hours)
        performance_metrics = log_service.get_performance_metrics(hours=hours)
        recent_activities = log_service.get_recent_activities(days=max(1, hours // 24))
        
        # Get recent error logs for alerts
        error_logs = log_service.get_error_logs(hours=hours, limit=10)
        
        dashboard_data = {
            "overview": {
                "time_window_hours": hours,
                "total_requests": performance_metrics["total_requests"],
                "success_rate": performance_metrics["success_rate"],
                "error_rate": performance_metrics["error_rate"],
                "avg_response_time": performance_metrics["avg_response_time_ms"],
            },
            "status_distribution": status_distribution,
            "performance_metrics": performance_metrics,
            "recent_activities": recent_activities,
            "recent_errors": [log.model_dump() for log in error_logs],
            "alerts": {
                "high_error_rate": performance_metrics["error_rate"] > 5.0,
                "slow_responses": performance_metrics["avg_response_time_ms"] > 5000,
                "recent_errors_count": len(error_logs),
            },
            "generated_at": datetime.now().isoformat(),
        }
        
        return dashboard_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating dashboard data: {str(e)}")


@router.post("/search", response_model=List[LogRead])
def search_logs(
    search_params: Dict[str, Any] = Body(...),
    log_service: LogService = Depends(get_log_service),
) -> List[LogRead]:
    """Advanced log search with multiple criteria."""
    try:
        # Extract search parameters
        limit = min(search_params.get("limit", 100), 1000)
        offset = search_params.get("offset", 0)
        hours = min(search_params.get("hours", 24), 168)
        status_min = search_params.get("status_min")
        status_max = search_params.get("status_max")
        search_term = search_params.get("search")
        
        # Validate parameters
        if status_min is not None and (status_min < 100 or status_min > 599):
            raise HTTPException(status_code=400, detail="status_min must be between 100 and 599")
        if status_max is not None and (status_max < 100 or status_max > 599):
            raise HTTPException(status_code=400, detail="status_max must be between 100 and 599")
        if status_min is not None and status_max is not None and status_min > status_max:
            raise HTTPException(status_code=400, detail="status_min cannot be greater than status_max")
        
        return log_service.get_logs_with_filters(
            limit=limit,
            offset=offset,
            hours=hours,
            status_min=status_min,
            status_max=status_max,
            search=search_term,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching logs: {str(e)}")


# ===== MAINTENANCE ENDPOINTS =====

@router.post("/cleanup", response_model=Dict[str, Any])
def cleanup_old_logs(
    cleanup_params: Dict[str, int] = Body(..., example={"days_to_keep": 90}),
    log_service: LogService = Depends(get_log_service),
) -> Dict[str, Any]:
    """Clean up old logs (admin function)."""
    days_to_keep = cleanup_params.get("days_to_keep", 90)
    return log_service.cleanup_old_logs(days_to_keep)


@router.get("/stats", response_model=Dict[str, Any])
def get_log_statistics(
    log_service: LogService = Depends(get_log_service),
) -> Dict[str, Any]:
    """Get overall log statistics."""
    try:
        # Get basic statistics using BaseService methods
        total_logs = log_service.count()
        
        # Get recent statistics
        recent_24h = log_service.get_performance_metrics(hours=24)
        recent_7d = log_service.get_performance_metrics(hours=24 * 7)
        
        return {
            "total_logs": total_logs,
            "last_24_hours": recent_24h,
            "last_7_days": recent_7d,
            "generated_at": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving log statistics: {str(e)}")


# ===== INDIVIDUAL LOG ENDPOINTS =====

@router.get("/{log_id}", response_model=LogRead)
def get_log_by_id(
    log_id: int,
    log_service: LogService = Depends(get_log_service),
) -> LogRead:
    """Get a specific log by ID using BaseService."""
    log = log_service.get_by_id(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


@router.delete("/{log_id}")
def delete_log(
    log_id: int,
    log_service: LogService = Depends(get_log_service),
) -> Dict[str, str]:
    """Delete a specific log entry (rare operation)."""
    success = log_service.delete(log_id)
    if not success:
        raise HTTPException(status_code=404, detail="Log not found")
    return {"message": f"Log {log_id} deleted successfully"}


# ===== HEALTH CHECK ENDPOINT =====

@router.get("/health", response_model=Dict[str, str])
def health_check(
    log_service: LogService = Depends(get_log_service),
) -> Dict[str, str]:
    """Health check endpoint for the logging service."""
    try:
        # Simple check - try to count logs
        log_service.count()
        return {
            "status": "healthy",
            "service": "logging",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=503, 
            detail=f"Logging service unhealthy: {str(e)}"
        )