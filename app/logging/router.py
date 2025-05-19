"""API router for the logging module with endpoints for retrieving and analyzing logs."""
from fastapi import APIRouter, Depends, Query, Response
from typing import List, Optional, Dict, Any
from app.core.dependencies import SessionDep
from app.logging.schemas import LogRead
from app.logging.service import LogService
from app.logging.dao import LogDAO

router = APIRouter(
    prefix="/logs",
    tags=["logs"],
)


def get_log_service(session: SessionDep) -> LogService:
    return LogService(LogDAO(session))


@router.get("/", response_model=List[LogRead])
async def get_logs(
    response: Response,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    hours: int = Query(24, ge=1, le=168),
    log_id: Optional[int] = None,
    status_min: Optional[int] = None,
    status_max: Optional[int] = None,
    search: Optional[str] = None,
    log_service: LogService = Depends(get_log_service),
) -> List[LogRead]:
    """Get logs with pagination and filtering"""
    logs = await log_service.get_logs(
        limit=limit,
        offset=offset,
        hours=hours,
        log_id=log_id,
        status_min=status_min,
        status_max=status_max,
        search=search,
    )

    # Get total count for pagination
    total_count = await log_service.get_logs_count(
        hours=hours, status_min=status_min, status_max=status_max, search=search
    )

    # Set total count in header
    response.headers["X-Total-Count"] = str(total_count)

    return logs


@router.get("/status-distribution", response_model=Dict[str, Any])
async def get_status_distribution(
    hours: int = Query(24, ge=1, le=168),
    log_service: LogService = Depends(get_log_service),
) -> Dict[str, Any]:
    """Get distribution of logs by status code"""
    return await log_service.get_status_distribution(hours=hours)


@router.get("/recent-activities", response_model=Dict[str, Any])
async def get_recent_activities(
    days: int = Query(7, ge=1, le=30),
    log_service: LogService = Depends(get_log_service),
) -> Dict[str, Any]:
    """Get recent activities for the dashboard"""
    return await log_service.get_recent_activities(days=days)
