from fastapi import APIRouter, Depends, HTTPException, Body, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.database import get_session
from app.reporting.service import ReportingService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/statistics", response_model=Dict[str, Any])
async def get_summary_statistics(session: Session = Depends(get_session)):
    """Get summary statistics for the dashboard"""
    reporting_service = ReportingService(session)
    return await reporting_service.get_summary_statistics()


@router.get("/recent-activities", response_model=Dict[str, Any])
async def get_recent_activities(
    days: int = Query(7, ge=1, le=30), session: Session = Depends(get_session)
):
    """Get recent activities for the dashboard"""
    reporting_service = ReportingService(session)
    return await reporting_service.get_recent_activities(days=days)


@router.get("/status-distribution", response_model=Dict[str, Any])
async def get_status_distribution(
    hours: int = Query(24, ge=1, le=168), session: Session = Depends(get_session)
):
    """Get distribution of logs by status code"""
    reporting_service = ReportingService(session)
    return await reporting_service.get_status_distribution(hours=hours)


@router.get("/cycle-codes", response_model=List[Dict[str, str]])
async def get_cycle_codes(session: Session = Depends(get_session)):
    """Get list of distinct cycle codes for report filters"""
    reporting_service = ReportingService(session)
    return await reporting_service.get_distinct_cycle_codes()


@router.post("/users-by-creation")
async def get_users_by_creation(
    params: Dict[str, Any] = Body(...), session: Session = Depends(get_session)
):
    """Report showing user creation by date"""
    reporting_service = ReportingService(session)
    return await reporting_service.get_users_by_creation(
        params.get("date_range", "last_30_days")
    )


@router.post("/employees-by-department")
async def get_employees_by_department(session: Session = Depends(get_session)):
    """Report showing employee count by department"""
    reporting_service = ReportingService(session)
    return await reporting_service.get_employees_by_department()


@router.post("/resource-counts")
async def get_resource_counts(
    params: Dict[str, Any] = Body(...), session: Session = Depends(get_session)
):
    """Report showing count of different resource types"""
    reporting_service = ReportingService(session)
    return await reporting_service.get_resource_counts(
        cycle_code=params.get("cycle_code")
    )


@router.post("/export-xlsx")
async def export_to_xlsx(
    export_data: Dict[str, Any] = Body(...), session: Session = Depends(get_session)
):
    """Export report data to Excel format"""
    reporting_service = ReportingService(session)
    output = await reporting_service.export_to_xlsx(export_data)

    file_name = export_data.get("fileName", "report")
    headers = {"Content-Disposition": f'attachment; filename="{file_name}.xlsx"'}

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
