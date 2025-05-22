"""API router for the reporting module with dual database support."""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Dict, Any, Optional, Annotated

from app.core.dependencies import SessionDep, DWSessionDep
from app.reporting.schemas import (
    ReportRead, ReportCreate, ReportUpdate, ReportSummary, RunReportRequest
)
from app.datawarehouse.schemas import DealRead, TrancheRead
from app.reporting.service import ReportService
from app.reporting.dao import ReportDAO
from app.datawarehouse.dao import DealDAO, TrancheDAO

router = APIRouter(prefix="/reports", tags=["Reports"])


# Dependency factories
def get_report_service(
    config_session: SessionDep, 
    dw_session: DWSessionDep
) -> ReportService:
    """Create ReportService with both database sessions."""
    return ReportService(
        ReportDAO(config_session),
        DealDAO(dw_session),
        TrancheDAO(dw_session)
    )


def get_deal_dao(dw_session: DWSessionDep) -> DealDAO:
    """Create DealDAO with data warehouse session."""
    return DealDAO(dw_session)


def get_tranche_dao(dw_session: DWSessionDep) -> TrancheDAO:
    """Create TrancheDAO with data warehouse session."""
    return TrancheDAO(dw_session)


# Type aliases for dependencies
ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]
DealDAODep = Annotated[DealDAO, Depends(get_deal_dao)]
TrancheDAODep = Annotated[TrancheDAO, Depends(get_tranche_dao)]


# --- Legacy Compatibility Routes (MUST come first!) ---

@router.get("/configurations", response_model=Dict[str, Any])
async def get_report_configurations_legacy() -> Dict[str, Any]:
    """Legacy endpoint for backward compatibility with existing frontend."""
    # This maintains compatibility with your existing ReportingTable component
    # while the new system is being implemented
    return {
        "deal_level_report": {
            "apiEndpoint": "/reports/run",
            "title": "Deal Level Report",
            "columns": [
                {"field": "deal_name", "header": "Deal Name", "type": "text"},
                {"field": "originator", "header": "Originator", "type": "text"},
                {"field": "total_principal", "header": "Total Principal", "type": "number"},
                {"field": "credit_rating", "header": "Credit Rating", "type": "text"},
                {"field": "yield_rate", "header": "Yield Rate", "type": "percentage"},
                {"field": "tranche_count", "header": "Tranche Count", "type": "number"},
            ]
        },
        "tranche_level_report": {
            "apiEndpoint": "/reports/run",
            "title": "Tranche Level Report", 
            "columns": [
                {"field": "deal_name", "header": "Deal Name", "type": "text"},
                {"field": "tranche_name", "header": "Tranche Name", "type": "text"},
                {"field": "class_name", "header": "Class", "type": "text"},
                {"field": "principal_amount", "header": "Principal Amount", "type": "number"},
                {"field": "interest_rate", "header": "Interest Rate", "type": "percentage"},
                {"field": "credit_rating", "header": "Credit Rating", "type": "text"},
            ]
        }
    }


@router.get("/cycle-codes", response_model=List[Dict[str, str]])
async def get_cycle_codes_legacy(deal_dao: DealDAODep) -> List[Dict[str, str]]:
    """Legacy endpoint for cycle codes - matches existing frontend expectations."""
    # This matches the exact format your existing frontend expects
    return [
        {"code": "2024-01", "label": "January 2024"},
        {"code": "2024-02", "label": "February 2024"},
        {"code": "2024-03", "label": "March 2024"},
        {"code": "2024-04", "label": "April 2024"},
    ]


# --- Report Configuration Routes ---

@router.get("/", response_model=List[ReportRead])
async def get_all_reports(service: ReportServiceDep) -> List[ReportRead]:
    """Get all report configurations."""
    return await service.get_all()


@router.get("/{report_id}", response_model=ReportRead)
async def get_report_by_id(report_id: int, service: ReportServiceDep) -> ReportRead:
    """Get a report configuration by ID."""
    report = await service.get_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/user/{created_by}", response_model=List[ReportSummary])
async def get_user_reports(created_by: str, service: ReportServiceDep) -> List[ReportSummary]:
    """Get report configurations for a specific user."""
    return await service.get_by_created_by(created_by)


@router.post("/", response_model=ReportRead)
async def create_report(report_data: ReportCreate, service: ReportServiceDep) -> ReportRead:
    """Create a new report configuration."""
    return await service.create(report_data)


@router.patch("/{report_id}", response_model=ReportRead)
async def update_report(
    report_id: int, report_data: ReportUpdate, service: ReportServiceDep
) -> ReportRead:
    """Update a report configuration."""
    report = await service.update(report_id, report_data)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.delete("/{report_id}")
async def delete_report(report_id: int, service: ReportServiceDep) -> Dict[str, str]:
    """Delete a report configuration."""
    result = await service.delete(report_id)
    if not result:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"message": "Report deleted successfully"}


# --- Report Execution Routes ---

@router.post("/run")
async def run_report(
    request: RunReportRequest, service: ReportServiceDep
) -> List[Dict[str, Any]]:
    """Run a saved report configuration."""
    return await service.run_saved_report(request.report_id, request.cycle_code)


@router.post("/run/{report_id}")
async def run_report_by_id(
    report_id: int, 
    service: ReportServiceDep,
    params: Dict[str, Any] = Body(...)
) -> List[Dict[str, Any]]:
    """Run a saved report by ID with cycle parameter."""
    cycle_code = params.get("cycle_code")
    if not cycle_code:
        raise HTTPException(status_code=400, detail="cycle_code is required")
    
    return await service.run_saved_report(report_id, cycle_code)


# --- Data Warehouse Query Routes (for report building) ---

@router.get("/data/deals", response_model=List[DealRead])
async def get_available_deals(
    service: ReportServiceDep,
    cycle_code: Optional[str] = None
) -> List[DealRead]:
    """Get available deals for report building."""
    return await service.get_available_deals(cycle_code)


@router.post("/data/tranches", response_model=Dict[int, List[TrancheRead]])
async def get_tranches_for_deals(
    service: ReportServiceDep,
    deal_ids: List[int] = Body(...),
    cycle_code: Optional[str] = Body(None)
) -> Dict[int, List[TrancheRead]]:
    """Get available tranches for specific deals."""
    if not deal_ids:
        raise HTTPException(status_code=400, detail="deal_ids cannot be empty")
    
    return await service.get_available_tranches_for_deals(deal_ids, cycle_code)


@router.get("/data/deals/{deal_id}/tranches", response_model=List[TrancheRead])
async def get_deal_tranches(
    deal_id: int,
    tranche_dao: TrancheDAODep,
    cycle_code: Optional[str] = None
) -> List[TrancheRead]:
    """Get tranches for a specific deal."""
    tranches = await tranche_dao.get_by_deal_id(deal_id, cycle_code)
    return [TrancheRead.model_validate(tranche) for tranche in tranches]


# --- Statistics and Metadata Routes ---

@router.get("/stats/summary")
async def get_report_statistics(
    deal_dao: DealDAODep,
    tranche_dao: TrancheDAODep,
    config_session: SessionDep
) -> Dict[str, Any]:
    """Get summary statistics for the reporting dashboard."""
    from app.reporting.dao import ReportDAO
    
    report_dao = ReportDAO(config_session)
    
    deal_count = await deal_dao.get_deal_count()
    tranche_count = await tranche_dao.get_tranche_count()
    report_count = await report_dao.get_report_count()
    
    return {
        "total_deals": deal_count,
        "total_tranches": tranche_count,
        "total_reports": report_count,
        "timestamp": "2024-01-01T00:00:00"  # You'd use actual timestamp
    }


@router.get("/data/cycles")
async def get_available_cycles(deal_dao: DealDAODep) -> List[Dict[str, str]]:
    """Get available cycle codes from the data warehouse."""
    # This would be a more sophisticated query in real implementation
    # For now, return some sample cycles
    return [
        {"code": "2024-01", "label": "January 2024"},
        {"code": "2024-02", "label": "February 2024"},
        {"code": "2024-03", "label": "March 2024"},
        {"code": "2024-04", "label": "April 2024"},
    ]

@router.get("/columns/{scope}")
async def get_available_columns(scope: str) -> Dict[str, List[Dict[str, Any]]]:
    """Get available columns for a report scope."""
    from app.reporting.column_registry import get_columns_by_category, ColumnScope
    
    try:
        scope_enum = ColumnScope(scope.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scope")
    
    categories = get_columns_by_category(scope_enum)
    
    # Convert to API response format
    result = {}
    for category, columns in categories.items():
        result[category] = [
            {
                "key": col.key,
                "label": col.label,
                "description": col.description,
                "column_type": col.column_type,
                "data_type": col.data_type,
                "is_default": col.is_default,
                "sort_order": col.sort_order
            }
            for col in columns
        ]
    
    return result

@router.get("/columns/{scope}/defaults")
async def get_default_columns(scope: str) -> List[str]:
    """Get default column keys for a scope."""
    from app.reporting.column_registry import get_default_columns, ColumnScope
    
    try:
        scope_enum = ColumnScope(scope.upper())
        return get_default_columns(scope_enum)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scope")
    


    """Additional router endpoints for tranche overrides.

Add these endpoints to app/reporting/router.py
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Dict, Any
from app.core.dependencies import SessionDep
from app.reporting.dao import OverrideDAO
from app.reporting.schemas import (
    TrancheOverrideRead, TrancheOverrideCreate, TrancheOverrideUpdate,
    BulkOverrideRequest, OverrideSummary, OverrideableColumn
)
from app.reporting.overrideable_columns import (
    get_overrideable_columns_for_scope, get_override_categories
)
from app.reporting.service_extensions import extend_report_service_with_overrides


# Dependency factory for OverrideDAO
def get_override_dao(session: SessionDep) -> OverrideDAO:
    """Create OverrideDAO with session."""
    return OverrideDAO(session)


# Update the get_report_service dependency to include override functionality
def get_enhanced_report_service(
    config_session: SessionDep, 
    dw_session: DWSessionDep
) -> ReportService:
    """Create ReportService with override functionality."""
    from app.reporting.service import ReportService
    from app.reporting.dao import ReportDAO
    from app.datawarehouse.dao import DealDAO, TrancheDAO
    
    base_service = ReportService(
        ReportDAO(config_session),
        DealDAO(dw_session),
        TrancheDAO(dw_session)
    )
    
    # Extend with override functionality
    override_dao = OverrideDAO(config_session)
    return extend_report_service_with_overrides(base_service, override_dao)


# --- Override Management Routes ---

@router.get("/{report_id}/overrides", response_model=List[TrancheOverrideRead])
async def get_report_overrides(
    report_id: int, 
    service: ReportService = Depends(get_enhanced_report_service)
) -> List[TrancheOverrideRead]:
    """Get all overrides for a report."""
    return await service.get_report_overrides(report_id)


@router.get("/{report_id}/overrides/summary", response_model=OverrideSummary)
async def get_override_summary(
    report_id: int,
    service: ReportService = Depends(get_enhanced_report_service)
) -> OverrideSummary:
    """Get summary statistics for report overrides."""
    return await service.get_override_summary(report_id)


@router.get("/{report_id}/overrides/tranche/{tranche_id}", response_model=List[TrancheOverrideRead])
async def get_tranche_overrides(
    report_id: int,
    tranche_id: int,
    service: ReportService = Depends(get_enhanced_report_service)
) -> List[TrancheOverrideRead]:
    """Get all overrides for a specific tranche."""
    return await service.get_tranche_overrides(report_id, tranche_id)


@router.post("/{report_id}/overrides", response_model=TrancheOverrideRead)
async def set_tranche_override(
    report_id: int,
    override_data: TrancheOverrideCreate,
    service: ReportService = Depends(get_enhanced_report_service)
) -> TrancheOverrideRead:
    """Set or update a tranche override."""
    return await service.set_tranche_override(report_id, override_data)


@router.patch("/{report_id}/overrides/{tranche_id}/{column_name}", response_model=TrancheOverrideRead)
async def update_tranche_override(
    report_id: int,
    tranche_id: int,
    column_name: str,
    update_data: TrancheOverrideUpdate,
    service: ReportService = Depends(get_enhanced_report_service)
) -> TrancheOverrideRead:
    """Update an existing override."""
    updated = await service.update_tranche_override(report_id, tranche_id, column_name, update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Override not found")
    return updated


@router.delete("/{report_id}/overrides/{tranche_id}/{column_name}")
async def clear_tranche_override(
    report_id: int,
    tranche_id: int,
    column_name: str,
    service: ReportService = Depends(get_enhanced_report_service)
) -> Dict[str, str]:
    """Clear a specific override."""
    result = await service.clear_tranche_override(report_id, tranche_id, column_name)
    if not result:
        raise HTTPException(status_code=404, detail="Override not found")
    return {"message": "Override cleared successfully"}


@router.delete("/{report_id}/overrides")
async def clear_all_report_overrides(
    report_id: int,
    service: ReportService = Depends(get_enhanced_report_service)
) -> Dict[str, Any]:
    """Clear all overrides for a report."""
    count = await service.clear_all_overrides_for_report(report_id)
    return {"message": f"Cleared {count} overrides"}


@router.delete("/{report_id}/overrides/tranche/{tranche_id}")
async def clear_tranche_overrides(
    report_id: int,
    tranche_id: int,
    service: ReportService = Depends(get_enhanced_report_service)
) -> Dict[str, Any]:
    """Clear all overrides for a specific tranche."""
    count = await service.clear_all_overrides_for_tranche(report_id, tranche_id)
    return {"message": f"Cleared {count} overrides for tranche {tranche_id}"}


@router.post("/{report_id}/overrides/bulk", response_model=List[TrancheOverrideRead])
async def bulk_set_overrides(
    report_id: int,
    bulk_request: BulkOverrideRequest,
    service: ReportService = Depends(get_enhanced_report_service)
) -> List[TrancheOverrideRead]:
    """Set multiple overrides in bulk."""
    return await service.bulk_set_overrides(report_id, bulk_request)


@router.get("/{report_id}/overrides/template")
async def export_overrides_template(
    report_id: int,
    service: ReportService = Depends(get_enhanced_report_service)
) -> List[Dict[str, Any]]:
    """Export override template for bulk editing."""
    return await service.export_overrides_template(report_id)


# --- Override Column Configuration Routes ---

@router.get("/overrides/columns/{scope}", response_model=List[OverrideableColumn])
async def get_overrideable_columns(scope: str) -> List[OverrideableColumn]:
    """Get columns that support overrides for a specific scope."""
    if scope.upper() not in ["DEAL", "TRANCHE"]:
        raise HTTPException(status_code=400, detail="Invalid scope. Must be DEAL or TRANCHE")
    
    return get_overrideable_columns_for_scope(scope)


@router.get("/overrides/columns/{scope}/categories")
async def get_overrideable_columns_by_category(scope: str) -> Dict[str, List[OverrideableColumn]]:
    """Get overrideable columns grouped by category."""
    if scope.upper() not in ["DEAL", "TRANCHE"]:
        raise HTTPException(status_code=400, detail="Invalid scope. Must be DEAL or TRANCHE")
    
    return get_override_categories(scope)


# --- Override Import/Export Routes ---

@router.post("/{report_id}/overrides/import")
async def import_overrides_from_csv(
    report_id: int,
    csv_data: str = Body(..., media_type="text/csv"),
    replace_existing: bool = Query(False, description="Replace all existing overrides"),
    service: ReportService = Depends(get_enhanced_report_service)
) -> Dict[str, Any]:
    """Import overrides from CSV data."""
    try:
        import csv
        import io
        
        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(csv_data))
        override_requests = []
        
        for row in csv_reader:
            if row.get('override_value') and row.get('override_value').strip():
                override_req = TrancheOverrideCreate(
                    tranche_id=int(row['tranche_id']),
                    column_name=row['column_name'],
                    override_value=row['override_value'],
                    override_type=row.get('override_type', 'manual'),
                    notes=row.get('notes', ''),
                    created_by='import_user'  # TODO: Get from auth context
                )
                override_requests.append(override_req)
        
        # Bulk import
        bulk_request = BulkOverrideRequest(
            overrides=override_requests,
            replace_existing=replace_existing
        )
        
        imported_overrides = await service.bulk_set_overrides(report_id, bulk_request)
        
        return {
            "message": f"Successfully imported {len(imported_overrides)} overrides",
            "imported_count": len(imported_overrides),
            "replaced_existing": replace_existing
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"CSV import failed: {str(e)}")


@router.get("/{report_id}/overrides/export.csv")
async def export_overrides_to_csv(
    report_id: int,
    service: ReportService = Depends(get_enhanced_report_service)
) -> Dict[str, Any]:
    """Export overrides template as CSV."""
    try:
        import csv
        import io
        
        template_data = await service.export_overrides_template(report_id)
        
        # Generate CSV
        output = io.StringIO()
        if template_data:
            fieldnames = template_data[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(template_data)
        
        csv_content = output.getvalue()
        
        return {
            "csv_content": csv_content,
            "filename": f"report_{report_id}_overrides_template.csv",
            "row_count": len(template_data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV export failed: {str(e)}")