from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session, select
from typing import List, Optional, Dict, Any
from app.database import get_session
from app.logging.models import Log, LogBase
from app.logging.services import LogService
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta

router = APIRouter(
    prefix="/api/logs",
    tags=["logs"],
)


@router.get("/", response_model=List[Log])
async def get_logs(
    response: Response,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    hours: int = Query(24, ge=1, le=168),
    log_id: Optional[int] = None,
    status_min: Optional[int] = None,
    status_max: Optional[int] = None,
    search: Optional[str] = None,
    session: Session = Depends(get_session),
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
    hours: int = Query(24, ge=1, le=168), session: Session = Depends(get_session)
):
    """Get distribution of logs by status code"""
    log_service = LogService(session)
    return await log_service.get_status_distribution(hours=hours)
