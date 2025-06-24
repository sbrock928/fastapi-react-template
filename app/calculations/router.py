# app/calculations/router.py
"""Clean API router for the unified calculation system"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text  # Add this import for raw SQL execution
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
from .field_introspection import FieldIntrospectionService

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
    
    # Get available models dynamically
    source_models = FieldIntrospectionService.get_available_models()
    
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
    
    # Get available fields dynamically through introspection
    static_fields = FieldIntrospectionService.get_available_fields()
    
    return {
        "aggregation_functions": aggregation_functions,
        "source_models": source_models,
        "group_levels": group_levels,
        "static_fields": static_fields
    }


# ===== PLACEHOLDERS ENDPOINT =====

@router.get("/placeholders", response_model=PlaceholderListResponse)
def get_available_placeholders(
    service: UnifiedCalculationService = Depends(get_unified_calculation_service)
):
    """Get available SQL placeholders for system calculations"""
    try:
        placeholders = service.get_available_placeholders()
        return PlaceholderListResponse(placeholders=placeholders)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving placeholders: {str(e)}")


# ===== STATIC FIELD ENDPOINTS =====

@router.get("/static-fields")
def get_static_fields(
    model: Optional[str] = Query(None, description="Filter by model name")
):
    """Get available static fields dynamically from schema introspection"""
    try:
        return FieldIntrospectionService.get_available_fields(model_filter=model)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving static fields: {str(e)}")


@router.get("/static-fields/by-model/{model_name}")
def get_static_fields_by_model(model_name: str):
    """Get available static fields for a specific model - used by frontend dropdown"""
    try:
        # Validate model exists
        available_models = [model["value"] for model in FieldIntrospectionService.get_available_models()]
        if model_name.lower() not in available_models:
            raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found. Available models: {available_models}")
        
        fields = FieldIntrospectionService.get_available_fields(model_filter=model_name.lower())
        
        # Format for frontend dropdown - include both field path and display name
        formatted_fields = []
        for field in fields:
            formatted_fields.append({
                "value": field["field_path"],
                "label": f"{field['name']} ({field['field_path']})",
                "description": field["description"],
                "type": field["type"],
                "format": field.get("format"),
                "model": field["model"],
                "nullable": field.get("nullable", True)
            })
        
        return {
            "model": model_name.lower(),
            "fields": formatted_fields,
            "count": len(formatted_fields)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving fields for model '{model_name}': {str(e)}")


@router.get("/static-fields/{field_path:path}")
def get_static_field_by_path(field_path: str):
    """Get static field information by path"""
    try:
        field = FieldIntrospectionService.get_field_by_path(field_path)
        if field:
            return field
        else:
            raise HTTPException(status_code=404, detail=f"Static field '{field_path}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving field: {str(e)}")


@router.get("/models")
def get_available_models():
    """Get available data models for field selection"""
    try:
        return FieldIntrospectionService.get_available_models()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving models: {str(e)}")


@router.get("/fields-by-model")
def get_fields_grouped_by_model():
    """Get all fields grouped by their source model"""
    try:
        return FieldIntrospectionService.get_fields_by_model()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving fields by model: {str(e)}")


@router.post("/validate-field")
def validate_field_path(request: Dict[str, str]):
    """Validate if a field path exists in the schema"""
    try:
        field_path = request.get("field_path")
        if not field_path:
            raise HTTPException(status_code=400, detail="field_path is required")
        
        return FieldIntrospectionService.validate_field_path(field_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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
        return service.get_user_calculation_usage(calc_id, report_scope)
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
        return service.get_calculation_usage(calc_id, calc_type)
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
        return service.get_system_calculation_usage(calc_id, report_scope)
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


@router.delete("/system/{calc_id}")
def delete_system_calculation(
    calc_id: int,
    service: UnifiedCalculationService = Depends(get_report_execution_service)
):
    """Delete a system calculation"""
    try:
        success = service.delete_calculation(calc_id)
        if not success:
            raise HTTPException(status_code=404, detail="System calculation not found")
        return {"message": "System calculation deleted successfully"}
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


@router.post("/execute-separate")
def execute_report_separately(
    request: Dict[str, Any],
    dw_db: Session = Depends(get_dw_db),
    config_db: Session = Depends(get_db)
):
    """Execute calculations separately and merge results - with better error handling"""
    try:
        # Parse request
        cycle_code = request.get("cycle_code")
        deal_tranche_map = request.get("deal_tranche_map", {})
        report_scope = request.get("report_scope", "TRANCHE")
        calculation_requests = request.get("calculation_requests", [])
        
        if not cycle_code:
            raise HTTPException(status_code=400, detail="cycle_code is required")
        
        if not calculation_requests:
            raise HTTPException(status_code=400, detail="calculation_requests cannot be empty")
        
        # FIXED: Convert cycle_code to integer to prevent type errors in arithmetic operations
        try:
            cycle_code_int = int(cycle_code)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail=f"Invalid cycle_code: {cycle_code}. Must be an integer.")
        
        # Convert deal_tranche_map keys to integers
        normalized_deal_map = {}
        for deal_key, tranches in deal_tranche_map.items():
            try:
                deal_int = int(deal_key)
                normalized_deal_map[deal_int] = tranches if isinstance(tranches, list) else []
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail=f"Invalid deal ID: {deal_key}")
        
        # Import and set up resolver components
        from .resolver import EnhancedCalculationResolver, CalculationRequest, QueryFilters
        
        # Convert calculation requests
        calc_requests = []
        for req in calculation_requests:
            calc_id = req.get("calc_id")
            alias = req.get("alias", str(calc_id))
            calc_requests.append(CalculationRequest(calc_id=calc_id, alias=alias))
        
        # Set up filters with integer cycle_code
        filters = QueryFilters(
            deal_tranche_map=normalized_deal_map,
            cycle_code=cycle_code_int,  # Now properly converted to integer
            report_scope=report_scope
        )
        
        # Execute using separate execution approach
        resolver = EnhancedCalculationResolver(dw_db, config_db)
        result = resolver.resolve_report_separately(calc_requests, filters)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing report separately: {str(e)}")


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
def preview_single_calculation(
    request: Dict[str, Any],
    service: UnifiedCalculationService = Depends(get_report_execution_service)
):
    """Preview SQL for a single calculation using the same logic as report previews"""
    try:
        # Extract required parameters
        calculation_request = request.get("calculation_request", {})
        deal_tranche_map = request.get("deal_tranche_map", {})
        cycle_code = request.get("cycle_code")
        
        calc_type = calculation_request.get("calc_type")
        calc_id = calculation_request.get("calc_id")
        
        if not calc_type or not calc_id:
            raise HTTPException(status_code=400, detail="calc_type and calc_id are required in calculation_request")
        
        # Convert deal_tranche_map keys to integers if they're strings
        normalized_deal_map = {}
        for deal_key, tranches in deal_tranche_map.items():
            try:
                deal_int = int(deal_key)
                normalized_deal_map[deal_int] = tranches if isinstance(tranches, list) else []
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail=f"Invalid deal ID in deal_tranche_map: {deal_key}")
        
        # Use the same service method that report previews use
        try:
            preview_result = service.preview_calculation(
                calc_id=calc_id,
                deal_tranche_map=normalized_deal_map,
                cycle_code=cycle_code,
                report_scope="TRANCHE"
            )
            
            # Extract the SQL and other data from the resolver response
            # The resolver returns the same format as report execution
            if "sql" in preview_result:
                sql_preview = preview_result["sql"]
                
                # Get calculation details from the database
                calc_response = service.get_calculation_by_id(calc_id)
                if not calc_response:
                    raise HTTPException(status_code=404, detail=f"Calculation with ID {calc_id} not found")
                
                return {
                    "sql": sql_preview,
                    "sql_preview": sql_preview,  # Both fields for compatibility
                    "calculation_type": calc_response.calculation_type.value if calc_response.calculation_type else "unknown",
                    "group_level": calc_response.group_level.value if calc_response.group_level else "unknown",
                    "calculation_name": calc_response.name,
                    "columns": preview_result.get("columns", []),
                    "parameters_used": preview_result.get("parameter_injections", {}).get("parameter_values", {}),
                    "parameters": {
                        "deal_tranche_map": normalized_deal_map,
                        "cycle_code": cycle_code
                    },
                    "placeholders_used": preview_result.get("placeholders_used", []),
                    "debug_info": preview_result.get("debug_info", {})
                }
            elif "error" in preview_result:
                # Return error with SQL fallback
                return {
                    "sql": f"-- Error: {preview_result['error']}",
                    "sql_preview": f"-- Error: {preview_result['error']}",
                    "error": preview_result["error"],
                    "calculation_type": "error",
                    "group_level": "unknown",
                    "calculation_name": "Error",
                    "columns": [],
                    "parameters_used": {},
                    "parameters": {
                        "deal_tranche_map": normalized_deal_map,
                        "cycle_code": cycle_code
                    },
                    "debug_info": preview_result.get("debug_info", {})
                }
            else:
                # Fallback if no SQL found in response
                raise Exception("No SQL found in preview result")
                
        except Exception as service_error:
            # If service fails, return a meaningful error with fallback SQL
            error_message = f"Failed to generate SQL preview: {str(service_error)}"
            return {
                "sql": f"-- Service Error: {error_message}",
                "sql_preview": f"-- Service Error: {error_message}",
                "error": error_message,
                "calculation_type": "error",
                "group_level": "unknown",
                "calculation_name": "Error",
                "columns": [],
                "parameters_used": {},
                "parameters": {
                    "deal_tranche_map": normalized_deal_map,
                    "cycle_code": cycle_code
                },
                "debug_info": {
                    "calc_id": calc_id,
                    "calc_type": calc_type,
                    "cycle_code": cycle_code,
                    "deal_tranche_map": normalized_deal_map,
                    "error": str(service_error)
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to preview calculation: {str(e)}")


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
        
        # Use the service to look up the calculation
        calculation = service.get_user_calculation_by_source_field(decoded_source_field)
        
        if calculation:
            return {
                "success": True,
                "calculation": calculation.model_dump(),
                "calculation_id": calculation.id,
                "source_field": decoded_source_field
            }
        else:
            raise HTTPException(
                status_code=404, 
                detail=f"No user calculation found with source_field '{decoded_source_field}'"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error looking up user calculation: {str(e)}")


@router.get("/system/by-result-column/{result_column}")
def get_system_calculation_by_result_column(
    result_column: str,
    service: UnifiedCalculationService = Depends(get_report_execution_service)
):
    """Get a system calculation by result_column_name (used with new calculation_id format)"""
    try:
        # URL decode the result_column parameter
        decoded_result_column = unquote(result_column)
        
        # Use the service to look up the calculation
        calculation = service.get_system_calculation_by_result_column(decoded_result_column)
        
        if calculation:
            return {
                "success": True,
                "calculation": calculation.model_dump(),
                "calculation_id": calculation.id,
                "result_column": decoded_result_column
            }
        else:
            raise HTTPException(
                status_code=404, 
                detail=f"No system calculation found with result_column '{decoded_result_column}'"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error looking up system calculation: {str(e)}")


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


# ===== REAL PARAMETER INJECTION ENDPOINT =====

@router.post("/get-real-parameters")
def get_real_parameters_for_preview(request: Dict[str, Any]):
    """Get real parameter values from deal_tranche_map for SQL preview (instead of placeholders)"""
    try:
        # Extract parameters from request
        deal_tranche_map = request.get("deal_tranche_map", {})
        cycle_code = request.get("cycle_code")
        
        if not cycle_code:
            raise HTTPException(status_code=400, detail="cycle_code is required")
        
        # FIXED: Convert cycle_code to integer to prevent type errors in arithmetic operations
        try:
            cycle_code_int = int(cycle_code)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail=f"Invalid cycle_code: {cycle_code}. Must be an integer.")
        
        # Convert deal_tranche_map keys to integers if they're strings
        normalized_deal_map = {}
        for deal_key, tranches in deal_tranche_map.items():
            try:
                deal_int = int(deal_key)
                normalized_deal_map[deal_int] = tranches if isinstance(tranches, list) else []
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail=f"Invalid deal ID in deal_tranche_map: {deal_key}")
        
        # Import the resolver components
        from .resolver import DynamicParameterInjector, QueryFilters
        
        # Create the filters object with the real data
        filters = QueryFilters(
            deal_tranche_map=normalized_deal_map,
            cycle_code=cycle_code_int,  # Now properly converted to integer
            report_scope="TRANCHE"  # Default to TRANCHE for most detailed view
        )
        
        # Create the parameter injector with real data
        injector = DynamicParameterInjector(filters)
        
        # Get the real parameter values that would be used in queries
        real_parameters = injector.get_parameter_values()
        
        return {
            "success": True,
            "real_parameters": real_parameters,
            "input_filters": {
                "deal_tranche_map": normalized_deal_map,
                "cycle_code": cycle_code_int
            },
            "parameter_descriptions": {
                "current_cycle": "The selected reporting cycle code",
                "previous_cycle": "The previous reporting cycle (current_cycle - 1)",
                "cycle_minus_2": "Two cycles before current (current_cycle - 2)",
                "deal_filter": "WHERE clause for CDI tables with selected deal numbers",
                "standard_deal_filter": "WHERE clause for standard tables with selected deal numbers",
                "deal_tranche_filter": "Combined WHERE clause for deal and tranche selections",
                "deal_numbers": "Comma-separated list of selected deal numbers",
                "tranche_ids": "Comma-separated list of selected tranche IDs (quoted for SQL)"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating real parameters: {str(e)}")


@router.post("/replace-placeholders-with-real-values")
def replace_placeholders_with_real_values(request: Dict[str, Any]):
    """Replace SQL placeholders with real values from deal_tranche_map"""
    try:
        # Extract parameters from request
        sql_text = request.get("sql_text", "").strip()
        deal_tranche_map = request.get("deal_tranche_map", {})
        cycle_code = request.get("cycle_code")
        
        if not sql_text:
            raise HTTPException(status_code=400, detail="sql_text is required")
        
        if not cycle_code:
            raise HTTPException(status_code=400, detail="cycle_code is required")
        
        # FIXED: Convert cycle_code to integer to prevent type errors in arithmetic operations
        try:
            cycle_code_int = int(cycle_code)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail=f"Invalid cycle_code: {cycle_code}. Must be an integer.")
        
        # Convert deal_tranche_map keys to integers if they're strings
        normalized_deal_map = {}
        for deal_key, tranches in deal_tranche_map.items():
            try:
                deal_int = int(deal_key)
                normalized_deal_map[deal_int] = tranches if isinstance(tranches, list) else []
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail=f"Invalid deal ID in deal_tranche_map: {deal_key}")
        
        # Import the resolver components
        from .resolver import DynamicParameterInjector, QueryFilters
        from .models import Calculation, CalculationType, GroupLevel
        
        # Create the filters object with the real data
        filters = QueryFilters(
            deal_tranche_map=normalized_deal_map,
            cycle_code=cycle_code_int,  # Now properly converted to integer
            report_scope="TRANCHE"  # Default to TRANCHE for most detailed view
        )
        
        # Create the parameter injector with real data
        injector = DynamicParameterInjector(filters)
        
        # Create a mock calculation object for the injection process
        # This is needed because inject_parameters expects a Calculation object
        class MockCalculation:
            def __init__(self, sql):
                self.raw_sql = sql
            
            def get_used_placeholders(self):
                """Extract placeholders from SQL"""
                import re
                placeholders = set()
                placeholder_pattern = r'\{([^}]+)\}'
                matches = re.findall(placeholder_pattern, self.raw_sql)
                for match in matches:
                    placeholders.add(match)
                return placeholders
        
        mock_calc = MockCalculation(sql_text)
        
        # Inject the real parameter values
        sql_with_real_values = injector.inject_parameters(sql_text, mock_calc)
        
        # Get the parameter values that were used
        parameter_values = injector.get_parameter_values()
        used_placeholders = mock_calc.get_used_placeholders();
        
        return {
            "success": True,
            "original_sql": sql_text,
            "sql_with_real_values": sql_with_real_values,
            "parameter_values_used": {k: v for k, v in parameter_values.items() if k in used_placeholders},
            "all_available_parameters": parameter_values,
            "placeholders_found": list(used_placeholders),
            "input_filters": {
                "deal_tranche_map": normalized_deal_map,
                "cycle_code": cycle_code
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error replacing placeholders: {str(e)}")


# ===== PLACEHOLDERS ENDPOINT (ENHANCED) =====

@router.post("/execute-raw-sql")
def execute_raw_sql(
    request: Dict[str, Any],
    dw_db: Session = Depends(get_dw_db),
    config_db: Session = Depends(get_db)
):
    """Execute raw SQL from field introspection with real parameter values"""
    try:
        # Extract parameters from request
        sql_text = request.get("sql_text", "").strip()
        deal_tranche_map = request.get("deal_tranche_map", {})
        cycle_code = request.get("cycle_code")
        alias = request.get("alias", "raw_sql_result")
        
        if not sql_text:
            raise HTTPException(status_code=400, detail="sql_text is required")
        
        if not cycle_code:
            raise HTTPException(status_code=400, detail="cycle_code is required")
        
        # Convert cycle_code to integer
        try:
            cycle_code_int = int(cycle_code)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail=f"Invalid cycle_code: {cycle_code}. Must be an integer.")
        
        # Convert deal_tranche_map keys to integers
        normalized_deal_map = {}
        for deal_key, tranches in deal_tranche_map.items():
            try:
                deal_int = int(deal_key)
                normalized_deal_map[deal_int] = tranches if isinstance(tranches, list) else []
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail=f"Invalid deal ID: {deal_key}")
        
        # Import resolver components
        from .resolver import DynamicParameterInjector, QueryFilters
        
        # Create filters
        filters = QueryFilters(
            deal_tranche_map=normalized_deal_map,
            cycle_code=cycle_code_int,
            report_scope="TRANCHE"
        )
        
        # Create parameter injector and inject real values
        injector = DynamicParameterInjector(filters)
        
        # Create a mock calculation object for placeholder extraction
        class MockCalculation:
            def __init__(self, sql):
                self.raw_sql = sql
            
            def get_used_placeholders(self):
                import re
                placeholders = set()
                placeholder_pattern = r'\{([^}]+)\}'
                matches = re.findall(placeholder_pattern, self.raw_sql)
                for match in matches:
                    placeholders.add(match)
                return placeholders
        
        mock_calc = MockCalculation(sql_text)
        sql_with_real_values = injector.inject_parameters(sql_text, mock_calc)
        
        # Execute the SQL
        try:
            result = dw_db.execute(text(sql_with_real_values))  # Wrap with text()
            rows = result.fetchall()
            
            # Convert to list of dictionaries
            if rows:
                columns = list(result.keys())
                data = [dict(zip(columns, row)) for row in rows]
            else:
                data = []
            
            return {
                "success": True,
                "alias": alias,
                "data": data,
                "row_count": len(data),
                "columns": list(result.keys()) if rows else [],
                "sql_executed": sql_with_real_values,
                "original_sql": sql_text,
                "parameter_values_used": injector.get_parameter_values(),
                "placeholders_found": list(mock_calc.get_used_placeholders())
            }
            
        except Exception as sql_error:
            return {
                "success": False,
                "alias": alias,
                "error": f"SQL execution failed: {str(sql_error)}",
                "sql_attempted": sql_with_real_values,
                "original_sql": sql_text,
                "parameter_values_used": injector.get_parameter_values(),
                "placeholders_found": list(mock_calc.get_used_placeholders())
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing raw SQL: {str(e)}")