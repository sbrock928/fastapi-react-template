from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.core.dependencies import SessionDep
from app.logging.schemas import LogRead
from app.logging.service import LogService

router = APIRouter(
    prefix="/logs",
    tags=["logs"],
)


@router.get("/", response_model=List[LogRead])
async def get_logs(
    session: SessionDep,
    response: Response,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    hours: int = Query(24, ge=1, le=168),
    log_id: Optional[int] = None,
    status_min: Optional[int] = None,
    status_max: Optional[int] = None,
    search: Optional[str] = None,
):
    """Get logs with pagination and filtering"""
    log_service = LogService(session)
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
    session: SessionDep, hours: int = Query(24, ge=1, le=168)
):
    """Get distribution of logs by status code"""
    log_service = LogService(session)
    return await log_service.get_status_distribution(hours=hours)
