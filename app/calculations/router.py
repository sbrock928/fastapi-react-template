# app/calculations/router.py
"""Clean API router for the separated calculation system"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.core.dependencies import get_db, get_dw_db, get_user_calculation_dao, get_system_calculation_dao

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
from app.calculations.audit_models import flush_pending_audits, get_audit_stats

# Additional endpoints to add to app/calculations/router.py
"""Audit trail endpoints for the calculation router."""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import Query, HTTPException, Body
from app.calculations.audit_service import CalculationAuditService
from app.core.dependencies import get_calculation_audit_service

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


@router.put("/user/{calc_id}", response_model=UserCalculationResponse)
def update_user_calculation(
    calc_id: int,
    request: UserCalculationUpdate,
    service: UserCalculationService = Depends(get_user_calculation_service)
):
    """Update an existing user calculation"""
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
    service: UserCalculationService = Depends(get_user_calculation_service)
):
    """Get usage information for a user calculation"""
    try:
        return service.get_user_calculation_usage(calc_id)
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
    service: SystemCalculationService = Depends(get_system_calculation_service)
):
    """Get usage information for a system calculation"""
    try:
        return service.get_system_calculation_usage(calc_id)
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


@router.post("/validate-system-sql")
def validate_system_sql(request: Dict[str, Any]):
    """Validate system SQL before creation"""
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
        
        # Basic SQL validation
        sql_lower = sql_text.lower().strip()
        errors = []
        warnings = []
        
        # Check basic structure
        if not sql_lower.startswith('select'):
            errors.append("SQL must be a SELECT statement")
        
        if 'from' not in sql_lower:
            errors.append("SQL must include a FROM clause")
        
        # Check for dangerous operations
        dangerous_keywords = ['drop', 'delete', 'insert', 'update', 'alter', 'truncate', 'create']
        for keyword in dangerous_keywords:
            if keyword in sql_lower:
                errors.append(f"Dangerous operation '{keyword.upper()}' not allowed")
        
        # Check for required fields based on group level
        if group_level == "deal":
            if 'deal.dl_nbr' not in sql_lower and 'dl_nbr' not in sql_lower:
                errors.append("Deal-level SQL must include deal.dl_nbr for proper grouping")
        
        if group_level == "tranche":
            has_deal_nbr = 'deal.dl_nbr' in sql_lower or 'dl_nbr' in sql_lower
            has_tranche_id = 'tranche.tr_id' in sql_lower or 'tr_id' in sql_lower
            
            if not has_deal_nbr:
                errors.append("Tranche-level SQL must include deal.dl_nbr for proper grouping")
            if not has_tranche_id:
                errors.append("Tranche-level SQL must include tranche.tr_id for proper grouping")
        
        # Check result column name format
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', result_column_name):
            errors.append("Result column name must be a valid SQL identifier (letters, numbers, underscores, starting with letter)")
        
        # Check if result column appears in SQL
        if result_column_name.lower() not in sql_lower:
            warnings.append(f"Result column '{result_column_name}' should appear in your SQL SELECT clause")
        
        # Additional warnings
        if 'order by' in sql_lower:
            warnings.append("ORDER BY clauses may impact performance in aggregated reports")
        
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


@router.post("/system/{calc_id}/approve", response_model=SystemCalculationResponse)
def approve_system_calculation(
    calc_id: int,
    approved_by: str = Body(..., embed=True),
    service: SystemCalculationService = Depends(get_system_calculation_service)
):
    """Approve a system calculation"""
    try:
        return service.approve_system_calculation(calc_id, approved_by)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/system/{calc_id}")
def delete_system_calculation(
    calc_id: int,
    service: SystemCalculationService = Depends(get_system_calculation_service)
):
    """Delete a system calculation"""
    try:
        return service.delete_system_calculation(calc_id)
    except Exception as e:
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


# ===== UNIFIED CALCULATIONS ENDPOINT =====

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
    

# Add this dependency function to the router
def get_audit_service(
    config_db: Session = Depends(get_db)
) -> CalculationAuditService:
    """Get calculation audit service"""
    from app.calculations.audit_dao import CalculationAuditDAO
    audit_dao = CalculationAuditDAO(config_db)
    return CalculationAuditService(audit_dao)

# ===== AUDIT TRAIL ENDPOINTS =====

@router.get("/audit/recent")
def get_recent_audit_activity(
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    audit_service: CalculationAuditService = Depends(get_audit_service)
):
    """Get recent audit activity across all calculations."""
    try:
        return {
            "success": True,
            "data": audit_service.get_recent_audit_activity(limit),
            "metadata": {
                "limit": limit,
                "timestamp": datetime.now().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving audit activity: {str(e)}")


@router.get("/audit/calculation/{calculation_type}/{calculation_id}")
def get_calculation_audit_history(
    calculation_type: str,
    calculation_id: int,
    limit: int = Query(50, ge=1, le=200, description="Maximum number of records to return"),
    audit_service: CalculationAuditService = Depends(get_audit_service)
):
    """Get audit history for a specific calculation."""
    try:
        # Validate calculation type
        if calculation_type not in ['user', 'system']:
            raise HTTPException(
                status_code=400, 
                detail="calculation_type must be 'user' or 'system'"
            )
        
        history = audit_service.get_audit_history_for_calculation(
            calculation_type, calculation_id, limit
        )
        
        return {
            "success": True,
            "data": history,
            "metadata": {
                "calculation_type": calculation_type,
                "calculation_id": calculation_id,
                "limit": limit,
                "record_count": len(history)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving audit history: {str(e)}")


@router.get("/audit/calculation/{calculation_type}/{calculation_id}/timeline")
def get_calculation_change_timeline(
    calculation_type: str,
    calculation_id: int,
    audit_service: CalculationAuditService = Depends(get_audit_service)
):
    """Get detailed change timeline for a specific calculation."""
    try:
        if calculation_type not in ['user', 'system']:
            raise HTTPException(
                status_code=400, 
                detail="calculation_type must be 'user' or 'system'"
            )
        
        timeline = audit_service.get_calculation_change_timeline(calculation_type, calculation_id)
        
        return {
            "success": True,
            "data": timeline,
            "metadata": {
                "calculation_type": calculation_type,
                "calculation_id": calculation_id
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving change timeline: {str(e)}")


@router.get("/audit/user/{username}")
def get_audit_activity_by_user(
    username: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    audit_service: CalculationAuditService = Depends(get_audit_service)
):
    """Get audit activity for a specific user."""
    try:
        activity = audit_service.get_audit_activity_by_user(username, limit)
        
        return {
            "success": True,
            "data": activity,
            "metadata": {
                "username": username,
                "limit": limit,
                "record_count": len(activity)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving user audit activity: {str(e)}")


@router.get("/audit/operation/{operation}")
def get_audit_activity_by_operation(
    operation: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    audit_service: CalculationAuditService = Depends(get_audit_service)
):
    """Get audit activity for a specific operation type (INSERT, UPDATE, DELETE)."""
    try:
        activity = audit_service.get_audit_activity_by_operation(operation, limit)
        
        return {
            "success": True,
            "data": activity,
            "metadata": {
                "operation": operation.upper(),
                "limit": limit,
                "record_count": len(activity)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving operation audit activity: {str(e)}")


@router.get("/audit/type/{calculation_type}")
def get_audit_activity_by_calculation_type(
    calculation_type: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    audit_service: CalculationAuditService = Depends(get_audit_service)
):
    """Get audit activity for a specific calculation type (user or system)."""
    try:
        activity = audit_service.get_audit_activity_by_calculation_type(calculation_type, limit)
        
        return {
            "success": True,
            "data": activity,
            "metadata": {
                "calculation_type": calculation_type,
                "limit": limit,
                "record_count": len(activity)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving calculation type audit activity: {str(e)}")


@router.post("/audit/search")
def search_audit_logs(
    search_params: Dict[str, Any] = Body(...),
    audit_service: CalculationAuditService = Depends(get_audit_service)
):
    """Advanced search for audit logs with multiple filters."""
    try:
        # Extract search parameters with defaults
        calculation_ids = search_params.get("calculation_ids")
        calculation_types = search_params.get("calculation_types")
        operations = search_params.get("operations")
        users = search_params.get("users")
        limit = search_params.get("limit", 100)
        
        # Parse date strings if provided
        start_date = None
        end_date = None
        if search_params.get("start_date"):
            start_date = datetime.fromisoformat(search_params["start_date"].replace('Z', '+00:00'))
        if search_params.get("end_date"):
            end_date = datetime.fromisoformat(search_params["end_date"].replace('Z', '+00:00'))
        
        results = audit_service.search_audit_logs(
            calculation_ids=calculation_ids,
            calculation_types=calculation_types,
            operations=operations,
            users=users,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        return {
            "success": True,
            "data": results,
            "metadata": {
                "search_params": search_params,
                "record_count": len(results)
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching audit logs: {str(e)}")


@router.get("/audit/statistics")
def get_audit_statistics(
    days_back: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    audit_service: CalculationAuditService = Depends(get_audit_service)
):
    """Get audit statistics for dashboard display."""
    try:
        stats = audit_service.get_audit_statistics(days_back)
        
        return {
            "success": True,
            "data": stats,
            "metadata": {
                "generated_at": datetime.now().isoformat()
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving audit statistics: {str(e)}")


@router.get("/audit/trends")
def get_audit_trends(
    days_back: int = Query(30, ge=7, le=365, description="Number of days to analyze"),
    audit_service: CalculationAuditService = Depends(get_audit_service)
):
    """Get audit activity trends for analytics."""
    try:
        trends = audit_service.get_audit_trends(days_back)
        
        return {
            "success": True,
            "data": trends,
            "metadata": {
                "generated_at": datetime.now().isoformat()
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving audit trends: {str(e)}")


@router.post("/audit/cleanup")
def cleanup_old_audit_logs(
    cleanup_params: Dict[str, int] = Body(..., example={"days_to_keep": 365}),
    audit_service: CalculationAuditService = Depends(get_audit_service)
):
    """Clean up old audit logs (admin function)."""
    try:
        days_to_keep = cleanup_params.get("days_to_keep", 365)
        result = audit_service.cleanup_old_audit_logs(days_to_keep)
        
        return {
            "success": True,
            "data": result,
            "message": f"Cleaned up audit logs older than {days_to_keep} days"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cleaning up audit logs: {str(e)}")


# ===== AUDIT DASHBOARD ENDPOINT =====

@router.get("/audit/dashboard")
def get_audit_dashboard(
    days_back: int = Query(30, ge=1, le=365, description="Number of days for dashboard data"),
    audit_service: CalculationAuditService = Depends(get_audit_service)
):
    """Get comprehensive audit dashboard data."""
    try:
        # Get statistics and trends
        stats = audit_service.get_audit_statistics(days_back)
        trends = audit_service.get_audit_trends(min(days_back, 30))  # Limit trends to 30 days max
        recent_activity = audit_service.get_recent_audit_activity(20)  # Last 20 activities
        
        dashboard_data = {
            "overview": {
                "period_days": days_back,
                "total_changes": stats["total_changes"],
                "daily_average": stats["daily_average"],
                "unique_calculations_changed": stats["unique_calculations_changed"],
                "insights": stats["insights"]
            },
            "statistics": stats,
            "trends": trends,
            "recent_activity": recent_activity[:10],  # Top 10 most recent
            "summary": {
                "top_users": stats["most_active_users"][:5],  # Top 5 users
                "operation_breakdown": stats["by_operation"],
                "calculation_type_breakdown": stats.get("by_table_display", {}),
                "busiest_day": trends["summary"].get("busiest_day", {}).get("date") if trends["daily_trends"] else None
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
        raise HTTPException(status_code=500, detail=f"Error generating audit dashboard: {str(e)}")


# ===== AUDIT MONITORING ENDPOINTS =====

@router.get("/audit/stats")
def get_audit_system_stats():
    """Get audit system statistics for monitoring."""
    try:
        stats = get_audit_stats()
        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving audit stats: {str(e)}")


@router.post("/audit/flush")
def flush_audit_logs():
    """Manually flush pending audit logs (admin function)."""
    try:
        stats_before = get_audit_stats()
        flush_pending_audits()
        stats_after = get_audit_stats()
        
        return {
            "success": True,
            "message": "Audit logs flushed successfully",
            "stats_before": stats_before,
            "stats_after": stats_after,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error flushing audit logs: {str(e)}")