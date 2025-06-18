"""Enhanced schemas for the unified calculation system with dynamic SQL parameter injection"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Set
from enum import Enum
import re

from .models import CalculationType, AggregationFunction, SourceModel, GroupLevel


class CalculationBase(BaseModel):
    """Base schema for calculation data"""
    name: str = Field(..., min_length=3, max_length=100, description="Calculation name")
    description: Optional[str] = Field(None, max_length=500, description="Calculation description")
    group_level: GroupLevel = Field(..., description="Aggregation level (deal or tranche)")


class UserAggregationCalculationCreate(CalculationBase):
    """Schema for creating user aggregation calculations"""
    calculation_type: CalculationType = Field(default=CalculationType.USER_AGGREGATION)
    aggregation_function: AggregationFunction = Field(..., description="Aggregation function to apply")
    source_model: SourceModel = Field(..., description="Source data model")
    source_field: str = Field(..., min_length=1, description="Source field name")
    weight_field: Optional[str] = Field(None, description="Weight field for weighted averages")
    
    @field_validator("weight_field")
    @classmethod
    def validate_weight_field(cls, v, info):
        """Validate weight field is provided for weighted averages"""
        if info.data.get("aggregation_function") == AggregationFunction.WEIGHTED_AVG and not v:
            raise ValueError("weight_field is required for weighted average calculations")
        return v


class SystemFieldCalculationCreate(CalculationBase):
    """Schema for creating system field calculations"""
    calculation_type: CalculationType = Field(default=CalculationType.SYSTEM_FIELD)
    field_path: str = Field(..., description="Field path (e.g., 'deal.dl_nbr')")
    
    @field_validator("field_path")
    @classmethod
    def validate_field_path(cls, v):
        """Validate field path format"""
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*$", v):
            raise ValueError("field_path must be in format 'model.field'")
        return v


class SystemSqlCalculationCreate(CalculationBase):
    """Schema for creating system SQL calculations with placeholder support"""
    calculation_type: CalculationType = Field(default=CalculationType.SYSTEM_SQL)
    raw_sql: str = Field(..., min_length=10, description="SQL query with placeholder support")
    result_column_name: str = Field(..., description="Name of the result column in the SQL")
    sql_parameters: Optional[Dict[str, Any]] = Field(default=None, description="SQL parameter configuration")
    
    @field_validator("result_column_name")
    @classmethod
    def validate_result_column_name(cls, v):
        """Validate result column name format"""
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", v):
            raise ValueError("result_column_name must be a valid SQL identifier")
        return v
    
    @field_validator("raw_sql")
    @classmethod
    def validate_raw_sql(cls, v):
        """Basic SQL validation"""
        if not v.strip():
            raise ValueError("raw_sql cannot be empty")
        
        # Check for dangerous operations
        dangerous_patterns = [
            r'\bDROP\b', r'\bDELETE\s+FROM\b', r'\bTRUNCATE\b',
            r'\bINSERT\s+INTO\b', r'\bUPDATE\s+.*\bSET\b', r'\bALTER\b',
            r'\bCREATE\b', r'\bEXEC\b', r'\bEXECUTE\b'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("SQL contains dangerous operations that are not allowed")
        
        return v.strip()


class CDIVariableCalculationCreate(CalculationBase):
    """Schema for creating CDI variable calculations"""
    calculation_type: CalculationType = Field(default=CalculationType.CDI_VARIABLE)
    variable_pattern: str = Field(..., description="CDI variable pattern (e.g., '#RPT_RRI_{tranche_suffix}')")
    result_column_name: str = Field(..., description="Name of the result column")
    tranche_mappings: Optional[Dict[str, List[str]]] = Field(default=None, description="Tranche suffix mappings")
    
    @field_validator("variable_pattern")
    @classmethod
    def validate_variable_pattern(cls, v, info):
        """Validate variable pattern format"""
        if not v.strip():
            raise ValueError("variable_pattern cannot be empty")
        
        group_level = info.data.get("group_level")
        if group_level == GroupLevel.TRANCHE and "{tranche_suffix}" not in v:
            raise ValueError("Tranche-level variable pattern must contain {tranche_suffix} placeholder")
        elif group_level == GroupLevel.DEAL and "{tranche_suffix}" in v:
            raise ValueError("Deal-level variable pattern should not contain {tranche_suffix} placeholder")
        
        return v.strip()


class CalculationUpdate(BaseModel):
    """Schema for updating calculations"""
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    group_level: Optional[GroupLevel] = None
    
    # User aggregation fields
    aggregation_function: Optional[AggregationFunction] = None
    source_model: Optional[SourceModel] = None
    source_field: Optional[str] = None
    weight_field: Optional[str] = None
    
    # System SQL fields
    raw_sql: Optional[str] = None
    result_column_name: Optional[str] = None
    sql_parameters: Optional[Dict[str, Any]] = None
    
    # Metadata
    metadata_config: Optional[Dict[str, Any]] = None


class CalculationResponse(BaseModel):
    """Schema for calculation responses"""
    id: int
    name: str
    description: Optional[str]
    calculation_type: CalculationType
    group_level: GroupLevel
    
    # User aggregation fields
    aggregation_function: Optional[AggregationFunction]
    source_model: Optional[SourceModel]
    source_field: Optional[str]
    weight_field: Optional[str]
    
    # System SQL fields
    raw_sql: Optional[str]
    result_column_name: Optional[str]
    sql_parameters: Optional[Dict[str, Any]]
    
    # Metadata and audit
    metadata_config: Optional[Dict[str, Any]]
    created_by: str
    approved_by: Optional[str]
    is_active: bool
    
    # Computed fields
    display_formula: str = Field(..., description="Human-readable formula")
    complexity_score: int = Field(..., description="Complexity score for sorting")
    used_placeholders: List[str] = Field(..., description="SQL placeholders used")
    required_models: List[str] = Field(..., description="Required data models")
    
    class Config:
        from_attributes = True


class CalculationPreviewRequest(BaseModel):
    """Schema for calculation preview requests"""
    calculation_id: int
    deal_tranche_map: Dict[int, List[str]] = Field(..., description="Deal to tranche mappings")
    cycle_code: int = Field(..., description="Reporting cycle")
    report_scope: Optional[str] = Field("TRANCHE", description="Report scope (DEAL or TRANCHE)")


class CalculationPreviewResponse(BaseModel):
    """Schema for calculation preview responses"""
    sql: str = Field(..., description="Generated SQL with parameters injected")
    calculation_type: str = Field(..., description="Type of calculation")
    group_level: str = Field(..., description="Aggregation level")
    alias: str = Field(..., description="Column alias")
    parameter_injections: Dict[str, Any] = Field(..., description="Parameter injection debug info")
    placeholders_used: List[str] = Field(..., description="Placeholders used in SQL")
    error: Optional[str] = Field(None, description="Error message if preview failed")


class SqlValidationRequest(BaseModel):
    """Schema for SQL validation requests"""
    sql_text: str = Field(..., min_length=1, description="SQL to validate")
    group_level: GroupLevel = Field(..., description="Expected group level")
    result_column_name: str = Field(..., description="Expected result column name")


class SqlValidationResult(BaseModel):
    """Schema for SQL validation results"""
    is_valid: bool = Field(..., description="Whether the SQL is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    has_ctes: bool = Field(default=False, description="Whether SQL contains CTEs")
    has_subqueries: bool = Field(default=False, description="Whether SQL contains subqueries")
    final_select_columns: List[str] = Field(default_factory=list, description="Columns in final SELECT")
    used_tables: List[str] = Field(default_factory=list, description="Tables used in SQL")
    placeholders_used: List[str] = Field(default_factory=list, description="Placeholders found in SQL")


class SqlValidationResponse(BaseModel):
    """Schema for SQL validation responses"""
    validation_result: SqlValidationResult


class PlaceholderInfo(BaseModel):
    """Schema for placeholder information"""
    name: str = Field(..., description="Placeholder name")
    description: str = Field(..., description="Placeholder description")
    example_value: str = Field(..., description="Example value")


class PlaceholderListResponse(BaseModel):
    """Schema for listing available placeholders"""
    placeholders: List[PlaceholderInfo]


class CalculationListResponse(BaseModel):
    """Schema for calculation list responses"""
    calculations: List[CalculationResponse]
    total_count: int
    active_count: int
    calculation_types: Dict[str, int] = Field(..., description="Count by calculation type")


class BulkCalculationOperation(BaseModel):
    """Schema for bulk operations on calculations"""
    calculation_ids: List[int] = Field(..., min_items=1, description="List of calculation IDs")
    operation: str = Field(..., description="Operation to perform (activate, deactivate, delete)")
    
    @field_validator("operation")
    @classmethod
    def validate_operation(cls, v):
        """Validate operation type"""
        valid_operations = ["activate", "deactivate", "delete", "approve"]
        if v not in valid_operations:
            raise ValueError(f"operation must be one of: {', '.join(valid_operations)}")
        return v


class BulkCalculationResponse(BaseModel):
    """Schema for bulk operation responses"""
    success_count: int = Field(..., description="Number of successful operations")
    failed_count: int = Field(..., description="Number of failed operations")
    failed_ids: List[int] = Field(default_factory=list, description="IDs that failed")
    errors: List[str] = Field(default_factory=list, description="Error messages")


# Report execution schemas
class ReportExecutionRequest(BaseModel):
    """Schema for report execution requests"""
    calculation_requests: List[Dict[str, Any]] = Field(..., description="List of calculation requests")
    deal_tranche_map: Dict[int, List[str]] = Field(..., description="Deal to tranche mappings")
    cycle_code: int = Field(..., description="Reporting cycle")
    report_scope: str = Field(..., description="Report scope (DEAL or TRANCHE)")


class ReportExecutionResponse(BaseModel):
    """Schema for report execution responses"""
    merged_data: List[Dict[str, Any]] = Field(..., description="Merged calculation results")
    unified_sql: str = Field(..., description="Generated unified SQL")
    debug_info: Dict[str, Any] = Field(..., description="Debug information")
    error: Optional[str] = Field(None, description="Error message if execution failed")


# Legacy compatibility schemas (for migration)
class LegacyCalculationCreate(BaseModel):
    """Legacy schema for backward compatibility during migration"""
    name: str
    description: Optional[str] = None
    function_type: str  # Maps to calculation_type
    level: str  # Maps to group_level
    source: Optional[str] = None  # Maps to source_model
    source_field: Optional[str] = None
    weight_field: Optional[str] = None
    
    def to_modern_schema(self) -> Dict[str, Any]:
        """Convert legacy schema to modern unified schema"""
        # Map legacy function_type to calculation_type
        type_mapping = {
            "SUM": CalculationType.USER_AGGREGATION,
            "AVG": CalculationType.USER_AGGREGATION,
            "COUNT": CalculationType.USER_AGGREGATION,
            "MIN": CalculationType.USER_AGGREGATION,
            "MAX": CalculationType.USER_AGGREGATION,
            "WEIGHTED_AVG": CalculationType.USER_AGGREGATION,
            "RAW": CalculationType.SYSTEM_FIELD,
            "SYSTEM_SQL": CalculationType.SYSTEM_SQL,
        }
        
        calc_type = type_mapping.get(self.function_type, CalculationType.USER_AGGREGATION)
        
        base_data = {
            "name": self.name,
            "description": self.description,
            "calculation_type": calc_type,
            "group_level": GroupLevel.DEAL if self.level == "deal" else GroupLevel.TRANCHE,
        }
        
        if calc_type == CalculationType.USER_AGGREGATION:
            base_data.update({
                "aggregation_function": AggregationFunction(self.function_type),
                "source_model": SourceModel(self.source) if self.source else None,
                "source_field": self.source_field,
                "weight_field": self.weight_field,
            })
        elif calc_type == CalculationType.SYSTEM_FIELD:
            base_data.update({
                "field_path": f"{self.source.lower()}.{self.source_field}" if self.source and self.source_field else "",
            })
        
        return base_data