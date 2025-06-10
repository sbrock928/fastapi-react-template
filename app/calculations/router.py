# app/calculations/router.py
"""Enhanced calculations router with support for multiple calculation types."""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union
from app.core.dependencies import get_db, get_query_engine
from app.core.exceptions import (
    CalculationNotFoundError,
    CalculationAlreadyExistsError,
    InvalidCalculationError,
)
from app.query import QueryEngine
from .service import CalculationService
from .schemas import (
    CalculationResponse,
    UserDefinedCalculationCreate,
    SystemSQLCalculationCreate,
    AvailableCalculation,
)
from .config import get_calculation_configuration

router = APIRouter()


def get_calculation_service(config_db: Session = Depends(get_db)) -> CalculationService:
    """Get calculation service for basic CRUD operations"""
    return CalculationService(config_db)


def get_calculation_service_with_preview(
    query_engine: QueryEngine = Depends(get_query_engine),
) -> CalculationService:
    """Get calculation service with query engine for preview operations"""
    return CalculationService(query_engine.config_db, query_engine)


# ===== CONFIGURATION ENDPOINTS =====


@router.get("/calculations/configuration")
def get_calculation_configuration_endpoint():
    """Get dynamically generated calculation configuration from SQLAlchemy models"""
    try:
        config = get_calculation_configuration()

        return {
            "success": True,
            "data": config,
            "message": "Calculation configuration retrieved successfully",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating calculation configuration: {str(e)}"
        )


# ===== UNIFIED RETRIEVAL ENDPOINTS =====


@router.get("/calculations", response_model=List[AvailableCalculation])
def get_available_calculations(
    service: CalculationService = Depends(get_calculation_service),
    group_level: Optional[str] = Query(
        None, description="Filter by group level: 'deal', 'tranche'"
    ),
    calculation_type: Optional[str] = Query(
        None, description="Filter by type: 'USER_DEFINED', 'SYSTEM_FIELD', 'SYSTEM_SQL'"
    ),
):
    """Get list of available calculations, optionally filtered by group level and/or type"""
    return service.get_available_calculations(group_level, calculation_type)


@router.get("/calculations/user-defined", response_model=List[AvailableCalculation])
def get_user_defined_calculations(
    service: CalculationService = Depends(get_calculation_service),
    group_level: Optional[str] = Query(
        None, description="Filter by group level: 'deal', 'tranche'"
    ),
):
    """Get only user-defined calculations"""
    return service.get_user_defined_calculations(group_level)


@router.get("/calculations/system", response_model=List[AvailableCalculation])
def get_system_calculations(
    service: CalculationService = Depends(get_calculation_service),
    group_level: Optional[str] = Query(
        None, description="Filter by group level: 'deal', 'tranche'"
    ),
):
    """Get only system-defined calculations (both field and SQL types)"""
    return service.get_system_calculations(group_level)


@router.get("/calculations/{calc_id}", response_model=CalculationResponse)
def get_calculation_by_id(
    calc_id: int, service: CalculationService = Depends(get_calculation_service)
):
    """Get a single calculation by ID"""
    calculation = service.get_calculation_by_id(calc_id)
    if not calculation:
        raise HTTPException(status_code=404, detail="Calculation not found")
    return calculation


# ===== USER DEFINED CALCULATION ENDPOINTS =====


@router.post("/calculations/user-defined", response_model=CalculationResponse, status_code=201)
def create_user_defined_calculation(
    request: UserDefinedCalculationCreate,
    service: CalculationService = Depends(get_calculation_service),
):
    """Create a new user-defined calculation"""
    try:
        return service.create_user_defined_calculation(request)
    except (CalculationAlreadyExistsError, InvalidCalculationError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/calculations/user-defined/{calc_id}", response_model=CalculationResponse)
def update_user_defined_calculation(
    calc_id: int,
    request: UserDefinedCalculationCreate,
    service: CalculationService = Depends(get_calculation_service),
):
    """Update an existing user-defined calculation"""
    try:
        return service.update_user_defined_calculation(calc_id, request)
    except CalculationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (CalculationAlreadyExistsError, InvalidCalculationError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===== SYSTEM SQL CALCULATION ENDPOINTS =====


@router.post("/calculations/system-sql", response_model=CalculationResponse, status_code=201)
def create_system_sql_calculation(
    request: SystemSQLCalculationCreate,
    service: CalculationService = Depends(get_calculation_service),
):
    """Create a new system SQL calculation (admin only)"""
    try:
        return service.create_system_sql_calculation(request)
    except (CalculationAlreadyExistsError, InvalidCalculationError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/calculations/system-sql/validate")
def validate_system_sql(
    sql_text: str = Body(..., embed=True),
    group_level: str = Body(..., embed=True),
    result_column_name: str = Body(..., embed=True),
    service: CalculationService = Depends(get_calculation_service),
):
    """Validate system SQL without saving"""
    try:
        result = service.validate_system_sql(sql_text, group_level, result_column_name)
        return {"success": True, "validation_result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")


# ===== PREVIEW AND USAGE ENDPOINTS =====


@router.get("/calculations/{calc_id}/preview-sql")
def preview_calculation_sql(
    calc_id: int,
    service: CalculationService = Depends(get_calculation_service_with_preview),
    aggregation_level: str = Query("deal", description="Aggregation level: 'deal' or 'tranche'"),
    sample_deals: str = Query("1001,1002,1003", description="Comma-separated sample deal numbers"),
    sample_tranches: str = Query("A,B", description="Comma-separated sample tranche IDs"),
    sample_cycle: int = Query(202404, description="Sample cycle code"),
):
    """Preview SQL for a calculation"""
    try:
        # Parse comma-separated values
        deal_list = [int(d.strip()) for d in sample_deals.split(",") if d.strip()]
        tranche_list = [t.strip() for t in sample_tranches.split(",") if t.strip()]

        return service.preview_calculation_sql(
            calc_id, aggregation_level, deal_list, tranche_list, sample_cycle
        )
    except CalculationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/calculations/{calc_id}/usage")
def get_calculation_usage(
    calc_id: int, service: CalculationService = Depends(get_calculation_service)
) -> Dict[str, Any]:
    """Get list of report templates that are using this calculation"""
    try:
        usage_info = service.get_calculation_usage_in_reports(calc_id)
        return {
            "calculation_id": calc_id,
            "is_in_use": len(usage_info) > 0,
            "report_count": len(usage_info),
            "reports": usage_info,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking calculation usage: {str(e)}")


# ===== DELETE ENDPOINT (USER-DEFINED ONLY) =====


@router.delete("/calculations/{calc_id}")
def delete_calculation(
    calc_id: int, service: CalculationService = Depends(get_calculation_service)
):
    """Delete a calculation (only user-defined calculations can be deleted)"""
    try:
        return service.delete_calculation(calc_id)
    except CalculationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidCalculationError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===== STATISTICS AND DEBUG ENDPOINTS =====


@router.get("/calculations/stats/counts")
def get_calculation_counts(service: CalculationService = Depends(get_calculation_service)):
    """Get calculation counts by type"""
    try:
        counts = service.dao.count_by_type()
        return {"success": True, "counts": counts, "total": sum(counts.values())}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving calculation counts: {str(e)}"
        )


# ===== DEBUG ENDPOINTS (DEVELOPMENT ONLY) =====


@router.get("/calculations/debug/model-fields/{model_name}")
def get_model_fields(model_name: str):
    """Debug endpoint to see all available fields for a model"""
    from .config import calculation_config_generator

    try:
        fields = calculation_config_generator.get_model_fields(model_name)
        exposed_fields = calculation_config_generator.model_registry.get(model_name, {}).get(
            "exposed_fields", []
        )

        return {
            "model_name": model_name,
            "all_available_fields": fields,
            "currently_exposed_fields": exposed_fields,
            "unexposed_fields": [f for f in fields if f not in exposed_fields],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error inspecting model: {str(e)}")
