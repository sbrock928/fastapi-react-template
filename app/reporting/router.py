from fastapi import APIRouter, Depends, HTTPException, Body, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.core.dependencies import SessionDep
from app.reporting.service import ReportingService
from app.logging.service import LogService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/statistics", response_model=Dict[str, Any])
async def get_summary_statistics(session: SessionDep):
    """Get summary statistics for the dashboard"""
    reporting_service = ReportingService(session)
    return await reporting_service.get_summary_statistics()


@router.get("/recent-activities", response_model=Dict[str, Any])
async def get_recent_activities(
    session: SessionDep,
    days: int = Query(7, ge=1, le=30)
):
    """Get recent activities for the dashboard"""
    # Use LogService since ReportingService doesn't have the get_recent_activities method
    log_service = LogService(session)
    return await log_service.get_recent_activities(days=days)


@router.get("/status-distribution", response_model=Dict[str, Any])
async def get_status_distribution(
    session: SessionDep,
    hours: int = Query(24, ge=1, le=168)
):
    """Get distribution of logs by status code"""
    reporting_service = ReportingService(session)
    return await reporting_service.get_status_distribution(hours=hours)


@router.get("/cycle-codes", response_model=List[Dict[str, str]])
async def get_cycle_codes(session: SessionDep):
    """Get list of distinct cycle codes for report filters"""
    reporting_service = ReportingService(session)
    return await reporting_service.get_distinct_cycle_codes()


@router.post("/users-by-creation")
async def get_users_by_creation(
    session: SessionDep,
    params: Dict[str, Any] = Body(...)
):
    """Report showing user creation by date"""
    reporting_service = ReportingService(session)
    return await reporting_service.get_users_by_creation(
        params.get("date_range", "last_30_days")
    )


@router.post("/employees-by-department")
async def get_employees_by_department(session: SessionDep):
    """Report showing employee count by department"""
    reporting_service = ReportingService(session)
    return await reporting_service.get_employees_by_department()


@router.post("/resource-counts")
async def get_resource_counts(
    session: SessionDep,
    params: Dict[str, Any] = Body(...)
):
    """Report showing count of different resource types"""
    reporting_service = ReportingService(session)
    return await reporting_service.get_resource_counts(
        cycle_code=params.get("cycle_code")
    )


@router.post("/export-xlsx")
async def export_to_xlsx(
    session: SessionDep,
    export_data: Dict[str, Any] = Body(...)
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
