"""Refactored API router for the reporting module to work with BaseService."""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
import pandas as pd
import io
from app.reporting.service import ReportService
from app.reporting.dao import ReportDAO
from app.reporting.schemas import (
    ReportRead,
    ReportCreate,
    ReportUpdate,
    ReportSummary,
    RunReportRequest,
    AvailableCalculation,
    ReportScope,
)
from app.core.dependencies import SessionDep, DWSessionDep, get_user_calculation_service, get_system_calculation_service, get_report_execution_service
from app.datawarehouse.dao import DatawarehouseDAO
from app.calculations.service import UserCalculationService, SystemCalculationService, ReportExecutionService


router = APIRouter(prefix="/reports", tags=["reporting"])


# Dependency functions
def get_report_dao(db: SessionDep) -> ReportDAO:
    return ReportDAO(db)


def get_dw_dao(db: DWSessionDep) -> DatawarehouseDAO:
    return DatawarehouseDAO(db)


def get_report_service(
    report_dao: ReportDAO = Depends(get_report_dao),
    dw_dao: DatawarehouseDAO = Depends(get_dw_dao),
    user_calc_service: UserCalculationService = Depends(get_user_calculation_service),
    system_calc_service: SystemCalculationService = Depends(get_system_calculation_service),
    report_execution_service: ReportExecutionService = Depends(get_report_execution_service)
) -> ReportService:
    return ReportService(
        report_dao, 
        dw_dao, 
        user_calc_service, 
        system_calc_service, 
        report_execution_service
    )


# ===== REPORT CONFIGURATION ENDPOINTS =====


@router.get("/", response_model=List[ReportRead])
def get_all_reports(service: ReportService = Depends(get_report_service)) -> List[ReportRead]:
    """Get all report configurations."""
    return service.get_all_with_relationships()  # FIXED: removed await, using custom method


@router.get("/summary", response_model=List[ReportSummary])
def get_all_reports_summary(
    service: ReportService = Depends(get_report_service),
) -> List[ReportSummary]:
    """Get all reports with summary information."""
    return service.get_all_summaries()  # FIXED: removed await


@router.get("/{report_id}", response_model=ReportRead)
def get_report_by_id(
    report_id: int, service: ReportService = Depends(get_report_service)
) -> ReportRead:
    """Get a specific report configuration by ID."""
    report = service.get_by_id_with_relationships(report_id)  # FIXED: removed await, using custom method
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("/", response_model=ReportRead)
def create_report(
    report_data: ReportCreate, service: ReportService = Depends(get_report_service)
) -> ReportRead:
    """Create a new report configuration."""
    return service.create_with_relationships(report_data)  # FIXED: removed await, using custom method


@router.patch("/{report_id}", response_model=ReportRead)
def update_report(
    report_id: int, report_data: ReportUpdate, service: ReportService = Depends(get_report_service)
) -> ReportRead:
    """Update an existing report configuration."""
    report = service.update_with_relationships(report_id, report_data)  # FIXED: removed await, using custom method
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.delete("/{report_id}")
def delete_report(
    report_id: int, service: ReportService = Depends(get_report_service)
) -> Dict[str, str]:
    """Delete a report configuration."""
    success = service.delete_report(report_id)  # FIXED: removed await, using custom method
    if not success:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"message": "Report deleted successfully"}


# ===== REPORT EXECUTION ENDPOINTS =====


@router.post("/run", response_model=List[Dict[str, Any]])
def run_report(
    request: RunReportRequest, service: ReportService = Depends(get_report_service)
) -> List[Dict[str, Any]]:
    """Run a saved report configuration."""
    return service.run_saved_report(
        request.report_id, request.cycle_code
    )  # FIXED: removed await


@router.post("/run/{report_id}", response_model=List[Dict[str, Any]])
def run_report_by_id(
    report_id: int, request: Dict[str, Any], service: ReportService = Depends(get_report_service)
) -> List[Dict[str, Any]]:
    """Run a saved report by ID with cycle parameter."""
    cycle_code = request.get("cycle_code")
    if not cycle_code:
        raise HTTPException(status_code=400, detail="cycle_code is required")
    return service.run_saved_report(report_id, cycle_code)  # FIXED: removed await


# ===== PREVIEW AND EXECUTION LOG ENDPOINTS =====


@router.get("/{report_id}/preview-sql")
def preview_report_sql(
    report_id: int, cycle_code: int = 202404, service: ReportService = Depends(get_report_service)
) -> Dict[str, Any]:
    """Preview SQL that would be generated for a report."""
    return service.preview_report_sql(report_id, cycle_code)  # FIXED: removed await


@router.get("/{report_id}/execution-logs")
def get_report_execution_logs(
    report_id: int, limit: int = 50, service: ReportService = Depends(get_report_service)
) -> List[Dict[str, Any]]:
    """Get execution logs for a report."""
    return service.get_execution_logs(report_id, limit)  # FIXED: removed await


# ===== CALCULATION CONFIGURATION ENDPOINTS =====


@router.get("/calculations/available", response_model=List[AvailableCalculation])
def get_available_calculations(
    scope: ReportScope, service: ReportService = Depends(get_report_service)
) -> List[AvailableCalculation]:
    """Get available calculations for report configuration based on scope."""
    return service.get_available_calculations(scope)  # This one stays sync


# ===== DATA ENDPOINTS (for report building) =====


@router.get("/data/issuer-codes", response_model=List[str])
def get_available_issuer_codes(
    service: ReportService = Depends(get_report_service),
) -> List[str]:
    """Get unique issuer codes for deal filtering."""
    deals = service.get_available_deals()  # This one stays sync
    issuer_codes = sorted(list(set(deal["issr_cde"] for deal in deals)))
    return issuer_codes


@router.get("/data/deals", response_model=List[Dict[str, Any]])
def get_available_deals(
    issuer_code: Optional[str] = None,
    service: ReportService = Depends(get_report_service),
) -> List[Dict[str, Any]]:
    """Get available deals for report building, optionally filtered by issuer code."""
    deals = service.get_available_deals()  # This one stays sync

    # Filter by issuer code if provided
    if issuer_code:
        deals = [deal for deal in deals if deal["issr_cde"] == issuer_code]

    return deals


@router.post("/data/tranches", response_model=Dict[int, List[Dict[str, Any]]])
def get_available_tranches(
    request: Dict[str, Any], service: ReportService = Depends(get_report_service)
) -> Dict[int, List[Dict[str, Any]]]:
    """Get available tranches for specific deals."""
    deal_ids = request.get("dl_nbrs", [])
    cycle_code = request.get("cycle_code")

    tranches_by_deal = service.get_available_tranches_for_deals(
        deal_ids, cycle_code
    )  # This one stays sync
    return {int(deal_id): tranches for deal_id, tranches in tranches_by_deal.items()}


@router.get("/data/cycles", response_model=List[Dict[str, Any]])
def get_available_cycles(
    service: ReportService = Depends(get_report_service),
) -> List[Dict[str, str]]:
    """Get available cycle codes from the data warehouse."""
    return service.get_available_cycles()  # This one stays sync


# ===== EXPORT ENDPOINTS =====


@router.post("/export-xlsx")
def export_to_xlsx(request: Dict[str, Any]) -> Response:
    """Export report data to Excel (XLSX) format."""
    try:
        report_type = request.get("reportType", "Unknown Report")
        data = request.get("data", [])
        file_name = request.get("fileName", "report.xlsx")

        if not data:
            raise HTTPException(status_code=400, detail="No data provided for export")

        # Create DataFrame from the data
        df = pd.DataFrame(data)

        # Create Excel file in memory
        excel_buffer = io.BytesIO()

        with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
            # Write the data to the Excel file
            df.to_excel(
                writer, sheet_name=report_type[:31], index=False
            )  # Excel sheet name limit is 31 chars

            # Get the workbook and worksheet to format
            workbook = writer.book
            worksheet = writer.sheets[report_type[:31]]

            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter

                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass

                # Set column width with some padding, max 50 characters
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        excel_buffer.seek(0)

        # Ensure the filename has .xlsx extension
        if not file_name.endswith(".xlsx"):
            file_name += ".xlsx"

        # Return the Excel file as a response
        return Response(
            content=excel_buffer.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={file_name}"},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating Excel file: {str(e)}")


# Additional endpoints to add to app/reporting/router.py
"""Execution log endpoints for the reporting router."""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import Query, HTTPException, Body
from app.reporting.execution_log_service import ReportExecutionLogService

# Add this import to the top of the reporting router
from app.core.dependencies import get_report_execution_log_service

# ===== EXECUTION LOG ENDPOINTS =====

@router.get("/execution-logs/recent")
def get_recent_execution_logs(
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    execution_log_service: ReportExecutionLogService = Depends(get_report_execution_log_service)
):
    """Get recent execution logs across all reports."""
    try:
        logs = execution_log_service.get_recent_executions(limit)
        
        return {
            "success": True,
            "data": logs,
            "metadata": {
                "limit": limit,
                "record_count": len(logs),
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving execution logs: {str(e)}")


@router.get("/execution-logs/failed")
def get_failed_execution_logs(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of records to return"),
    execution_log_service: ReportExecutionLogService = Depends(get_report_execution_log_service)
):
    """Get recent failed execution logs for troubleshooting."""
    try:
        failed_logs = execution_log_service.get_failed_executions(limit)
        
        return {
            "success": True,
            "data": failed_logs,
            "metadata": {
                "limit": limit,
                "record_count": len(failed_logs),
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving failed execution logs: {str(e)}")


@router.get("/{report_id}/execution-logs/detailed")
def get_detailed_report_execution_logs(
    report_id: int,
    limit: int = Query(50, ge=1, le=200, description="Maximum number of records to return"),
    execution_log_service: ReportExecutionLogService = Depends(get_report_execution_log_service),
    service: ReportService = Depends(get_report_service)
):
    """Get detailed execution logs for a specific report with statistics."""
    try:
        # Verify report exists
        report = service.get_by_id_with_relationships(report_id)  # FIXED: removed await, using custom method
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Get execution logs and statistics
        logs = execution_log_service.get_execution_logs_for_report(report_id, limit)
        stats = execution_log_service.get_execution_stats_for_report(report_id)
        
        return {
            "success": True,
            "data": {
                "report_info": {
                    "id": report.id,
                    "name": report.name,
                    "description": report.description,
                    "scope": report.scope
                },
                "execution_logs": logs,
                "statistics": stats
            },
            "metadata": {
                "report_id": report_id,
                "limit": limit,
                "log_count": len(logs)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving detailed execution logs: {str(e)}")


@router.post("/execution-logs/search")
def search_execution_logs(
    search_params: Dict[str, Any] = Body(...),
    execution_log_service: ReportExecutionLogService = Depends(get_report_execution_log_service)
):
    """Search execution logs by date range and other criteria."""
    try:
        # Parse dates
        start_date_str = search_params.get("start_date")
        end_date_str = search_params.get("end_date")
        report_id = search_params.get("report_id")
        
        if not start_date_str or not end_date_str:
            raise HTTPException(
                status_code=400, 
                detail="Both start_date and end_date are required"
            )
        
        # Parse date strings
        start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        
        logs = execution_log_service.get_executions_by_date_range(
            start_date, end_date, report_id
        )
        
        return {
            "success": True,
            "data": logs,
            "metadata": {
                "search_params": search_params,
                "record_count": len(logs),
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching execution logs: {str(e)}")


@router.get("/execution-logs/performance")
def get_performance_dashboard(
    days_back: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    execution_log_service: ReportExecutionLogService = Depends(get_report_execution_log_service)
):
    """Get performance metrics dashboard."""
    try:
        performance_data = execution_log_service.get_performance_dashboard(days_back)
        
        return {
            "success": True,
            "data": performance_data,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "dashboard_version": "1.0"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving performance dashboard: {str(e)}")


@router.get("/execution-logs/trends")
def get_execution_trends(
    days_back: int = Query(30, ge=7, le=365, description="Number of days to analyze"),
    execution_log_service: ReportExecutionLogService = Depends(get_report_execution_log_service)
):
    """Get execution trends for analytics."""
    try:
        trends = execution_log_service.get_execution_trends(days_back)
        
        return {
            "success": True,
            "data": trends,
            "metadata": {
                "generated_at": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving execution trends: {str(e)}")


@router.post("/execution-logs/cleanup")
def cleanup_old_execution_logs(
    cleanup_params: Dict[str, int] = Body(..., example={"days_to_keep": 90}),
    execution_log_service: ReportExecutionLogService = Depends(get_report_execution_log_service)
):
    """Clean up old execution logs (admin function)."""
    try:
        days_to_keep = cleanup_params.get("days_to_keep", 90)
        result = execution_log_service.cleanup_old_logs(days_to_keep)
        
        return {
            "success": True,
            "data": result,
            "message": f"Cleaned up execution logs older than {days_to_keep} days"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning up execution logs: {str(e)}")


# ===== EXECUTION ANALYTICS ENDPOINTS =====

@router.get("/{report_id}/execution-logs/analytics")
def get_report_execution_analytics(
    report_id: int,
    days_back: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    execution_log_service: ReportExecutionLogService = Depends(get_report_execution_log_service),
    service: ReportService = Depends(get_report_service)
):
    """Get comprehensive execution analytics for a specific report."""
    try:
        # Verify report exists
        report = service.get_by_id_with_relationships(report_id)  # FIXED: removed await, using custom method
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Get comprehensive stats
        stats = execution_log_service.get_execution_stats_for_report(report_id)
        
        # Get recent executions for trends
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        recent_logs = execution_log_service.get_executions_by_date_range(
            start_date, end_date, report_id
        )
        
        # Calculate daily execution counts
        daily_counts = {}
        for log_data in recent_logs:
            log_date = datetime.fromisoformat(log_data["executed_at"]).date()
            date_key = log_date.isoformat()
            if date_key not in daily_counts:
                daily_counts[date_key] = {"successful": 0, "failed": 0, "total": 0}
            
            daily_counts[date_key]["total"] += 1
            if log_data["success"]:
                daily_counts[date_key]["successful"] += 1
            else:
                daily_counts[date_key]["failed"] += 1
        
        # Format for charts
        daily_trends = [
            {
                "date": date,
                "successful_executions": counts["successful"],
                "failed_executions": counts["failed"],
                "total_executions": counts["total"]
            }
            for date, counts in sorted(daily_counts.items())
        ]
        
        analytics_data = {
            "report_info": {
                "id": report.id,
                "name": report.name,
                "description": report.description,
                "scope": report.scope
            },
            "overall_statistics": stats,
            "period_analysis": {
                "period_days": days_back,
                "start_date": start_date.date().isoformat(),
                "end_date": end_date.date().isoformat(),
                "daily_trends": daily_trends,
                "total_executions_in_period": len(recent_logs)
            },
            "performance_insights": {
                "reliability_score": stats["success_rate"],
                "avg_execution_time_display": stats.get("average_execution_time_display", "N/A"),
                "has_recent_failures": any(not log["success"] for log in recent_logs[-10:]) if recent_logs else False,
                "execution_frequency": len(recent_logs) / days_back if days_back > 0 else 0
            }
        }
        
        return {
            "success": True,
            "data": analytics_data,
            "metadata": {
                "report_id": report_id,
                "analysis_period_days": days_back,
                "generated_at": datetime.now().isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating execution analytics: {str(e)}")


# ===== SYSTEM-WIDE EXECUTION DASHBOARD =====

@router.get("/execution-logs/dashboard")
def get_execution_dashboard(
    days_back: int = Query(30, ge=1, le=365, description="Number of days for dashboard data"),
    execution_log_service: ReportExecutionLogService = Depends(get_report_execution_log_service)
):
    """Get comprehensive execution dashboard data for all reports."""
    try:
        # Get various metrics
        performance_data = execution_log_service.get_performance_dashboard(days_back)
        recent_failures = execution_log_service.get_failed_executions(10)
        trends = execution_log_service.get_execution_trends(min(days_back, 30))
        
        dashboard_data = {
            "overview": {
                "period_days": days_back,
                "total_executions": performance_data["total_executions"],
                "success_rate": performance_data["success_rate"],
                "average_execution_time": performance_data["average_execution_time_display"],
                "reports_executed": performance_data["reports_executed"]
            },
            "performance_metrics": performance_data,
            "trends": trends,
            "recent_failures": recent_failures,
            "alerts": {
                "high_failure_rate": performance_data["failure_rate"] > 10,
                "slow_executions": performance_data["average_execution_time_ms"] > 30000,  # 30 seconds
                "recent_failures_count": len(recent_failures)
            },
            "summary": {
                "healthiest_period": "Good" if performance_data["success_rate"] > 95 else "Needs Attention",
                "execution_volume": "High" if performance_data["total_executions"] > days_back * 10 else "Normal",
                "system_status": "Healthy" if performance_data["success_rate"] > 90 and len(recent_failures) < 5 else "Warning"
            }
        }
        
        return {
            "success": True,
            "data": dashboard_data,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "dashboard_version": "1.0"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating execution dashboard: {str(e)}")