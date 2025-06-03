# app/features/calculations/schemas.py
"""Pydantic schemas for refactored calculations API"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from .models import AggregationFunction, SourceModel, GroupLevel

class CalculationCreateRequest(BaseModel):
    """Request model for creating calculations"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    aggregation_function: AggregationFunction
    source_model: SourceModel
    source_field: str = Field(..., min_length=1, max_length=100)
    group_level: GroupLevel
    weight_field: Optional[str] = Field(None, max_length=100, description="Required for weighted averages")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Total Ending Balance",
                "description": "Sum of all tranche ending balance amounts",
                "aggregation_function": "SUM",
                "source_model": "TrancheBal",
                "source_field": "tr_end_bal_amt",
                "group_level": "deal"
            }
        }

class CalculationResponse(BaseModel):
    """Response model for calculation definitions"""
    id: int
    name: str
    description: Optional[str]
    aggregation_function: AggregationFunction
    source_model: SourceModel
    source_field: str
    group_level: GroupLevel
    weight_field: Optional[str]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]

    class Config:
        from_attributes = True
