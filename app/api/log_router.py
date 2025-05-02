from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.models.base import Log
from typing import List
from datetime import datetime, timedelta

router = APIRouter(
    prefix="/api/logs",
    tags=["logs"],
)

@router.get("/", response_model=List[dict])
async def get_logs(
    session: Session = Depends(get_session),
    limit: int = 100,
    offset: int = 0,
    hours: int = 24,
    log_id: int = None
):
    """
    Get the most recent logs from the system.
    
    - limit: Maximum number of logs to return
    - offset: Number of logs to skip for pagination
    - hours: Only return logs from the last X hours
    """
    if log_id:
        # If a specific log is requested
        query = select(Log).where(Log.id == log_id)
    else:
        # Calculate the cutoff time
        cutoff_time = datetime.now() - timedelta(hours=hours)
    
        # Build the query
        query = select(Log).where(Log.timestamp > cutoff_time).order_by(Log.timestamp.desc()).offset(offset).limit(limit)
    
    # Execute the query
    logs = session.exec(query).all()
    
    # Convert to dictionaries for JSON serialization
    result = []
    for log in logs:
        try:
            # Handle both older and newer Pydantic versions
            log_dict = log.dict()
        except AttributeError:
            log_dict = log.model_dump()
            
        # Format timestamp for better readability
        log_dict["timestamp"] = log_dict["timestamp"].isoformat()
        
        result.append(log_dict)
    
    return result