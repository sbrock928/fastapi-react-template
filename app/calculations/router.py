# app/calculations/router.py
"""API router for the new separated calculation system"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.core.dependencies import get_db, get_dw_db
from app.core.exceptions import (
    CalculationNotFoundError,
    CalculationAlreadyExistsError,
    InvalidCalculationError,
)

from .service import (
    UserCalculationService,
    SystemCalculationService,
    StaticFieldService,
    CalculationConfigService,
    ReportExecutionService
)
from .resolver import CalculationRequest, QueryFilters
from .schemas import (
    UserCalculationCreate,
    UserCalculationUpdate, 
    UserCalculationResponse,
    SystemCalculationCreate,
    SystemCalculationResponse,
    StaticFieldInfo,
    CalculationConfigResponse,
    ReportExecutionRequest,
    ReportExecutionResponse,
    SQLPreviewResponse,
    CalculationUsageResponse,
    CalculationRequestSchema
)

router = APIRouter(prefix="/calculations", tags=["calculations"])


# ===== DEPENDENCY FUNCTIONS =====

def get_user_calculation_service(config_db: Session = Depends(get_db)) -> UserCalculationService:
    """Get user calculation service"""
    return UserCalculationService(config_db)


def get_system_calculation_service(config_db: Session = Depends(get_db)) -> SystemCalculationService:
    """Get system calculation service"""
    return SystemCalculationService(config_db)


def get_report_execution_service(
    config_db: Session = Depends(get_db),
    dw_db: Session = Depends(get_dw_db)
) -> ReportExecutionService:
    """Get report execution service"""
    return ReportExecutionService(dw_db, config_db)


# ===== CONFIGURATION ENDPOINTS =====

@router.get("/config", response_model=CalculationConfigResponse)
def get_calculation_configuration():
    """Get calculation configuration for UI"""
    return CalculationConfigResponse(
        aggregation_functions=CalculationConfigService.get_aggregation_functions(),
        source_models=CalculationConfigService.get_source_models(),
        group_levels=CalculationConfigService.get_group_levels(),
        static_fields=StaticFieldService.get_all_static_fields()
    )


# ===== STATIC FIELD ENDPOINTS =====

@router.get("/static-fields", response_model=List[StaticFieldInfo])
def get_static_fields(
    model: Optional[str] = Query(None, description="Filter by model name")
):
    """Get available static fields"""
    if model:
        return StaticFieldService.get_static_fields_by_model(model)
    return StaticFieldService.get_all_static_fields()


@router.get("/static-fields/{field_path:path}", response_model=StaticFieldInfo)
def get_static_field_by_path(field_path: str):
    """Get static field information by path"""
    field_info = StaticFieldService.get_static_field_by_path(field_path)
    if not field_info:
        raise HTTPException(status_code=404, detail=f"Static field '{field_path}' not found")
    return field_info


# ===== USER CALCULATION ENDPOINTS =====

@router.get("/user", response_model=List[UserCalculationResponse])
def get_user_calculations(
    group_level: Optional[str] = Query(None, description="Filter by group level"),
    service: UserCalculationService = Depends(get_user_calculation_service)
):
    """Get all user-defined calculations"""
    return service.get_all_user_calculations(group_level)


@router.get("/user/{calc_id}", response_model=UserCalculationResponse)
def get_user_calculation_by_id(
    calc_id: int,
    service: UserCalculationService = Depends(get_user_calculation_service)
):
    """Get a user calculation by ID"""
    calculation = service.get_user_calculation_by_id(calc_id)
    if not calculation:
        raise HTTPException(status_code=404, detail="User calculation not found")
    return calculation


@router.post("/user", response_model=UserCalculationResponse, status_code=201)
def create_user_calculation(
    request: UserCalculationCreate,
    service: UserCalculationService = Depends(get_user_calculation_service)
):
    """Create a new user-defined calculation"""
    try:
        return service.create_user_calculation(request)
    except (CalculationAlreadyExistsError, InvalidCalculationError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/user/{calc_id}", response_model=UserCalculationResponse)
def update_user_calculation(
    calc_id: int,
    request: UserCalculationUpdate,
    service: UserCalculationService = Depends(get_user_calculation_service)
):
    """Update an existing user calculation"""
    try:
        return service.update_user_calculation(calc_id, request)
    except CalculationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (CalculationAlreadyExistsError, InvalidCalculationError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/user/{calc_id}")
def delete_user_calculation(
    calc_id: int,
    service: UserCalculationService = Depends(get_user_calculation_service)
):
    """Delete a user calculation"""
    try:
        return service.delete_user_calculation(calc_id)
    except CalculationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidCalculationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/user/{calc_id}/usage", response_model=CalculationUsageResponse)
def get_user_calculation_usage(
    calc_id: int,
    service: UserCalculationService = Depends(get_user_calculation_service)
):
    """Get usage information for a user calculation"""
    try:
        return service.get_user_calculation_usage(calc_id)
    except CalculationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===== SYSTEM CALCULATION ENDPOINTS =====

@router.get("/system", response_model=List[SystemCalculationResponse])
def get_system_calculations(
    group_level: Optional[str] = Query(None, description="Filter by group level"),
    approved_only: bool = Query(False, description="Only return approved calculations"),
    service: SystemCalculationService = Depends(get_system_calculation_service)
):
    """Get all system-defined calculations"""
    return service.get_all_system_calculations(group_level)


@router.get("/system/{calc_id}", response_model=SystemCalculationResponse)
def get_system_calculation_by_id(
    calc_id: int,
    service: SystemCalculationService = Depends(get_system_calculation_service)
):
    """Get a system calculation by ID"""
    calculation = service.get_system_calculation_by_id(calc_id)
    if not calculation:
        raise HTTPException(status_code=404, detail="System calculation not found")
    return calculation


@router.post("/system", response_model=SystemCalculationResponse, status_code=201)
def create_system_calculation(
    request: SystemCalculationCreate,
    service: SystemCalculationService = Depends(get_system_calculation_service)
):
    """Create a new system-defined calculation (admin only)"""
    try:
        return service.create_system_calculation(request)
    except (CalculationAlreadyExistsError, InvalidCalculationError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/system/{calc_id}/approve", response_model=SystemCalculationResponse)
def approve_system_calculation(
    calc_id: int,
    approved_by: str = Body(..., embed=True),
    service: SystemCalculationService = Depends(get_system_calculation_service)
):
    """Approve a system calculation"""
    try:
        return service.approve_system_calculation(calc_id, approved_by)
    except CalculationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/system/{calc_id}")
def delete_system_calculation(
    calc_id: int,
    service: SystemCalculationService = Depends(get_system_calculation_service)
):
    """Delete a system calculation"""
    try:
        return service.delete_system_calculation(calc_id)
    except CalculationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidCalculationError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===== REPORT EXECUTION ENDPOINTS =====

@router.post("/execute-report", response_model=ReportExecutionResponse)
def execute_report(
    request: ReportExecutionRequest,
    service: ReportExecutionService = Depends(get_report_execution_service)
):
    """Execute a report with mixed calculation types"""
    try:
        # Convert schema requests to resolver requests
        calc_requests = []
        for req_schema in request.calculation_requests:
            calc_request = CalculationRequest(
                calc_type=req_schema.calc_type,
                calc_id=req_schema.calc_id,
                field_path=req_schema.field_path,
                alias=req_schema.alias
            )
            calc_requests.append(calc_request)

        result = service.execute_report(
            calc_requests,
            request.deal_tranche_map,
            request.cycle_code
        )
        
        return ReportExecutionResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing report: {str(e)}")


@router.post("/preview-sql", response_model=SQLPreviewResponse)
def preview_report_sql(
    request: ReportExecutionRequest,
    service: ReportExecutionService = Depends(get_report_execution_service)
):
    """Preview SQL for a report without executing it"""
    try:
        # Convert schema requests to resolver requests
        calc_requests = []
        for req_schema in request.calculation_requests:
            calc_request = CalculationRequest(
                calc_type=req_schema.calc_type,
                calc_id=req_schema.calc_id,
                field_path=req_schema.field_path,
                alias=req_schema.alias
            )
            calc_requests.append(calc_request)

        result = service.preview_report_sql(
            calc_requests,
            request.deal_tranche_map,
            request.cycle_code
        )
        
        return SQLPreviewResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error previewing SQL: {str(e)}")


# ===== INDIVIDUAL CALCULATION PREVIEW =====

@router.post("/preview-single")
def preview_single_calculation(
    calculation_request: CalculationRequestSchema,
    deal_tranche_map: Dict[int, List[str]] = Body(...),
    cycle_code: int = Body(...),
    service: ReportExecutionService = Depends(get_report_execution_service)
):
    """Preview SQL for a single calculation"""
    try:
        calc_request = CalculationRequest(
            calc_type=calculation_request.calc_type,
            calc_id=calculation_request.calc_id,
            field_path=calculation_request.field_path,
            alias=calculation_request.alias
        )

        filters = QueryFilters(deal_tranche_map, cycle_code)
        query_result = service.resolver.resolve_single_calculation(calc_request, filters)
        
        return {
            "sql": query_result.sql,
            "columns": query_result.columns,
            "calculation_type": query_result.calc_type,
            "group_level": query_result.group_level,
            "parameters": {
                "deal_tranche_map": deal_tranche_map,
                "cycle_code": cycle_code
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error previewing calculation: {str(e)}")


# ===== STATISTICS ENDPOINTS =====

@router.get("/stats/counts")
def get_calculation_counts(
    user_service: UserCalculationService = Depends(get_user_calculation_service),
    system_service: SystemCalculationService = Depends(get_system_calculation_service)
):
    """Get calculation counts by type"""
    try:
        user_calcs = user_service.get_all_user_calculations()
        system_calcs = system_service.get_all_system_calculations()
        
        return {
            "success": True,
            "counts": {
                "user_calculations": len(user_calcs),
                "system_calculations": len(system_calcs),
                "total": len(user_calcs) + len(system_calcs)
            },
            "breakdown": {
                "user_by_group_level": {
                    "deal": len([c for c in user_calcs if c.group_level.value == "deal"]),
                    "tranche": len([c for c in user_calcs if c.group_level.value == "tranche"])
                },
                "system_by_group_level": {
                    "deal": len([c for c in system_calcs if c.group_level.value == "deal"]),
                    "tranche": len([c for c in system_calcs if c.group_level.value == "tranche"])
                },
                "system_by_approval": {
                    "approved": len([c for c in system_calcs if c.is_approved()]),
                    "pending": len([c for c in system_calcs if not c.is_approved()])
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving calculation counts: {str(e)}")


# ===== LEGACY COMPATIBILITY ENDPOINTS (for migration) =====

@router.get("/legacy/all")
def get_all_calculations_legacy_format(
    user_service: UserCalculationService = Depends(get_user_calculation_service),
    system_service: SystemCalculationService = Depends(get_system_calculation_service)
):
    """Get all calculations in legacy format for migration compatibility"""
    user_calcs = user_service.get_all_user_calculations()
    system_calcs = system_service.get_all_system_calculations()
    static_fields = StaticFieldService.get_all_static_fields()
    
    # Convert to legacy format
    legacy_calculations = []
    
    # Add user calculations
    for calc in user_calcs:
        legacy_calculations.append({
            "id": calc.id,
            "name": calc.name,
            "description": calc.description,
            "calculation_type": "USER_DEFINED",
            "group_level": calc.group_level.value,
            "aggregation_function": calc.aggregation_function.value,
            "source_model": calc.source_model.value,
            "source_field": calc.source_field,
            "weight_field": calc.weight_field,
            "display_type": calc.get_display_type(),
            "source_description": calc.get_source_description(),
            "is_system_managed": False,
            "created_at": calc.created_at,
            "created_by": calc.created_by
        })
    
    # Add system calculations
    for calc in system_calcs:
        legacy_calculations.append({
            "id": calc.id,
            "name": calc.name,
            "description": calc.description,
            "calculation_type": "SYSTEM_SQL",
            "group_level": calc.group_level.value,
            "raw_sql": calc.raw_sql,
            "result_column_name": calc.result_column_name,
            "display_type": calc.get_display_type(),
            "source_description": calc.get_source_description(),
            "is_system_managed": True,
            "created_at": calc.created_at,
            "created_by": calc.created_by
        })
    
    # Add static fields as legacy calculations
    for field in static_fields:
        legacy_calculations.append({
            "id": f"static_{field.field_path}",  # Fake ID for compatibility
            "name": field.name,
            "description": field.description,
            "calculation_type": "SYSTEM_FIELD",
            "group_level": "tranche" if field.field_path.startswith(("tranche.", "tranchebal.")) else "deal",
            "field_path": field.field_path,
            "field_type": field.type,
            "display_type": f"Static Field ({field.type})",
            "source_description": field.field_path,
            "is_system_managed": True,
            "created_at": None,
            "created_by": "system"
        })
    
    return legacy_calculations


# ===== HEALTH CHECK =====

@router.get("/health")
def calculation_system_health():
    """Health check for the calculation system"""
    return {
        "status": "healthy",
        "system": "new_separated_calculations",
        "features": [
            "user_calculations",
            "system_calculations", 
            "static_fields",
            "individual_sql_queries",
            "in_memory_merging",
            "future_expansion_ready"
        ]
    }