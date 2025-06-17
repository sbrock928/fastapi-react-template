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
    result_column_name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$", 
                                   description="Column name in the result dataset")
    group_level: Optional[str] = Field(None, description="Calculation level: 'deal' or 'tranche'")
    tranche_mappings: Dict[str, List[str]] = Field(default={}, description="Mapping of tranche suffixes to tr_id values")
    
    @field_validator("variable_pattern")
    @classmethod 
    def validate_variable_pattern(cls, v):
        """Validate variable pattern format"""
        if not v or not v.strip():
            raise ValueError("variable_pattern cannot be empty")
        
        return v.strip()
    
    @field_validator("group_level")
    @classmethod
    def validate_group_level(cls, v):
        """Validate group level"""
        if v is not None and v not in ['deal', 'tranche']:
            raise ValueError("group_level must be 'deal' or 'tranche'")
        return v
    
    @field_validator("tranche_mappings")
    @classmethod
    def validate_tranche_mappings(cls, v):
        """Validate tranche mappings structure"""
        # Allow empty tranche mappings for deal-level calculations
        if not v:
            return v
        
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
    result_column_name: Optional[str] = Field(None, pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$")
    group_level: Optional[str] = Field(None, description="Calculation level: 'deal' or 'tranche'")
    tranche_mappings: Optional[Dict[str, List[str]]] = Field(None)
    
    @field_validator("variable_pattern")
    @classmethod
    def validate_variable_pattern(cls, v):
        """Validate variable pattern format if provided"""
        if v is not None:
            if not v.strip():
                raise ValueError("variable_pattern cannot be empty")
            # Note: We can't validate tranche_suffix requirement here because
            # we don't have access to group_level in field validation
            # This validation will be done at the service layer
            return v.strip()
        return v
    
    @field_validator("group_level")
    @classmethod
    def validate_group_level(cls, v):
        """Validate group level if provided"""
        if v is not None and v not in ['deal', 'tranche']:
            raise ValueError("group_level must be 'deal' or 'tranche'")
        return v


class CDIVariableResponse(BaseModel):
    """Schema for CDI variable calculation responses"""
    id: int
    name: str
    description: Optional[str]
    variable_pattern: str
    result_column_name: str
    group_level: str = Field(..., description="Calculation level: 'deal' or 'tranche'")
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
    record_count: int = Field(..., description="Number of result records returned")
    group_level: str = Field(..., description="Calculation level: 'deal' or 'tranche'")
    data: List[Dict[str, Any]] = Field(..., description="Result data as list of dictionaries")
    execution_time_ms: Optional[float] = Field(None, description="Execution time in milliseconds")
    
    class Config:
        from_attributes = True


class CDIVariableConfigResponse(BaseModel):
    """Schema for CDI variable configuration data"""
    available_patterns: List[str] = Field(..., description="Available variable patterns")
    default_tranche_mappings: Dict[str, List[str]] = Field(..., description="Default tranche mappings")
    variable_types: List[str] = Field(..., description="Common variable types")
    deal_level_examples: Optional[List[str]] = Field(default=[], description="Example deal-level patterns")
    tranche_level_examples: Optional[List[str]] = Field(default=[], description="Example tranche-level patterns")
    
    class Config:
        from_attributes = True


class CDIVariableSummary(BaseModel):
    """Schema for CDI variable calculation summaries"""
    id: int
    name: str
    result_column_name: str
    tranche_count: int = Field(..., description="Number of tranche types configured")
    created_by: str
    created_at: datetime
    is_active: bool


class CDIVariableValidationRequest(BaseModel):
    """Schema for validating CDI variable configurations"""
    variable_pattern: str
    group_level: str = Field(..., description="Calculation level: 'deal' or 'tranche'")
    tranche_mappings: Dict[str, List[str]] = Field(default={}, description="Tranche mappings (required for tranche-level)")
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


# ===== DISCOVERY AND ANALYSIS SCHEMAS =====

class CDIVariableDiscoveryRequest(BaseModel):
    """Schema for discovering CDI variables in the datawarehouse"""
    cycle_code: int = Field(..., description="Cycle code to search in")
    deal_numbers: List[int] = Field(..., min_length=1, max_length=100, description="Deal numbers to analyze")
    pattern_prefix: str = Field(default="#RPT_", description="Variable name prefix to search for")

class CDIVariableDiscoveryResponse(BaseModel):
    """Schema for CDI variable discovery results"""
    cycle_code: int
    deal_count: int
    discovered_variables: List[str] = Field(..., description="All discovered variable names")
    deal_level_candidates: List[str] = Field(..., description="Variables that appear to be deal-level")
    tranche_level_candidates: List[str] = Field(..., description="Variables that appear to be tranche-level")
    analysis_summary: Dict[str, Any] = Field(..., description="Summary statistics")

class CDIVariableLevelAnalysis(BaseModel):
    """Schema for analyzing whether a variable is deal or tranche level"""
    variable_name: str
    direct_records: int = Field(..., description="Number of direct CDI records found")
    tranche_joined_records: int = Field(..., description="Number of records that can join to tranches")
    suggested_level: str = Field(..., description="Suggested level: deal_level, tranche_level, mixed_or_deal_level, no_data, unknown")
    analysis: Dict[str, Any] = Field(..., description="Detailed analysis results")

# Updated variable type constants
DEAL_LEVEL_VARIABLE_TYPES = [
    {"value": "deal_summary", "label": "Deal Summary", "pattern": "#RPT_DEAL_TOTAL"},
    {"value": "deal_payment_info", "label": "Deal Payment Info", "pattern": "#RPT_DEAL_PAYMENT_DATE"},
    {"value": "deal_status", "label": "Deal Status", "pattern": "#RPT_DEAL_STATUS"},
]

TRANCHE_LEVEL_VARIABLE_TYPES = [
    {"value": "investment_income", "label": "Investment Income", "pattern": "#RPT_RRI_{tranche_suffix}"},
    {"value": "excess_interest", "label": "Excess Interest", "pattern": "#RPT_EXC_{tranche_suffix}"},
    {"value": "fees", "label": "Fees", "pattern": "#RPT_FEES_{tranche_suffix}"},
    {"value": "principal", "label": "Principal", "pattern": "#RPT_PRINC_{tranche_suffix}"},
    {"value": "interest", "label": "Interest", "pattern": "#RPT_INT_{tranche_suffix}"},
]

ALL_VARIABLE_TYPES = DEAL_LEVEL_VARIABLE_TYPES + TRANCHE_LEVEL_VARIABLE_TYPES