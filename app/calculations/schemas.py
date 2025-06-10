# app/calculations/schemas.py
"""Updated Pydantic schemas for different calculation types."""

from pydantic import BaseModel, Field, validator
from typing import Optional, Union
from datetime import datetime
from .models import CalculationType, AggregationFunction, SourceModel, GroupLevel

# Base schemas
class CalculationBase(BaseModel):
    """Base schema for all calculations."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    group_level: GroupLevel

    class Config:
        from_attributes = True

# User Defined Calculation Schemas
class UserDefinedCalculationCreate(CalculationBase):
    """Schema for creating user-defined calculations."""
    aggregation_function: AggregationFunction
    source_model: SourceModel
    source_field: str = Field(..., min_length=1, max_length=100)
    weight_field: Optional[str] = Field(None, max_length=100)
    
    @validator('weight_field')
    def validate_weight_field_for_weighted_avg(cls, v, values):
        """Validate weight field is provided for weighted averages."""
        if values.get('aggregation_function') == AggregationFunction.WEIGHTED_AVG and not v:
            raise ValueError('weight_field is required for weighted average calculations')
        return v

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

# System SQL calculation schemas
class SystemSQLCalculationCreate(CalculationBase):
    """Schema for creating system SQL calculations."""
    raw_sql: str = Field(..., min_length=10, description="SQL query text")
    result_column_name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Issuer Type Classification",
                "description": "Categorizes deals by issuer type (GSE, Government, Private)",
                "group_level": "deal",
                "raw_sql": "SELECT deal.dl_nbr, CASE WHEN deal.issr_cde LIKE '%FHLMC%' THEN 'GSE' ELSE 'Private' END AS issuer_type FROM deal",
                "result_column_name": "issuer_type"
            }
        }

# Union type for creation requests
CalculationCreateRequest = Union[
    UserDefinedCalculationCreate,
    SystemSQLCalculationCreate
]

# Response schemas
class CalculationResponse(BaseModel):
    """Unified response schema for all calculation types."""
    id: int
    name: str
    description: Optional[str]
    calculation_type: CalculationType
    group_level: GroupLevel
    is_system_managed: bool
    
    # User-defined calculation fields
    aggregation_function: Optional[AggregationFunction] = None
    source_model: Optional[SourceModel] = None
    source_field: Optional[str] = None
    weight_field: Optional[str] = None
    
    # System SQL calculation fields
    raw_sql: Optional[str] = None
    result_column_name: Optional[str] = None
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]

    class Config:
        from_attributes = True

# Simplified schemas for specific types
class UserDefinedCalculationResponse(CalculationBase):
    """Response schema specifically for user-defined calculations."""
    id: int
    calculation_type: CalculationType = CalculationType.USER_DEFINED
    aggregation_function: AggregationFunction
    source_model: SourceModel
    source_field: str
    weight_field: Optional[str] = None
    is_system_managed: bool = False
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]

    class Config:
        from_attributes = True

class SystemSQLCalculationResponse(CalculationBase):
    """Response schema specifically for system SQL calculations."""
    id: int
    calculation_type: CalculationType = CalculationType.SYSTEM_SQL
    raw_sql: str
    result_column_name: str
    is_system_managed: bool = True
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]

    class Config:
        from_attributes = True

# Update schemas for editing
class UserDefinedCalculationUpdate(BaseModel):
    """Update schema for user-defined calculations."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    aggregation_function: Optional[AggregationFunction] = None
    source_model: Optional[SourceModel] = None
    source_field: Optional[str] = Field(None, min_length=1, max_length=100)
    weight_field: Optional[str] = Field(None, max_length=100)
    group_level: Optional[GroupLevel] = None

    class Config:
        from_attributes = True

# System calculations should not be updatable by users
class SystemCalculationUpdate(BaseModel):
    """Limited update schema for system calculations (admin use only)."""
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None

    class Config:
        from_attributes = True

# Available calculation schema for reporting (simplified)
class AvailableCalculation(BaseModel):
    """Schema for available calculations that can be selected for reports."""
    id: int
    name: str
    description: Optional[str] = None
    calculation_type: CalculationType
    group_level: GroupLevel
    category: str
    is_default: bool = False
    is_system_managed: bool
    
    # Display fields (computed)
    display_type: str  # "User Defined (SUM)", "System Field (number)", "System SQL"
    source_description: str  # "Deal.dl_nbr", "Custom SQL (issuer_type)", etc.

    class Config:
        from_attributes = True