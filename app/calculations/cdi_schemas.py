# app/calculations/cdi_schemas.py
"""Pydantic schemas for CDI Variable calculations"""

from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Optional, Any
from datetime import datetime


class CDIVariableBase(BaseModel):
    """Base schema for CDI variable calculations"""
    name: str = Field(..., min_length=1, max_length=100, description="Display name for the calculation")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")
    variable_pattern: str = Field(..., description="Pattern for CDI variable names, e.g., '#RPT_RRI_{tranche_suffix}'")
    variable_type: str = Field(..., description="Type identifier, e.g., 'investment_income', 'excess_interest'")
    result_column_name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$", 
                                   description="Column name in the result dataset")
    tranche_mappings: Dict[str, List[str]] = Field(..., description="Mapping of tranche suffixes to tr_id values")
    
    @field_validator("variable_pattern")
    @classmethod 
    def validate_variable_pattern(cls, v):
        """Validate variable pattern format"""
        if not v or not v.strip():
            raise ValueError("variable_pattern cannot be empty")
        
        if "{tranche_suffix}" not in v:
            raise ValueError("variable_pattern must contain '{tranche_suffix}' placeholder")
        
        return v.strip()
    
    @field_validator("tranche_mappings")
    @classmethod
    def validate_tranche_mappings(cls, v):
        """Validate tranche mappings structure"""
        if not v:
            raise ValueError("tranche_mappings cannot be empty")
        
        for suffix, tr_ids in v.items():
            if not suffix or not suffix.strip():
                raise ValueError("Tranche suffix cannot be empty")
            if not tr_ids or not isinstance(tr_ids, list):
                raise ValueError(f"Tranche mapping for '{suffix}' must be a non-empty list")
            if not all(isinstance(tr_id, str) and tr_id.strip() for tr_id in tr_ids):
                raise ValueError(f"All tr_id values for '{suffix}' must be non-empty strings")
        
        return v


class CDIVariableCreate(CDIVariableBase):
    """Schema for creating CDI variable calculations"""
    pass


class CDIVariableUpdate(BaseModel):
    """Schema for updating CDI variable calculations"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    variable_pattern: Optional[str] = Field(None)
    variable_type: Optional[str] = Field(None)
    result_column_name: Optional[str] = Field(None, pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$")
    tranche_mappings: Optional[Dict[str, List[str]]] = Field(None)
    
    @field_validator("variable_pattern")
    @classmethod
    def validate_variable_pattern(cls, v):
        """Validate variable pattern format if provided"""
        if v is not None:
            if not v.strip():
                raise ValueError("variable_pattern cannot be empty")
            if "{tranche_suffix}" not in v:
                raise ValueError("variable_pattern must contain '{tranche_suffix}' placeholder")
            return v.strip()
        return v


class CDIVariableResponse(BaseModel):
    """Schema for CDI variable calculation responses"""
    id: int
    name: str
    description: Optional[str]
    variable_pattern: str
    variable_type: str
    result_column_name: str
    tranche_mappings: Dict[str, List[str]]
    created_by: str
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


class CDIVariableExecutionRequest(BaseModel):
    """Schema for executing CDI variable calculations"""
    calculation_id: int = Field(..., description="ID of the CDI variable calculation")
    cycle_code: int = Field(..., description="Cycle code to execute for")
    deal_numbers: List[int] = Field(..., min_length=1, description="List of deal numbers to include")
    
    @field_validator("deal_numbers")
    @classmethod
    def validate_deal_numbers(cls, v):
        """Validate deal numbers list"""
        if not v:
            raise ValueError("deal_numbers cannot be empty")
        if len(v) > 1000:  # Reasonable limit
            raise ValueError("Too many deal numbers (max 1000)")
        if not all(isinstance(deal, int) and deal > 0 for deal in v):
            raise ValueError("All deal numbers must be positive integers")
        return v


class CDIVariableExecutionResponse(BaseModel):
    """Schema for CDI variable calculation execution results"""
    calculation_id: int
    calculation_name: str
    cycle_code: int
    deal_count: int
    tranche_count: int
    data: List[Dict[str, Any]] = Field(..., description="Result data as list of dictionaries")
    execution_time_ms: Optional[float] = Field(None, description="Execution time in milliseconds")
    
    class Config:
        from_attributes = True


class CDIVariableConfigResponse(BaseModel):
    """Schema for CDI variable configuration data"""
    available_patterns: List[str] = Field(..., description="Available variable patterns")
    default_tranche_mappings: Dict[str, List[str]] = Field(..., description="Default tranche mappings")
    variable_types: List[str] = Field(..., description="Common variable types")
    
    class Config:
        from_attributes = True


class CDIVariableSummary(BaseModel):
    """Schema for CDI variable calculation summaries"""
    id: int
    name: str
    variable_type: str
    result_column_name: str
    tranche_count: int = Field(..., description="Number of tranche types configured")
    created_by: str
    created_at: datetime
    is_active: bool


class CDIVariableValidationRequest(BaseModel):
    """Schema for validating CDI variable configurations"""
    variable_pattern: str
    tranche_mappings: Dict[str, List[str]]
    cycle_code: int = Field(..., description="Cycle code to test against")
    sample_deal_numbers: List[int] = Field(..., min_length=1, max_length=10, 
                                          description="Sample deal numbers for validation")


class CDIVariableValidationResponse(BaseModel):
    """Schema for CDI variable validation results"""
    is_valid: bool
    validation_results: Dict[str, Any] = Field(..., description="Detailed validation results")
    sample_data_count: int = Field(..., description="Number of sample records found")
    warnings: List[str] = Field(default=[], description="Validation warnings")
    errors: List[str] = Field(default=[], description="Validation errors")


# ===== BULK OPERATION SCHEMAS =====

class CDIVariableBulkCreateRequest(BaseModel):
    """Schema for creating multiple CDI variable calculations at once"""
    calculations: List[CDIVariableCreate] = Field(..., min_length=1, max_length=50)
    created_by: str = Field(..., description="User creating the calculations")


class CDIVariableBulkCreateResponse(BaseModel):
    """Schema for bulk creation results"""
    created_count: int
    failed_count: int
    created_calculations: List[CDIVariableResponse]
    failures: List[Dict[str, str]] = Field(default=[], description="Failed calculations with error messages")


# ===== HELPER SCHEMAS =====

class TrancheMapping(BaseModel):
    """Schema for individual tranche mapping"""
    suffix: str = Field(..., description="Tranche suffix (e.g., 'M1', 'B1')")
    tr_ids: List[str] = Field(..., min_length=1, description="List of tr_id values")
    description: Optional[str] = Field(None, description="Optional description of this mapping")


class VariablePatternInfo(BaseModel):
    """Schema for variable pattern information"""
    pattern: str = Field(..., description="Variable pattern template")
    description: str = Field(..., description="Description of what this pattern represents")
    examples: List[str] = Field(..., description="Example variable names generated from this pattern")
    common_variable_type: str = Field(..., description="Commonly used variable_type for this pattern")