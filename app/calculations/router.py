# app/features/calculations/router.py
"""Refactored calculations router using unified query engine"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.dependencies import get_db, get_query_engine
from app.core.exceptions import CalculationNotFoundError, CalculationAlreadyExistsError, InvalidCalculationError
from app.shared.query_engine import QueryEngine
from .service import CalculationService
from .schemas import CalculationCreateRequest, CalculationResponse

router = APIRouter()

def get_calculation_service(config_db: Session = Depends(get_db)) -> CalculationService:
    """Get calculation service for config-only operations"""
    return CalculationService(config_db)

def get_calculation_service_with_preview(query_engine: QueryEngine = Depends(get_query_engine)) -> CalculationService:
    """Get calculation service with query engine for preview operations"""
    return CalculationService(query_engine.config_db, query_engine)

@router.get("/calculations/configuration")
async def get_calculation_configuration():
    """Get comprehensive calculation configuration including fields, functions, models, and levels"""
    
    # Aggregation functions available in the system (including RAW for non-aggregated fields)
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
            "label": "RAW - Individual field value",
            "description": "Show the actual field value for each row without aggregation",
            "category": "raw"
        }
    ]
    
    # Source models available for calculations
    source_models = [
        {
            "value": "Deal",
            "label": "Deal", 
            "description": "Base deal information"
        },
        {
            "value": "Tranche",
            "label": "Tranche",
            "description": "Tranche structure data"
        },
        {
            "value": "TrancheBal",
            "label": "TrancheBal",
            "description": "Tranche balance and performance data"
        }
    ]
    
    # Group levels for aggregation
    group_levels = [
        {
            "value": "deal",
            "label": "Deal Level",
            "description": "Aggregate to deal level"
        },
        {
            "value": "tranche", 
            "label": "Tranche Level",
            "description": "Aggregate to tranche level"
        }
    ]
    
    # Field metadata for each model
    field_mappings = {
        "Deal": [
            {
                "value": "dl_nbr",
                "label": "Deal Number",
                "type": "number",
                "description": "Unique identifier for the deal"
            }
        ],
        "Tranche": [
            {
                "value": "tr_id",
                "label": "Tranche ID", 
                "type": "string",
                "description": "Tranche identifier within the deal"
            },
            {
                "value": "dl_nbr",
                "label": "Deal Number",
                "type": "number", 
                "description": "Parent deal number"
            },
            {
                "value": "tr_cusip_id",
                "label": "Tranche CUSIP ID",
                "type": "string",
                "description": "CUSIP identifier for the tranche"
            }
        ],
        "TrancheBal": [
            {
                "value": "tr_end_bal_amt",
                "label": "Ending Balance Amount",
                "type": "currency",
                "description": "Outstanding principal balance at period end"
            },
            {
                "value": "tr_prin_rel_ls_amt", 
                "label": "Principal Release/Loss Amount",
                "type": "currency",
                "description": "Principal released or lost during the period"
            },
            {
                "value": "tr_pass_thru_rte",
                "label": "Pass Through Rate",
                "type": "percentage",
                "description": "Interest rate passed through to investors"
            },
            {
                "value": "tr_accrl_days",
                "label": "Accrual Days",
                "type": "number",
                "description": "Number of days in the accrual period"
            },
            {
                "value": "tr_int_dstrb_amt",
                "label": "Interest Distribution Amount", 
                "type": "currency",
                "description": "Interest distributed to investors"
            },
            {
                "value": "tr_prin_dstrb_amt",
                "label": "Principal Distribution Amount",
                "type": "currency", 
                "description": "Principal distributed to investors"
            },
            {
                "value": "tr_int_accrl_amt",
                "label": "Interest Accrual Amount",
                "type": "currency",
                "description": "Interest accrued during the period"
            },
            {
                "value": "tr_int_shtfl_amt",
                "label": "Interest Shortfall Amount",
                "type": "currency",
                "description": "Interest shortfall amount"
            },
            {
                "value": "cycle_cde",
                "label": "Cycle Code",
                "type": "number",
                "description": "Reporting cycle identifier (YYYYMM format)"
            }
        ]
    }
    
    return {
        "success": True,
        "data": {
            "aggregation_functions": aggregation_functions,
            "source_models": source_models,
            "group_levels": group_levels,
            "field_mappings": field_mappings
        },
        "message": "Calculation configuration retrieved successfully"
    }

@router.get("/calculations", response_model=List[CalculationResponse])
async def get_available_calculations(
    service: CalculationService = Depends(get_calculation_service),
    group_level: Optional[str] = Query(None, description="Filter by group level: 'deal', 'tranche'")
):
    """Get list of available calculations, optionally filtered by group level"""
    return await service.get_available_calculations(group_level)

@router.post("/calculations", response_model=CalculationResponse, status_code=201)
async def create_calculation(
    request: CalculationCreateRequest,
    service: CalculationService = Depends(get_calculation_service)
):
    """Create a new calculation"""
    try:
        return await service.create_calculation(request)
    except (CalculationAlreadyExistsError, InvalidCalculationError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/calculations/{calc_id}/preview-sql")
async def preview_calculation_sql(
    calc_id: int,
    service: CalculationService = Depends(get_calculation_service_with_preview),
    aggregation_level: str = Query("deal", description="Aggregation level: 'deal' or 'tranche'"),
    sample_deals: str = Query("101,102,103", description="Comma-separated sample deal numbers"),
    sample_tranches: str = Query("A,B", description="Comma-separated sample tranche IDs"),
    sample_cycle: int = Query(202404, description="Sample cycle code")
):
    """Preview SQL using unified query engine"""
    try:
        # Parse comma-separated values
        deal_list = [int(d.strip()) for d in sample_deals.split(',') if d.strip()]
        tranche_list = [t.strip() for t in sample_tranches.split(',') if t.strip()]
        
        return await service.preview_calculation_sql(
            calc_id, aggregation_level, deal_list, tranche_list, sample_cycle
        )
    except CalculationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/calculations/{calc_id}", response_model=CalculationResponse)
async def update_calculation(
    calc_id: int,
    request: CalculationCreateRequest,
    service: CalculationService = Depends(get_calculation_service)
):
    """Update an existing calculation"""
    try:
        return await service.update_calculation(calc_id, request)
    except CalculationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidCalculationError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/calculations/{calc_id}")
async def delete_calculation(
    calc_id: int,
    service: CalculationService = Depends(get_calculation_service)
):
    """Delete a calculation"""
    try:
        return await service.delete_calculation(calc_id)
    except CalculationNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))