"""API router for the reporting module."""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from app.reporting.service import ReportService
from app.reporting.dao import ReportDAO, ReportingDAO
from app.reporting.schemas import (
    ReportRead,
    ReportCreate,
    ReportUpdate,
    ReportSummary,
    RunReportRequest,
)
from app.core.dependencies import SessionDep, DWSessionDep
from app.datawarehouse.dao import DealDAO, TrancheDAO


router = APIRouter(prefix="/reports", tags=["reporting"])


# Dependency functions
async def get_report_dao(db: SessionDep) -> ReportDAO:
    return ReportDAO(db)


async def get_reporting_dao(db: DWSessionDep) -> ReportingDAO:
    return ReportingDAO(db)


async def get_deal_dao(db: DWSessionDep) -> DealDAO:
    return DealDAO(db)


async def get_tranche_dao(db: DWSessionDep) -> TrancheDAO:
    return TrancheDAO(db)


async def get_report_service(
    report_dao: ReportDAO = Depends(get_report_dao),
    deal_dao: DealDAO = Depends(get_deal_dao),
    tranche_dao: TrancheDAO = Depends(get_tranche_dao),
) -> ReportService:
    return ReportService(report_dao, deal_dao, tranche_dao)


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
    report_id: int, request: Dict[str, str], service: ReportService = Depends(get_report_service)
) -> List[Dict[str, Any]]:
    """Run a saved report by ID with cycle parameter."""
    cycle_code = request.get("cycle_code")
    if not cycle_code:
        raise HTTPException(status_code=400, detail="cycle_code is required")
    return await service.run_saved_report(report_id, cycle_code)


# ===== DATA ENDPOINTS (for report building) =====


@router.get("/data/deals", response_model=List[Dict[str, Any]])
async def get_available_deals(
    cycle_code: Optional[str] = None, service: ReportService = Depends(get_report_service)
) -> List[Dict[str, Any]]:
    """Get available deals for report building."""
    deals = await service.get_available_deals(cycle_code)
    return [deal.model_dump() for deal in deals]


@router.post("/data/tranches", response_model=Dict[int, List[Dict[str, Any]]])
async def get_available_tranches(
    request: Dict[str, Any], service: ReportService = Depends(get_report_service)
) -> Dict[int, List[Dict[str, Any]]]:
    """Get available tranches for specific deals."""
    deal_ids = request.get("deal_ids", [])
    cycle_code = request.get("cycle_code")

    tranches_by_deal = await service.get_available_tranches_for_deals(deal_ids, cycle_code)
    return {
        deal_id: [tranche.model_dump() for tranche in tranches]
        for deal_id, tranches in tranches_by_deal.items()
    }


@router.get("/data/cycles", response_model=List[Dict[str, str]])
async def get_available_cycles(
    reporting_dao: ReportingDAO = Depends(get_reporting_dao),
) -> List[Dict[str, str]]:
    """Get available cycle codes from the data warehouse."""
    # Return dummy cycle data for now
    dummy_cycles = [
        {"code": "2024Q1", "label": "2024Q1 (Quarter 1 2024)"},
        {"code": "2024Q2", "label": "2024Q2 (Quarter 2 2024)"},
        {"code": "2024Q3", "label": "2024Q3 (Quarter 3 2024)"},
        {"code": "2024Q4", "label": "2024Q4 (Quarter 4 2024)"},
        {"code": "2025Q1", "label": "2025Q1 (Quarter 1 2025)"},
    ]
    return dummy_cycles
