"""API router for the reporting module with endpoints for reports and statistics."""

from fastapi import APIRouter, Depends, Body, HTTPException, Path, Query
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
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


@router.get("/configurations", response_model=Dict[str, Any])
async def get_report_configurations(
    service: ReportingService = Depends(get_reporting_service),
) -> Dict[str, Any]:
    """Get all available report configurations with their column schemas"""
    return await service.get_report_configurations()


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


@router.post("/employee-details")
async def get_employee_details(
    service: ReportingService = Depends(get_reporting_service), params: Dict[str, Any] = Body(...)
) -> List[Dict[str, Any]]:
    """Report showing detailed employee information"""
    # Add implementation in service if needed
    # For now, returning empty list as placeholder until service method is implemented
    return []


@router.post("/user-details")
async def get_user_details(
    service: ReportingService = Depends(get_reporting_service), 
    params: Dict[str, Any] = Body(...)
) -> List[Dict[str, Any]]:
    """
    Report showing detailed user information
    
    Filter parameters:
    - username: Optional filter by username (partial match)
    - email: Optional filter by email (partial match)
    - is_active: Optional filter by active status
    - is_superuser: Optional filter by superuser status
    - date_range: Optional filter for users created within period (e.g., "7days", "30days", "90days", "1year")
    """
    return await service.get_user_details(
        username=params.get("username"),
        email=params.get("email"),
        is_active=params.get("is_active"),
        is_superuser=params.get("is_superuser"),
        date_range=params.get("date_range")
    )


@router.post("/subscriber-details")
async def get_subscriber_details(
    service: ReportingService = Depends(get_reporting_service), params: Dict[str, Any] = Body(...)
) -> List[Dict[str, Any]]:
    """Report showing detailed subscriber information"""
    # Add implementation in service if needed
    # For now, returning empty list as placeholder until service method is implemented
    return []


@router.post("/log-details")
async def get_log_details(
    service: ReportingService = Depends(get_reporting_service), params: Dict[str, Any] = Body(...)
) -> List[Dict[str, Any]]:
    """Report showing detailed log information"""
    # Add implementation in service if needed
    # For now, returning empty list as placeholder until service method is implemented
    return []


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

# New endpoints for task queue integration

@router.post("/execute-async/{report_id}")
async def execute_report_async(
    report_id: int = Path(..., description="ID of the report to execute"),
    parameters: Dict[str, Any] = Body(..., description="Parameters for the report"),
    user_id: Optional[int] = Query(None, description="ID of the user executing the report"),
    service: ReportingService = Depends(get_reporting_service)
) -> Dict[str, Any]:
    """
    Execute a report asynchronously using the task queue
    
    This endpoint will submit a task to the Celery queue and return immediately
    with a task ID that can be used to check the status of the report execution.
    """
    return await service.execute_report_async(report_id, parameters, user_id)


@router.get("/executions")
async def get_report_executions(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    report_id: Optional[int] = Query(None, description="Filter by report ID"),
    status: Optional[str] = Query(None, description="Filter by status (QUEUED, RUNNING, COMPLETED, FAILED)"),
    limit: int = Query(100, description="Maximum number of executions to return"),
    service: ReportingService = Depends(get_reporting_service)
) -> List[Dict[str, Any]]:
    """
    Get report execution history with optional filters
    """
    return await service.get_report_executions(
        user_id=user_id,
        report_id=report_id,
        status=status,
        limit=limit
    )


@router.get("/executions/{execution_id}")
async def get_report_execution(
    execution_id: int = Path(..., description="ID of the report execution"),
    service: ReportingService = Depends(get_reporting_service)
) -> Dict[str, Any]:
    """
    Get details of a specific report execution
    """
    executions = await service.get_report_executions(limit=1)
    for execution in executions:
        if execution["id"] == execution_id:
            return execution
    
    raise HTTPException(status_code=404, detail=f"Report execution {execution_id} not found")


# Scheduled reports endpoints

@router.post("/schedules")
async def create_scheduled_report(
    report_data: Dict[str, Any] = Body(..., description="Scheduled report data"),
    service: ReportingService = Depends(get_reporting_service)
) -> Dict[str, Any]:
    """
    Create a new scheduled report
    """
    return await service.create_scheduled_report(report_data)


@router.get("/schedules")
async def get_scheduled_reports(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    service: ReportingService = Depends(get_reporting_service)
) -> List[Dict[str, Any]]:
    """
    Get all scheduled reports, optionally filtered by user ID
    """
    return await service.get_scheduled_reports(user_id)


@router.get("/schedules/{report_id}")
async def get_scheduled_report(
    report_id: int = Path(..., description="ID of the scheduled report"),
    service: ReportingService = Depends(get_reporting_service)
) -> Dict[str, Any]:
    """
    Get a specific scheduled report by ID
    """
    reports = await service.get_scheduled_reports()
    for report in reports:
        if report["id"] == report_id:
            return report
    
    raise HTTPException(status_code=404, detail=f"Scheduled report {report_id} not found")


@router.put("/schedules/{report_id}")
async def update_scheduled_report(
    report_id: int = Path(..., description="ID of the scheduled report to update"),
    report_data: Dict[str, Any] = Body(..., description="Updated report data"),
    service: ReportingService = Depends(get_reporting_service)
) -> Dict[str, Any]:
    """
    Update a scheduled report
    """
    return await service.update_scheduled_report(report_id, report_data)


@router.delete("/schedules/{report_id}")
async def delete_scheduled_report(
    report_id: int = Path(..., description="ID of the scheduled report to delete"),
    service: ReportingService = Depends(get_reporting_service)
) -> Dict[str, Any]:
    """
    Delete a scheduled report
    """
    return await service.delete_scheduled_report(report_id)


# Internal endpoint for task queue to call
router.prefix = "/api"  # Change the prefix temporarily
internal_router = APIRouter(prefix="/internal", tags=["Internal"])


@internal_router.post("/reports/{report_id}/execute")
async def internal_execute_report(
    report_id: int = Path(..., description="ID of the report to execute"),
    data: Dict[str, Any] = Body(..., description="Execution parameters and metadata"),
    service: ReportingService = Depends(get_reporting_service)
) -> Dict[str, Any]:
    """
    Internal endpoint for the task queue to call when executing a report
    
    This endpoint should not be called directly by clients.
    """
    # This would contain the actual report generation logic
    # For now, we'll return a simulated result
    
    # In a real implementation, we would:
    # 1. Generate the report
    # 2. Save it to a file or database
    # 3. Update the execution record
    # 4. Return the result
    
    try:
        # Simulate report generation
        import time
        import random
        time.sleep(2)  # Simulate some processing time
        
        # Generate a simulated file path
        file_path = f"/reports/{report_id}/{data['task_id']}.xlsx"
        
        # Update the execution record
        await service.report_dao.update_report_execution_status(
            task_id=data['task_id'],
            status="COMPLETED",
            result_path=file_path
        )
        
        # Notify the user if user_id is provided
        if data.get('user_id'):
            # In a real implementation, we would call a notification service
            pass
        
        return {
            "status": "COMPLETED",
            "report_id": report_id,
            "task_id": data['task_id'],
            "report_path": file_path
        }
    except Exception as e:
        # Update the execution record with the error
        await service.report_dao.update_report_execution_status(
            task_id=data['task_id'],
            status="FAILED",
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error executing report: {str(e)}"
        )

# Restore the router prefix and add the internal router
router.prefix = "/reports"
router.include_router(internal_router)
