"""API router for the reporting module."""

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
    AvailableField,
    ReportScope,
)
from app.core.dependencies import SessionDep, DWSessionDep
from app.datawarehouse.dao import DatawarehouseDAO


router = APIRouter(prefix="/reports", tags=["reporting"])


# Dependency functions
async def get_report_dao(db: SessionDep) -> ReportDAO:
    return ReportDAO(db)


async def get_dw_dao(db: DWSessionDep) -> DatawarehouseDAO:
    return DatawarehouseDAO(db)


async def get_report_service(
    report_dao: ReportDAO = Depends(get_report_dao),
    dw_dao: DatawarehouseDAO = Depends(get_dw_dao),
) -> ReportService:
    return ReportService(report_dao, dw_dao)


# ===== REPORT CONFIGURATION ENDPOINTS =====


@router.get("/", response_model=List[ReportRead])
async def get_all_reports(service: ReportService = Depends(get_report_service)) -> List[ReportRead]:
    """Get all report configurations."""
    return await service.get_all()


@router.get("/summary", response_model=List[ReportSummary])
async def get_all_reports_summary(
    service: ReportService = Depends(get_report_service),
) -> List[ReportSummary]:
    """Get all reports with summary information."""
    return await service.get_all_summaries()


@router.get("/{report_id}", response_model=ReportRead)
async def get_report_by_id(
    report_id: int, service: ReportService = Depends(get_report_service)
) -> ReportRead:
    """Get a specific report configuration by ID."""
    report = await service.get_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("/", response_model=ReportRead)
async def create_report(
    report_data: ReportCreate, service: ReportService = Depends(get_report_service)
) -> ReportRead:
    """Create a new report configuration."""
    return await service.create(report_data)


@router.patch("/{report_id}", response_model=ReportRead)
async def update_report(
    report_id: int, report_data: ReportUpdate, service: ReportService = Depends(get_report_service)
) -> ReportRead:
    """Update an existing report configuration."""
    report = await service.update(report_id, report_data)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.delete("/{report_id}")
async def delete_report(
    report_id: int, service: ReportService = Depends(get_report_service)
) -> Dict[str, str]:
    """Delete a report configuration."""
    success = await service.delete(report_id)
    if not success:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"message": "Report deleted successfully"}


# ===== REPORT EXECUTION ENDPOINTS =====


@router.post("/run", response_model=List[Dict[str, Any]])
async def run_report(
    request: RunReportRequest, service: ReportService = Depends(get_report_service)
) -> List[Dict[str, Any]]:
    """Run a saved report configuration."""
    return await service.run_saved_report(request.report_id, request.cycle_code)


@router.post("/run/{report_id}", response_model=List[Dict[str, Any]])
async def run_report_by_id(
    report_id: int, request: Dict[str, Any], service: ReportService = Depends(get_report_service)
) -> List[Dict[str, Any]]:
    """Run a saved report by ID with cycle parameter."""
    cycle_code = request.get("cycle_code")
    if not cycle_code:
        raise HTTPException(status_code=400, detail="cycle_code is required")
    return await service.run_saved_report(report_id, cycle_code)


@router.get("/{report_id}/schema", response_model=Dict[str, Any])
async def get_report_schema(
    report_id: int, service: ReportService = Depends(get_report_service)
) -> Dict[str, Any]:
    """Get the schema/structure of a saved report for skeleton preview."""
    return await service.get_report_schema(report_id)


# ===== FIELD CONFIGURATION ENDPOINTS =====


@router.get("/fields/available", response_model=List[AvailableField])
async def get_available_fields(
    scope: ReportScope, service: ReportService = Depends(get_report_service)
) -> List[AvailableField]:
    """Get available fields for report configuration based on scope."""
    return await service.get_available_fields(scope)


# ===== DATA ENDPOINTS (for report building) =====


@router.get("/data/deals", response_model=List[Dict[str, Any]])
async def get_available_deals(
    service: ReportService = Depends(get_report_service),
) -> List[Dict[str, Any]]:
    """Get available deals for report building."""
    deals = await service.get_available_deals()
    return [deal.model_dump() for deal in deals]


@router.post("/data/tranches", response_model=Dict[int, List[Dict[str, Any]]])
async def get_available_tranches(
    request: Dict[str, Any], service: ReportService = Depends(get_report_service)
) -> Dict[int, List[Dict[str, Any]]]:
    """Get available tranches for specific deals."""
    dl_nbrs = request.get("dl_nbrs", [])
    cycle_code = request.get("cycle_code")

    tranches_by_deal = await service.get_available_tranches_for_deals(dl_nbrs, cycle_code)
    # Convert string keys to integers and return the dictionaries directly
    return {
        int(deal_id): tranches  # tranches are already dictionaries, no need for model_dump()
        for deal_id, tranches in tranches_by_deal.items()
    }


@router.get("/data/cycles", response_model=List[Dict[str, Any]])
async def get_available_cycles(
    service: ReportService = Depends(get_report_service),
) -> List[Dict[str, Any]]:
    """Get available cycle codes from the data warehouse."""
    return await service.get_available_cycles()


# ===== EXPORT ENDPOINTS =====


@router.post("/export-xlsx")
async def export_to_xlsx(request: Dict[str, Any]) -> Response:
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
