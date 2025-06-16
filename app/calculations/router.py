# app/calculations/router.py
"""Clean API router for the separated calculation system"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from urllib.parse import unquote
import time
from app.core.dependencies import get_db, get_dw_db, get_user_calculation_dao, get_system_calculation_dao

from .service import (
    UserCalculationService,
    SystemCalculationService,
    StaticFieldService,
    CalculationConfigService,
    ReportExecutionService
)
from .cdi_service import CDIVariableCalculationService
from .cdi_schemas import (
    CDIVariableCreate, 
    CDIVariableUpdate, 
    CDIVariableResponse,
    CDIVariableExecutionRequest,
    CDIVariableExecutionResponse,
    CDIVariableConfigResponse,
    CDIVariableSummary,
    CDIVariableValidationRequest,
    CDIVariableValidationResponse,
    CDIVariableBulkCreateRequest,
    CDIVariableBulkCreateResponse
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
    CalculationRequestSchema,
    UserCalculationRead,
    SystemCalculationRead,
    StaticFieldRead,
    UserCalculationStats,
    SystemCalculationStats,
    CalculationConfigRead,
    CalculationExecutionRequest,
    CalculationExecutionResponse,
    CalculationExecutionSQLResponse,
    SystemCalculationUpdate
)

router = APIRouter(prefix="/calculations", tags=["calculations"])


# ===== DEPENDENCY FUNCTIONS =====

def get_user_calculation_service(user_calc_dao = Depends(get_user_calculation_dao)) -> UserCalculationService:
    """Get user calculation service"""
    return UserCalculationService(user_calc_dao)


def get_system_calculation_service(system_calc_dao = Depends(get_system_calculation_dao)) -> SystemCalculationService:
    """Get system calculation service"""
    return SystemCalculationService(system_calc_dao)


def get_report_execution_service(
    config_db: Session = Depends(get_db),
    dw_db: Session = Depends(get_dw_db)
) -> ReportExecutionService:
    """Get report execution service"""
    return ReportExecutionService(dw_db, config_db)


def get_cdi_service(
    config_db: Session = Depends(get_db),
    dw_db: Session = Depends(get_dw_db),
    system_calc_service: SystemCalculationService = Depends(get_system_calculation_service)
) -> CDIVariableCalculationService:
    """Get CDI variable calculation service"""
    cdi_service = CDIVariableCalculationService(dw_db, config_db, system_calc_service)
    # Set up bidirectional relationship
    system_calc_service.set_cdi_service(cdi_service)
    return cdi_service


# ===== UNIFIED CALCULATIONS ENDPOINT (ROOT) =====

class UnifiedCalculationsResponse(BaseModel):
    """Unified response containing both user and system calculations"""
    user_calculations: List[UserCalculationResponse]
    system_calculations: List[SystemCalculationResponse]
    summary: Dict[str, Any]

@router.get("", response_model=UnifiedCalculationsResponse)
def get_all_calculations(
    group_level: Optional[str] = Query(None, description="Filter by group level"),
    user_service: UserCalculationService = Depends(get_user_calculation_service),
    system_service: SystemCalculationService = Depends(get_system_calculation_service)
):
    """Get all calculations (user and system) in a unified response"""
    try:
        # Fetch both types of calculations
        user_calcs = user_service.get_all_user_calculations(group_level)
        system_calcs = system_service.get_all_system_calculations(group_level)
        
        # Create summary statistics
        user_in_use = sum(1 for calc in user_calcs if calc.usage_info and calc.usage_info.get('is_in_use', False))
        system_in_use = sum(1 for calc in system_calcs if calc.usage_info and calc.usage_info.get('is_in_use', False))
        
        summary = {
            "total_calculations": len(user_calcs) + len(system_calcs),
            "user_calculation_count": len(user_calcs),
            "system_calculation_count": len(system_calcs),
            "user_in_use_count": user_in_use,
            "system_in_use_count": system_in_use,
            "total_in_use": user_in_use + system_in_use,
            "group_level_filter": group_level
        }
        
        return UnifiedCalculationsResponse(
            user_calculations=user_calcs,
            system_calculations=system_calcs,
            summary=summary
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving calculations: {str(e)}")


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
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/user/{calc_id}", response_model=UserCalculationResponse)
def update_user_calculation(
    calc_id: int,
    request: UserCalculationUpdate,
    service: UserCalculationService = Depends(get_user_calculation_service)
):
    """Update an existing user calculation (partial update)"""
    try:
        return service.update_user_calculation(calc_id, request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/user/{calc_id}")
def delete_user_calculation(
    calc_id: int,
    service: UserCalculationService = Depends(get_user_calculation_service)
):
    """Delete a user calculation"""
    try:
        return service.delete_user_calculation(calc_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/user/{calc_id}/usage", response_model=CalculationUsageResponse)
def get_user_calculation_usage(
    calc_id: int,
    report_scope: Optional[str] = Query(None, description="Filter usage by report scope (DEAL/TRANCHE)"),
    service: UserCalculationService = Depends(get_user_calculation_service)
):
    """Get usage information for a user calculation"""
    try:
        return service.get_user_calculation_usage(calc_id, report_scope)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===== UNIFIED CALCULATION USAGE ENDPOINT =====

@router.get("/{calc_id}/usage", response_model=CalculationUsageResponse)
def get_calculation_usage(
    calc_id: int,
    calc_type: str = Query(..., description="Calculation type: 'user' or 'system'"),
    user_service: UserCalculationService = Depends(get_user_calculation_service),
    system_service: SystemCalculationService = Depends(get_system_calculation_service)
):
    """Get usage information for any calculation type"""
    try:
        if calc_type.lower() == 'user':
            return user_service.get_user_calculation_usage(calc_id)
        elif calc_type.lower() == 'system':
            return system_service.get_system_calculation_usage(calc_id)
        else:
            raise HTTPException(
                status_code=400, 
                detail="calc_type must be 'user' or 'system'"
            )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/user/{calc_id}/approve", response_model=UserCalculationResponse)
def approve_user_calculation(
    calc_id: int,
    approved_by: str = Body(..., embed=True),
    service: UserCalculationService = Depends(get_user_calculation_service)
):
    """Approve a user calculation"""
    try:
        return service.approve_user_calculation(calc_id, approved_by)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===== SYSTEM CALCULATION ENDPOINTS =====

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


@router.get("/system/{calc_id}/usage", response_model=CalculationUsageResponse)
def get_system_calculation_usage(
    calc_id: int,
    report_scope: Optional[str] = Query(None, description="Filter usage by report scope (DEAL/TRANCHE)"),
    service: SystemCalculationService = Depends(get_system_calculation_service)
):
    """Get usage information for a system calculation"""
    try:
        return service.get_system_calculation_usage(calc_id, report_scope)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/system", response_model=SystemCalculationResponse, status_code=201)
def create_system_calculation(
    request: SystemCalculationCreate,
    service: SystemCalculationService = Depends(get_system_calculation_service)
):
    """Create a new system-defined calculation with automatic approval for development"""
    try:
        # Create the system calculation
        created_calc = service.create_system_calculation(request)
        
        # Auto-approve for development (TODO: implement proper approval workflow)
        approved_calc = service.approve_system_calculation(created_calc.id, "system_auto_approval")
        
        return approved_calc
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/system/{calc_id}", response_model=SystemCalculationResponse)
def update_system_calculation(
    calc_id: int,
    request: SystemCalculationUpdate,
    service: SystemCalculationService = Depends(get_system_calculation_service)
):
    """Update an existing system calculation (partial update)"""
    try:
        return service.update_system_calculation(calc_id, request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/validate-system-sql")
def validate_system_sql(request: Dict[str, Any], service: SystemCalculationService = Depends(get_system_calculation_service)):
    """Validate system SQL using the same validation logic as creation"""
    try:
        sql_text = request.get("sql_text", "").strip()
        group_level = request.get("group_level", "")
        result_column_name = request.get("result_column_name", "")
        
        if not sql_text:
            return {
                "validation_result": {
                    "is_valid": False,
                    "errors": ["SQL text cannot be empty"],
                    "warnings": []
                }
            }
        
        if not group_level or group_level not in ["deal", "tranche"]:
            return {
                "validation_result": {
                    "is_valid": False,
                    "errors": ["Valid group_level is required (deal or tranche)"],
                    "warnings": []
                }
            }
        
        if not result_column_name:
            return {
                "validation_result": {
                    "is_valid": False,
                    "errors": ["Result column name is required"],
                    "warnings": []
                }
            }
        
        # Use the same validation logic as the schema and service layers
        errors = []
        warnings = []
        
        try:
            # Test Pydantic schema validation
            from .models import GroupLevel
            group_level_enum = GroupLevel(group_level)
            
            # Create a test SystemCalculationCreate object to validate with Pydantic
            test_request = SystemCalculationCreate(
                name="validation_test",
                raw_sql=sql_text,
                result_column_name=result_column_name,
                group_level=group_level_enum
            )
            
            # Test service layer validation
            service._validate_system_sql(sql_text, group_level_enum, result_column_name)
            
        except ValueError as e:
            # Pydantic validation error
            errors.append(str(e))
        except Exception as e:
            # Service validation error
            errors.append(str(e))
        
        # Add performance warnings (these aren't errors but good to show)
        sql_lower = sql_text.lower()
        if 'order by' in sql_lower:
            warnings.append("ORDER BY clauses may impact performance in aggregated reports")
        
        # Check for high CTE count
        cte_count = len(__import__('re').findall(r'WITH\s+\w+\s+AS', sql_text, __import__('re').IGNORECASE))
        if cte_count > 5:
            warnings.append(f"High number of CTEs ({cte_count}) may impact performance")
        
        # Check for recursive CTEs
        if __import__('re').search(r'WITH\s+RECURSIVE', sql_text, __import__('re').IGNORECASE):
            warnings.append('Recursive CTEs may have performance implications')
        
        return {
            "validation_result": {
                "is_valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
        }
        
    except Exception as e:
        return {
            "validation_result": {
                "is_valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": []
            }
        }


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
            "sql": query_result["sql"],
            "columns": query_result["columns"],
            "calculation_type": query_result["calculation_type"],
            "group_level": query_result["group_level"],
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


# ===== HEALTH CHECK =====

@router.get("/health")
def calculation_system_health():
    """Health check for the calculation system"""
    return {
        "status": "healthy",
        "system": "separated_calculations",
        "features": [
            "user_calculations",
            "system_calculations", 
            "static_fields",
            "individual_sql_queries",
            "in_memory_merging"
        ]
    }


# ===== NEW ENDPOINTS FOR LOOKUP BY SOURCE_FIELD AND RESULT_COLUMN =====

@router.get("/user/by-source-field/{source_field}", response_model=UserCalculationRead)
def get_user_calculation_by_source_field(
    source_field: str,
    service: UserCalculationService = Depends(get_user_calculation_service)
):
    """Get a user calculation by source_field (used with new calculation_id format)"""
    # URL decode the source_field parameter
    decoded_source_field = unquote(source_field)
    
    calculation = service.get_user_calculation_by_source_field(decoded_source_field)
    if not calculation:
        raise HTTPException(
            status_code=404, 
            detail=f"User calculation with source_field '{decoded_source_field}' not found"
        )
    return calculation


@router.get("/system/by-result-column/{result_column}", response_model=SystemCalculationRead)
def get_system_calculation_by_result_column(
    result_column: str,
    service: SystemCalculationService = Depends(get_system_calculation_service)
):
    """Get a system calculation by result_column_name (used with new calculation_id format)"""
    # URL decode the result_column parameter
    decoded_result_column = unquote(result_column)
    
    calculation = service.get_system_calculation_by_result_column(decoded_result_column)
    if not calculation:
        raise HTTPException(
            status_code=404, 
            detail=f"System calculation with result_column '{decoded_result_column}' not found"
        )
    return calculation


@router.get("/usage/{calculation_id}", response_model=CalculationUsageResponse)
def get_calculation_usage_by_calculation_id(
    calculation_id: str,
    service: UserCalculationService = Depends(get_user_calculation_service),
    system_service: SystemCalculationService = Depends(get_system_calculation_service)
):
    """Get calculation usage by the new calculation_id format"""
    # URL decode the calculation_id parameter
    decoded_calc_id = unquote(calculation_id)
    
    # Parse the calculation_id format
    if decoded_calc_id.startswith("user."):
        source_field = decoded_calc_id[5:]  # Remove "user." prefix
        calculation = service.get_user_calculation_by_source_field(source_field)
        if not calculation:
            raise HTTPException(
                status_code=404, 
                detail=f"User calculation with source_field '{source_field}' not found"
            )
        return service.get_user_calculation_usage(calculation.id)
    
    elif decoded_calc_id.startswith("system."):
        result_column = decoded_calc_id[7:]  # Remove "system." prefix
        calculation = system_service.get_system_calculation_by_result_column(result_column)
        if not calculation:
            raise HTTPException(
                status_code=404, 
                detail=f"System calculation with result_column '{result_column}' not found"
            )
        return system_service.get_system_calculation_usage(calculation.id)
    
    elif decoded_calc_id.startswith("static_"):
        # Static fields don't have usage tracking, return empty usage
        field_path = decoded_calc_id.replace("static_", "")
        return {
            "calculation_id": decoded_calc_id,
            "calculation_name": field_path,
            "is_in_use": False,
            "report_count": 0,
            "reports": []
        }
    
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid calculation_id format: {decoded_calc_id}. Expected 'user.', 'system.', or 'static_' prefix."
        )


# ===== VALIDATION ENDPOINTS FOR NEW FORMATS =====

@router.post("/user/validate-source-field")
def validate_user_calculation_source_field(
    request: Dict[str, str],
    service: UserCalculationService = Depends(get_user_calculation_service)
):
    """Validate if a source_field is available for user calculations"""
    source_field = request.get("source_field")
    if not source_field:
        raise HTTPException(status_code=400, detail="source_field is required")
    
    existing_calc = service.get_user_calculation_by_source_field(source_field)
    return {
        "source_field": source_field,
        "is_available": existing_calc is None,
        "existing_calculation": existing_calc.name if existing_calc else None
    }


@router.post("/system/validate-result-column")
def validate_system_calculation_result_column(
    request: Dict[str, str],
    service: SystemCalculationService = Depends(get_system_calculation_service)
):
    """Validate if a result_column_name is available for system calculations"""
    result_column = request.get("result_column")
    if not result_column:
        raise HTTPException(status_code=400, detail="result_column is required")
    
    existing_calc = service.get_system_calculation_by_result_column(result_column)
    return {
        "result_column": result_column,
        "is_available": existing_calc is None,
        "existing_calculation": existing_calc.name if existing_calc else None
    }


# ===== CDI VARIABLE CONFIGURATION ENDPOINTS =====

@router.get("/cdi-variables/config", response_model=CDIVariableConfigResponse)
def get_cdi_variable_config(
    cdi_service: CDIVariableCalculationService = Depends(get_cdi_service)
) -> CDIVariableConfigResponse:
    """Get configuration data for CDI variable calculations"""
    return CDIVariableConfigResponse(
        available_patterns=cdi_service.get_available_variable_patterns(),
        default_tranche_mappings=cdi_service.get_default_tranche_mappings(),
        variable_types=[
            "investment_income",
            "excess_interest", 
            "fees",
            "principal",
            "interest",
            "other"
        ]
    )

# ===== CDI VARIABLE CRUD ENDPOINTS =====

@router.get("/cdi-variables", response_model=List[CDIVariableResponse])
def get_all_cdi_variables(
    cdi_service: CDIVariableCalculationService = Depends(get_cdi_service)
) -> List[CDIVariableResponse]:
    """Get all CDI variable calculations"""
    return cdi_service.get_all_cdi_variable_calculations()

@router.get("/cdi-variables/summary", response_model=List[CDIVariableSummary])
def get_cdi_variables_summary(
    cdi_service: CDIVariableCalculationService = Depends(get_cdi_service)
) -> List[CDIVariableSummary]:
    """Get summary of all CDI variable calculations"""
    cdi_calcs = cdi_service.get_all_cdi_variable_calculations()
    
    summaries = []
    for calc in cdi_calcs:
        summaries.append(CDIVariableSummary(
            id=calc.id,
            name=calc.name,
            variable_type=calc.variable_type,
            result_column_name=calc.result_column_name,
            tranche_count=len(calc.tranche_mappings),
            created_by=calc.created_by,
            created_at=calc.created_at,
            is_active=calc.is_active
        ))
    
    return summaries

@router.get("/cdi-variables/{calc_id}", response_model=CDIVariableResponse)
def get_cdi_variable_by_id(
    calc_id: int,
    cdi_service: CDIVariableCalculationService = Depends(get_cdi_service)
) -> CDIVariableResponse:
    """Get a specific CDI variable calculation by ID"""
    calc = cdi_service.get_cdi_variable_calculation(calc_id)
    if not calc:
        raise HTTPException(status_code=404, detail="CDI variable calculation not found")
    return calc

@router.post("/cdi-variables", response_model=CDIVariableResponse)
def create_cdi_variable(
    request: CDIVariableCreate,
    cdi_service: CDIVariableCalculationService = Depends(get_cdi_service),
    created_by: str = "system"  # TODO: Get from auth context
) -> CDIVariableResponse:
    """Create a new CDI variable calculation"""
    try:
        return cdi_service.create_cdi_variable_calculation(request, created_by)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/cdi-variables/{calc_id}", response_model=CDIVariableResponse)
def update_cdi_variable(
    calc_id: int,
    request: CDIVariableUpdate,
    cdi_service: CDIVariableCalculationService = Depends(get_cdi_service)
) -> CDIVariableResponse:
    """Update an existing CDI variable calculation (partial update)"""
    try:
        return cdi_service.update_cdi_variable_calculation(calc_id, request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/cdi-variables/{calc_id}")
def delete_cdi_variable(
    calc_id: int,
    system_calc_service: SystemCalculationService = Depends(get_system_calculation_service)
) -> Dict[str, str]:
    """Delete a CDI variable calculation (soft delete the underlying SystemCalculation)"""
    try:
        return system_calc_service.delete_system_calculation(calc_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===== CDI VARIABLE EXECUTION ENDPOINTS =====

@router.post("/cdi-variables/{calc_id}/execute", response_model=CDIVariableExecutionResponse)
def execute_cdi_variable(
    calc_id: int,
    request: CDIVariableExecutionRequest,
    cdi_service: CDIVariableCalculationService = Depends(get_cdi_service)
) -> CDIVariableExecutionResponse:
    """Execute a CDI variable calculation"""
    start_time = time.time()
    
    try:
        # Get calculation info
        calc = cdi_service.get_cdi_variable_calculation(calc_id)
        if not calc:
            raise HTTPException(status_code=404, detail="CDI variable calculation not found")
        
        # Execute the calculation
        result_df = cdi_service.execute_cdi_variable_calculation(
            calc_id, request.cycle_code, request.deal_numbers
        )
        
        # Convert DataFrame to list of dicts
        result_data = result_df.to_dict('records') if not result_df.empty else []
        
        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        return CDIVariableExecutionResponse(
            calculation_id=calc_id,
            calculation_name=calc.name,
            cycle_code=request.cycle_code,
            deal_count=len(request.deal_numbers),
            tranche_count=len(result_data),
            data=result_data,
            execution_time_ms=execution_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Execution failed: {str(e)}")

@router.post("/cdi-variables/execute-batch")
def execute_cdi_variables_batch(
    calculation_ids: List[int],
    cycle_code: int,
    deal_numbers: List[int],
    cdi_service: CDIVariableCalculationService = Depends(get_cdi_service)
) -> Dict[str, Any]:
    """Execute multiple CDI variable calculations in batch"""
    
    results = {}
    errors = {}
    
    for calc_id in calculation_ids:
        try:
            result_df = cdi_service.execute_cdi_variable_calculation(calc_id, cycle_code, deal_numbers)
            results[str(calc_id)] = result_df.to_dict('records') if not result_df.empty else []
        except Exception as e:
            errors[str(calc_id)] = str(e)
    
    return {
        "successful_calculations": len(results),
        "failed_calculations": len(errors),
        "results": results,
        "errors": errors,
        "cycle_code": cycle_code,
        "deal_count": len(deal_numbers)
    }

# ===== CDI VARIABLE VALIDATION ENDPOINTS =====

@router.post("/cdi-variables/validate", response_model=CDIVariableValidationResponse)
def validate_cdi_variable_config(
    request: CDIVariableValidationRequest,
    cdi_service: CDIVariableCalculationService = Depends(get_cdi_service)
) -> CDIVariableValidationResponse:
    """Validate a CDI variable configuration before creating it"""
    
    try:
        # Generate test SQL to see if configuration is valid
        sql = cdi_service._generate_dynamic_sql(
            request.variable_pattern, 
            request.tranche_mappings, 
            request.cycle_code, 
            request.sample_deal_numbers
        )
        
        # Try to execute the SQL to validate it
        import pandas as pd
        result_df = pd.read_sql(sql, cdi_service.dw_db.bind)
        
        warnings = []
        errors = []
        
        # Check for potential issues
        if result_df.empty:
            warnings.append("No data found for the given configuration and sample deals")
        
        # Check if all tranche types have data
        found_tranches = set()
        if not result_df.empty and 'tranche_type' in result_df.columns:
            found_tranches = set(result_df['tranche_type'].unique())
        
        configured_tranches = set(request.tranche_mappings.keys())
        missing_tranches = configured_tranches - found_tranches
        
        if missing_tranches:
            warnings.append(f"No data found for tranche types: {', '.join(missing_tranches)}")
        
        return CDIVariableValidationResponse(
            is_valid=len(errors) == 0,
            validation_results={
                "sql_generated": True,
                "sql_executed": True,
                "configured_tranches": list(configured_tranches),
                "found_tranches": list(found_tranches),
                "missing_tranches": list(missing_tranches)
            },
            sample_data_count=len(result_df),
            warnings=warnings,
            errors=errors
        )
        
    except Exception as e:
        return CDIVariableValidationResponse(
            is_valid=False,
            validation_results={"sql_generated": False, "error": str(e)},
            sample_data_count=0,
            warnings=[],
            errors=[f"Configuration validation failed: {str(e)}"]
        )

# ===== BULK OPERATIONS =====

@router.post("/cdi-variables/bulk-create", response_model=CDIVariableBulkCreateResponse)
def bulk_create_cdi_variables(
    request: CDIVariableBulkCreateRequest,
    cdi_service: CDIVariableCalculationService = Depends(get_cdi_service)
) -> CDIVariableBulkCreateResponse:
    """Create multiple CDI variable calculations at once"""
    
    created_calculations = []
    failures = []
    
    for calc_request in request.calculations:
        try:
            created_calc = cdi_service.create_cdi_variable_calculation(calc_request, request.created_by)
            created_calculations.append(created_calc)
        except Exception as e:
            failures.append({
                "calculation_name": calc_request.name,
                "error": str(e)
            })
    
    return CDIVariableBulkCreateResponse(
        created_count=len(created_calculations),
        failed_count=len(failures),
        created_calculations=created_calculations,
        failures=failures
    )

# ===== INTEGRATION WITH EXISTING ENDPOINTS =====

@router.get("/all-with-cdi", response_model=Dict[str, Any])
def get_all_calculations_with_cdi(
    group_level: Optional[str] = Query(None),
    user_calc_service: UserCalculationService = Depends(get_user_calculation_service),
    system_calc_service: SystemCalculationService = Depends(get_system_calculation_service),
    cdi_service: CDIVariableCalculationService = Depends(get_cdi_service)
) -> Dict[str, Any]:
    """Get all calculations including CDI variables"""
    
    # Get regular calculations
    user_calcs = user_calc_service.get_all_user_calculations(group_level)
    system_calcs = system_calc_service.get_all_system_calculations(group_level)
    
    # Get CDI variable calculations
    cdi_calcs = cdi_service.get_all_cdi_variable_calculations()
    
    # Filter system calcs to exclude CDI variables (to avoid duplication)
    regular_system_calcs = [
        calc for calc in system_calcs 
        if not system_calc_service.is_cdi_variable_calculation(calc.id)
    ]
    
    return {
        "user_calculations": [UserCalculationResponse.model_validate(calc) for calc in user_calcs],
        "system_calculations": [SystemCalculationResponse.model_validate(calc) for calc in regular_system_calcs],
        "cdi_variable_calculations": cdi_calcs,
        "summary": {
            "total_user": len(user_calcs),
            "total_system": len(regular_system_calcs),
            "total_cdi_variables": len(cdi_calcs),
            "total_all": len(user_calcs) + len(regular_system_calcs) + len(cdi_calcs)
        }
    }