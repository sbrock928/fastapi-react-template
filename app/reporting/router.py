"""API router for the reporting module with endpoints for reports and statistics."""
from fastapi import APIRouter, Depends, Body
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any
from app.core.dependencies import SessionDep
from app.reporting.service import ReportingService
from app.reporting.dao import ReportingDAO


router = APIRouter(prefix="/reports", tags=["Reports"])


def get_reporting_service(session: SessionDep) -> ReportingService:
    return ReportingService(ReportingDAO(session))


@router.get("/statistics", response_model=Dict[str, Any])
async def get_summary_statistics(
    service: ReportingService = Depends(get_reporting_service),
) -> Dict[str, Any]:
    """Get summary statistics for the dashboard"""
    return await service.get_summary_statistics()


@router.get("/cycle-codes", response_model=List[Dict[str, str]])
async def get_cycle_codes(
    service: ReportingService = Depends(get_reporting_service),
) -> List[Dict[str, str]]:
    """Get list of distinct cycle codes for report filters"""
    return await service.get_distinct_cycle_codes()


@router.post("/employees-by-department")
async def get_employees_by_department(
    service: ReportingService = Depends(get_reporting_service),
) -> List[Dict[str, Any]]:
    """Report showing employee count by department"""
    return await service.get_employees_by_department()


@router.post("/resource-counts")
async def get_resource_counts(
    service: ReportingService = Depends(get_reporting_service), params: Dict[str, Any] = Body(...)
) -> List[Dict[str, Any]]:
    """Report showing count of different resource types"""
    return await service.get_resource_counts(cycle_code=params.get("cycle_code"))


@router.post("/export-xlsx")
async def export_to_xlsx(
    service: ReportingService = Depends(get_reporting_service),
    export_data: Dict[str, Any] = Body(...),
) -> StreamingResponse:
    """Export report data to Excel format"""
    output = await service.export_to_xlsx(export_data)

    file_name = export_data.get("fileName", "report")
    headers = {"Content-Disposition": f'attachment; filename="{file_name}.xlsx"'}

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
