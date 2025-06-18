# app/calculations/router.py
"""Clean API router for the unified calculation system"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from urllib.parse import unquote
import time
from app.core.dependencies import get_db, get_dw_db, get_unified_calculation_service

from .schemas import (
    UserAggregationCalculationCreate, SystemFieldCalculationCreate, SystemSqlCalculationCreate,
    CalculationUpdate, CalculationResponse, CalculationListResponse,
    SqlValidationRequest, SqlValidationResponse, PlaceholderListResponse,
    CalculationPreviewRequest, CalculationPreviewResponse,
    BulkCalculationOperation, BulkCalculationResponse
)
from .service import UnifiedCalculationService

router = APIRouter(prefix="/calculations", tags=["calculations"])


# ===== DEPENDENCY FUNCTIONS =====

def get_user_calculation_service(service: UnifiedCalculationService = Depends(get_unified_calculation_service)) -> UnifiedCalculationService:
    """Get user calculation service (unified)"""
    return service


def get_system_calculation_service(service: UnifiedCalculationService = Depends(get_unified_calculation_service)) -> UnifiedCalculationService:
    """Get system calculation service (unified)"""
    return service


def get_report_execution_service(
    service: UnifiedCalculationService = Depends(get_unified_calculation_service)
) -> UnifiedCalculationService:
    """Get report execution service (unified)"""
    return service


# ===== UNIFIED CALCULATIONS ENDPOINT (ROOT) =====

class UnifiedCalculationsResponse(BaseModel):
    """Unified response containing both user and system calculations"""
    user_calculations: List[CalculationResponse]
    system_calculations: List[CalculationResponse]
    summary: Dict[str, Any]

@router.get("", response_model=UnifiedCalculationsResponse)
def get_all_calculations(
    group_level: Optional[str] = Query(None, description="Filter by group level"),
    service: UnifiedCalculationService = Depends(get_report_execution_service)
):
    """Get all calculations (user and system) in a unified response"""
    try:
        # Fetch both types of calculations using the unified service
        user_calcs = service.get_calculations_by_type("USER_AGGREGATION", group_level)
        system_calcs = service.get_calculations_by_type("SYSTEM_SQL", group_level)
        
        # Create summary statistics
        summary = {
            "total_calculations": len(user_calcs) + len(system_calcs),
            "user_calculation_count": len(user_calcs),
            "system_calculation_count": len(system_calcs),
            "user_in_use_count": 0,  # TODO: implement usage tracking
            "system_in_use_count": 0,  # TODO: implement usage tracking
            "total_in_use": 0,
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

@router.get("/config")
def get_calculation_configuration():
    """Get calculation configuration for UI"""
    from .models import AggregationFunction, SourceModel, GroupLevel
    
    # Generate detailed configuration with labels and descriptions for UI dropdowns
    aggregation_functions = [
        {
            "value": "SUM",
            "label": "SUM - Total amount",
            "description": "Add all values together",
            "category": "aggregated"
        },
        {
            "value": "AVG",
            "label": "AVG - Average",
            "description": "Calculate average value",
            "category": "aggregated"
        },
        {
            "value": "COUNT",
            "label": "COUNT - Count records",
            "description": "Count number of records",
            "category": "aggregated"
        },
        {
            "value": "MIN",
            "label": "MIN - Minimum value",
            "description": "Find minimum value",
            "category": "aggregated"
        },
        {
            "value": "MAX",
            "label": "MAX - Maximum value",
            "description": "Find maximum value",
            "category": "aggregated"
        },
        {
            "value": "WEIGHTED_AVG",
            "label": "WEIGHTED_AVG - Weighted average",
            "description": "Calculate weighted average using specified weight field",
            "category": "aggregated"
        },
        {
            "value": "RAW",
            "label": "RAW - Raw field value",
            "description": "Include field value without aggregation",
            "category": "raw"
        }
    ]
    
    source_models = [
        {
            "value": "Deal",
            "label": "Deal - Deal-level information",
            "description": "Core deal attributes and metadata"
        },
        {
            "value": "Tranche",
            "label": "Tranche - Tranche structure",
            "description": "Tranche-specific attributes and configuration"
        },
        {
            "value": "TrancheBal",
            "label": "TrancheBal - Balance & performance",
            "description": "Tranche balance amounts and performance metrics"
        }
    ]
    
    group_levels = [
        {
            "value": "deal",
            "label": "Deal Level",
            "description": "Aggregate to deal level - one result per deal"
        },
        {
            "value": "tranche",
            "label": "Tranche Level",
            "description": "Aggregate to tranche level - one result per tranche"
        }
    ]
    
    # Basic static fields structure (TODO: implement full static fields service)
    static_fields = [
        {
            "field_path": "deal.dl_nbr",
            "name": "Deal Number",
            "description": "Unique deal identifier",
            "type": "number",
            "nullable": False
        },
        {
            "field_path": "deal.issr_cde",
            "name": "Issuer Code",
            "description": "Deal issuer identifier",
            "type": "string",
            "nullable": True
        },
        {
            "field_path": "tranche.tr_id",
            "name": "Tranche ID",
            "description": "Tranche identifier within deal",
            "type": "string",
            "nullable": False
        },
        {
            "field_path": "tranchebal.tr_end_bal_amt",
            "name": "Ending Balance Amount",
            "description": "Tranche ending balance amount",
            "type": "currency",
            "nullable": True
        },
        {
            "field_path": "tranchebal.tr_pass_thru_rte",
            "name": "Pass Through Rate",
            "description": "Tranche pass-through interest rate",
            "type": "percentage",
            "nullable": True
        },
        {
            "field_path": "tranchebal.cycle_cde",
            "name": "Cycle Code",
            "description": "Reporting cycle identifier",
            "type": "number",
            "nullable": False
        }
    ]
    
    return {
        "aggregation_functions": aggregation_functions,
        "source_models": source_models,
        "group_levels": group_levels,
        "static_fields": static_fields
    }


# ===== STATIC FIELD ENDPOINTS =====

@router.get("/static-fields")
def get_static_fields(
    model: Optional[str] = Query(None, description="Filter by model name")
):
    """Get available static fields"""
    # TODO: implement static fields service
    return []


@router.get("/static-fields/{field_path:path}")
def get_static_field_by_path(field_path: str):
    """Get static field information by path"""
    # TODO: implement static field lookup
    raise HTTPException(status_code=404, detail=f"Static field '{field_path}' not found")


# ===== USER CALCULATION ENDPOINTS =====

@router.get("/user/{calc_id}", response_model=CalculationResponse)
def get_user_calculation_by_id(
    calc_id: int,
    service: UnifiedCalculationService = Depends(get_report_execution_service)
):
    """Get a user calculation by ID"""
    calculation = service.get_calculation_by_id(calc_id)
    if not calculation or calculation.calculation_type != "USER_AGGREGATION":
        raise HTTPException(status_code=404, detail="User calculation not found")
    return calculation


@router.post("/user", response_model=CalculationResponse, status_code=201)
def create_user_calculation(
    request: UserAggregationCalculationCreate,
    service: UnifiedCalculationService = Depends(get_report_execution_service)
):
    """Create a new user-defined calculation"""
    try:
        return service.create_user_aggregation_calculation(request, "system")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/user/{calc_id}", response_model=CalculationResponse)
def update_user_calculation(
    calc_id: int,
    request: CalculationUpdate,
    service: UnifiedCalculationService = Depends(get_report_execution_service)
):
    """Update an existing user calculation (partial update)"""
    try:
        return service.update_calculation(calc_id, request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/user/{calc_id}")
def delete_user_calculation(
    calc_id: int,
    service: UnifiedCalculationService = Depends(get_report_execution_service)
):
    """Delete a user calculation"""
    try:
        service.delete_calculation(calc_id)
        return {"message": "User calculation deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/user/{calc_id}/usage")
def get_user_calculation_usage(
    calc_id: int,
    report_scope: Optional[str] = Query(None, description="Filter usage by report scope (DEAL/TRANCHE)"),
    service: UnifiedCalculationService = Depends(get_report_execution_service)
):
    """Get usage information for a user calculation"""
    try:
        # TODO: implement usage tracking
        return {
            "calculation_id": calc_id,
            "calculation_name": "Unknown",
            "is_in_use": False,
            "report_count": 0,
            "reports": []
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===== UNIFIED CALCULATION USAGE ENDPOINT =====

@router.get("/{calc_id}/usage")
def get_calculation_usage(
    calc_id: int,
    calc_type: str = Query(..., description="Calculation type: 'user' or 'system'"),
    service: UnifiedCalculationService = Depends(get_report_execution_service)
):
    """Get usage information for any calculation type"""
    try:
        # TODO: implement usage tracking
        return {
            "calculation_id": calc_id,
            "calculation_name": "Unknown",
            "is_in_use": False,
            "report_count": 0,
            "reports": []
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/user/{calc_id}/approve", response_model=CalculationResponse)
def approve_user_calculation(
    calc_id: int,
    approved_by: str = Body(..., embed=True),
    service: UnifiedCalculationService = Depends(get_report_execution_service)
):
    """Approve a user calculation"""
    try:
        return service.approve_calculation(calc_id, approved_by)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===== SYSTEM CALCULATION ENDPOINTS =====

@router.get("/system/{calc_id}", response_model=CalculationResponse)
def get_system_calculation_by_id(
    calc_id: int,
    service: UnifiedCalculationService = Depends(get_report_execution_service)
):
    """Get a system calculation by ID"""
    calculation = service.get_calculation_by_id(calc_id)
    if not calculation or calculation.calculation_type != "SYSTEM_SQL":
        raise HTTPException(status_code=404, detail="System calculation not found")
    return calculation


@router.get("/system/{calc_id}/usage")
def get_system_calculation_usage(
    calc_id: int,
    report_scope: Optional[str] = Query(None, description="Filter usage by report scope (DEAL/TRANCHE)"),
    service: UnifiedCalculationService = Depends(get_report_execution_service)
):
    """Get usage information for a system calculation"""
    try:
        # TODO: implement usage tracking
        return {
            "calculation_id": calc_id,
            "calculation_name": "Unknown",
            "is_in_use": False,
            "report_count": 0,
            "reports": []
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/system", response_model=CalculationResponse, status_code=201)
def create_system_calculation(
    request: SystemSqlCalculationCreate,
    service: UnifiedCalculationService = Depends(get_report_execution_service)
):
    """Create a new system-defined calculation with automatic approval for development"""
    try:
        # Create the system calculation
        created_calc = service.create_system_sql_calculation(request, "system")
        
        # Auto-approve for development (TODO: implement proper approval workflow)
        approved_calc = service.approve_calculation(created_calc.id, "system_auto_approval")
        
        return approved_calc
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/system/{calc_id}", response_model=CalculationResponse)
def update_system_calculation(
    calc_id: int,
    request: CalculationUpdate,
    service: UnifiedCalculationService = Depends(get_report_execution_service)
):
    """Update an existing system calculation (partial update)"""
    try:
        return service.update_calculation(calc_id, request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/validate-system-sql")
def validate_system_sql(request: Dict[str, Any]):
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
        
        # Use basic validation logic
        errors = []
        warnings = []
        
        try:
            # Test Pydantic schema validation
            from .models import GroupLevel
            group_level_enum = GroupLevel(group_level)
            
            # Create a test SystemSqlCalculationCreate object to validate with Pydantic
            test_request = SystemSqlCalculationCreate(
                name="validation_test",
                raw_sql=sql_text,
                result_column_name=result_column_name,
                group_level=group_level_enum
            )
            
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


# ===== SIMPLIFIED ENDPOINTS =====

@router.post("/execute-report")
def execute_report(request: Dict[str, Any]):
    """Execute a report with mixed calculation types - simplified"""
    try:
        # TODO: implement report execution
        return {
            "success": False,
            "message": "Report execution not yet implemented in unified system"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing report: {str(e)}")


@router.post("/preview-sql")
def preview_report_sql(request: Dict[str, Any]):
    """Preview SQL for a report without executing it - simplified"""
    try:
        # TODO: implement SQL preview
        return {
            "success": False,
            "message": "SQL preview not yet implemented in unified system"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error previewing SQL: {str(e)}")


@router.post("/preview-single")
def preview_single_calculation(request: Dict[str, Any]):
    """Preview SQL for a single calculation - simplified"""
    try:
        # TODO: implement single calculation preview
        return {
            "success": False,
            "message": "Single calculation preview not yet implemented in unified system"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error previewing calculation: {str(e)}")


# ===== STATISTICS ENDPOINTS =====

@router.get("/stats/counts")
def get_calculation_counts(
    service: UnifiedCalculationService = Depends(get_report_execution_service)
):
    """Get calculation counts by type"""
    try:
        # Get all calculations
        user_calcs = service.get_calculations_by_type("USER_AGGREGATION")
        system_calcs = service.get_calculations_by_type("SYSTEM_SQL")
        
        return {
            "success": True,
            "counts": {
                "user_calculations": len(user_calcs),
                "system_calculations": len(system_calcs),
                "total": len(user_calcs) + len(system_calcs)
            },
            "breakdown": {
                "user_by_group_level": {
                    "deal": len([c for c in user_calcs if c.group_level == "deal"]),
                    "tranche": len([c for c in user_calcs if c.group_level == "tranche"])
                },
                "system_by_group_level": {
                    "deal": len([c for c in system_calcs if c.group_level == "deal"]),
                    "tranche": len([c for c in system_calcs if c.group_level == "tranche"])
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
        "system": "unified_calculations",
        "features": [
            "user_aggregation_calculations",
            "system_sql_calculations", 
            "unified_data_model"
        ]
    }


# ===== SIMPLIFIED LOOKUP ENDPOINTS =====

@router.get("/user/by-source-field/{source_field}")
def get_user_calculation_by_source_field(
    source_field: str,
    service: UnifiedCalculationService = Depends(get_report_execution_service)
):
    """Get a user calculation by source_field (used with new calculation_id format)"""
    try:
        # URL decode the source_field parameter
        decoded_source_field = unquote(source_field)
        
        # TODO: implement source field lookup
        return {
            "success": False,
            "message": f"Source field lookup for '{decoded_source_field}' not yet implemented"
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/system/by-result-column/{result_column}")
def get_system_calculation_by_result_column(
    result_column: str,
    service: UnifiedCalculationService = Depends(get_report_execution_service)
):
    """Get a system calculation by result_column_name (used with new calculation_id format)"""
    try:
        # URL decode the result_column parameter
        decoded_result_column = unquote(result_column)
        
        # TODO: implement result column lookup
        return {
            "success": False,
            "message": f"Result column lookup for '{decoded_result_column}' not yet implemented"
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/usage/{calculation_id}")
def get_calculation_usage_by_calculation_id(
    calculation_id: str,
    service: UnifiedCalculationService = Depends(get_report_execution_service)
):
    """Get calculation usage by the new calculation_id format"""
    try:
        # URL decode the calculation_id parameter
        decoded_calc_id = unquote(calculation_id)
        
        # TODO: implement usage tracking
        return {
            "calculation_id": decoded_calc_id,
            "calculation_name": "Unknown",
            "is_in_use": False,
            "report_count": 0,
            "reports": []
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===== VALIDATION ENDPOINTS FOR NEW FORMATS =====

@router.post("/user/validate-source-field")
def validate_user_calculation_source_field(request: Dict[str, str]):
    """Validate if a source_field is available for user calculations"""
    try:
        source_field = request.get("source_field")
        if not source_field:
            raise HTTPException(status_code=400, detail="source_field is required")
        
        # TODO: implement validation
        return {
            "source_field": source_field,
            "is_available": True,  # Placeholder
            "existing_calculation": None
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/system/validate-result-column")
def validate_system_calculation_result_column(request: Dict[str, str]):
    """Validate if a result_column_name is available for system calculations"""
    try:
        result_column = request.get("result_column")
        if not result_column:
            raise HTTPException(status_code=400, detail="result_column is required")
        
        # TODO: implement validation
        return {
            "result_column": result_column,
            "is_available": True,  # Placeholder
            "existing_calculation": None
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))