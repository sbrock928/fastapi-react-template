# app/calculations/schemas.py
"""Pydantic schemas for the new separated calculation system"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Dict, Any, List, Union, Literal
from datetime import datetime
from enum import Enum
from .models import AggregationFunction, SourceModel, GroupLevel


# ===== USER CALCULATION SCHEMAS =====

class UserCalculationBase(BaseModel):
    """Base schema for user calculations"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    aggregation_function: AggregationFunction
    source_model: SourceModel
    source_field: str = Field(..., min_length=1, max_length=100)
    weight_field: Optional[str] = Field(None, max_length=100)
    group_level: GroupLevel
    advanced_config: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class UserCalculationCreate(UserCalculationBase):
    """Schema for creating user calculations"""
    
    @field_validator("weight_field")
    @classmethod
    def validate_weight_field_for_weighted_avg(cls, v, info):
        """Validate weight field is provided for weighted averages."""
        if info.data.get("aggregation_function") == AggregationFunction.WEIGHTED_AVG and not v:
            raise ValueError("weight_field is required for weighted average calculations")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Total Ending Balance",
                "description": "Sum of all tranche ending balance amounts",
                "aggregation_function": "SUM",
                "source_model": "TrancheBal",
                "source_field": "tr_end_bal_amt",
                "group_level": "deal",
                "advanced_config": {
                    "filters": [
                        {"field": "deal.issr_cde", "operator": "=", "value": "FHLMC"}
                    ]
                }
            }
        }


class UserCalculationUpdate(BaseModel):
    """Schema for updating user calculations"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    aggregation_function: Optional[AggregationFunction] = None
    source_model: Optional[SourceModel] = None
    source_field: Optional[str] = Field(None, min_length=1, max_length=100)
    weight_field: Optional[str] = Field(None, max_length=100)
    group_level: Optional[GroupLevel] = None
    advanced_config: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class UserCalculationResponse(UserCalculationBase):
    """Response schema for user calculations"""
    id: int
    calculation_type: str = "USER_DEFINED"  # Added for frontend compatibility
    approved_by: Optional[str] = None
    approval_date: Optional[datetime] = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    usage_info: Optional[Dict[str, Any]] = None  # Include usage information

    def get_display_type(self) -> str:
        """Get display type for UI"""
        return f"User Defined ({self.aggregation_function.value})"

    def get_source_description(self) -> str:
        """Get source description for UI"""
        return f"{self.source_model.value}.{self.source_field}"

    def is_approved(self) -> bool:
        """Check if calculation is approved"""
        return self.approved_by is not None

    class Config:
        from_attributes = True


# ===== SYSTEM CALCULATION SCHEMAS =====

class SystemCalculationBase(BaseModel):
    """Base schema for system calculations"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    raw_sql: str = Field(..., min_length=10)
    result_column_name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$")
    group_level: GroupLevel
    metadata_config: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class SystemCalculationCreate(SystemCalculationBase):
    """Schema for creating system calculations"""
    
    @field_validator("raw_sql")
    @classmethod
    def validate_sql_basic(cls, v):
        """Enhanced SQL validation with CTE support"""
        if not v or not v.strip():
            raise ValueError("raw_sql cannot be empty")
        
        sql_trimmed = v.strip()
        
        # Check for CTEs first
        has_ctes = sql_trimmed.upper().strip().startswith('WITH')
        
        if has_ctes:
            # For CTEs, validate the structure but don't require it to start with SELECT
            if not cls._validate_cte_structure(sql_trimmed):
                raise ValueError("Invalid CTE structure")
        else:
            # For simple queries, require SELECT start
            sql_lower = sql_trimmed.lower()
            if not sql_lower.startswith('select'):
                raise ValueError("SQL must be a SELECT statement")
            
            if 'from' not in sql_lower:
                raise ValueError("SQL must include a FROM clause")
        
        # Check for dangerous operations
        dangerous_keywords = ['drop', 'delete', 'insert', 'update', 'alter', 'truncate', 'create']
        sql_lower = sql_trimmed.lower()
        for keyword in dangerous_keywords:
            if keyword in sql_lower:
                raise ValueError(f"Dangerous operation '{keyword.upper()}' not allowed")
        
        return sql_trimmed
    
    @staticmethod
    def _validate_cte_structure(sql: str) -> bool:
        """Basic CTE structure validation"""
        import re
        
        # Check for basic CTE syntax
        if not re.search(r'WITH\s+\w+\s+AS\s*\(', sql, re.IGNORECASE):
            return False
        
        # Check for balanced parentheses
        paren_count = 0
        in_quotes = False
        quote_char = ''
        
        for i, char in enumerate(sql):
            prev_char = sql[i-1] if i > 0 else ''
            
            if (char == '"' or char == "'") and prev_char != '\\':
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = ''
            
            if not in_quotes:
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
        
        return paren_count == 0

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Issuer Type Classification",
                "description": "Categorizes deals by issuer type",
                "group_level": "deal",
                "raw_sql": """
                    SELECT 
                        deal.dl_nbr,
                        CASE 
                            WHEN deal.issr_cde LIKE '%FHLMC%' THEN 'GSE'
                            WHEN deal.issr_cde LIKE '%GNMA%' THEN 'Government'
                            ELSE 'Private'
                        END AS issuer_type
                    FROM deal
                """,
                "result_column_name": "issuer_type",
                "metadata_config": {
                    "required_models": ["Deal"],
                    "performance_hints": {"complexity": "low"}
                }
            }
        }


class SystemCalculationUpdate(BaseModel):
    """Schema for updating system calculations"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    raw_sql: Optional[str] = Field(None, min_length=10)
    result_column_name: Optional[str] = Field(None, min_length=1, max_length=100, pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$")
    group_level: Optional[GroupLevel] = None
    metadata_config: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class SystemCalculationResponse(SystemCalculationBase):
    """Response schema for system calculations"""
    id: int
    calculation_type: str = "SYSTEM_SQL"  # Added for frontend compatibility
    created_by: str
    approved_by: Optional[str] = None
    approval_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    usage_info: Optional[Dict[str, Any]] = None  # Include usage information

    def get_display_type(self) -> str:
        """Get display type for UI"""
        return "System SQL"

    def get_source_description(self) -> str:
        """Get source description for UI"""
        return f"Custom SQL ({self.result_column_name})"

    def is_approved(self) -> bool:
        """Check if calculation is approved"""
        return self.approved_by is not None

    class Config:
        from_attributes = True


# ===== STATIC FIELD SCHEMAS =====

class StaticFieldInfo(BaseModel):
    """Schema for static field information"""
    field_path: str  # e.g., "deal.dl_nbr", "tranche.tr_id"
    name: str
    description: str
    type: str  # "number", "string", "currency", "percentage", etc.
    required_models: List[str]
    nullable: bool

    class Config:
        json_schema_extra = {
            "example": {
                "field_path": "deal.dl_nbr",
                "name": "Deal Number",
                "description": "Unique identifier for the deal",
                "type": "number",
                "required_models": ["Deal"],
                "nullable": False
            }
        }


# ===== CALCULATION REQUEST SCHEMAS =====

class CalculationRequestSchema(BaseModel):
    """Schema for calculation requests in reports"""
    calc_type: str = Field(..., pattern="^(static_field|user_calculation|system_calculation)$")
    calc_id: Optional[int] = None  # Required for user_calculation and system_calculation
    field_path: Optional[str] = None  # Required for static_field
    alias: Optional[str] = None  # Custom alias for result column

    @field_validator("calc_id")
    @classmethod
    def validate_calc_id_when_required(cls, v, info):
        """Validate calc_id is provided when needed"""
        calc_type = info.data.get("calc_type")
        if calc_type in ["user_calculation", "system_calculation"] and not v:
            raise ValueError(f"calc_id is required for {calc_type}")
        return v

    @field_validator("field_path")
    @classmethod
    def validate_field_path_when_required(cls, v, info):
        """Validate field_path is provided when needed"""
        calc_type = info.data.get("calc_type")
        if calc_type == "static_field" and not v:
            raise ValueError("field_path is required for static_field")
        return v

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "calc_type": "static_field",
                    "field_path": "deal.dl_nbr",
                    "alias": "deal_number"
                },
                {
                    "calc_type": "user_calculation", 
                    "calc_id": 1,
                    "alias": "total_balance"
                },
                {
                    "calc_type": "system_calculation",
                    "calc_id": 1,
                    "alias": "issuer_type"
                }
            ]
        }


# ===== REPORT EXECUTION SCHEMAS =====

class ReportExecutionRequest(BaseModel):
    """Schema for report execution requests"""
    calculation_requests: List[CalculationRequestSchema]
    deal_tranche_map: Dict[int, List[str]]  # deal_id -> [tranche_ids] or [] for all
    cycle_code: int

    @field_validator("calculation_requests")
    @classmethod
    def validate_calculation_requests_not_empty(cls, v):
        """Validate at least one calculation is requested"""
        if not v:
            raise ValueError("At least one calculation must be requested")
        return v

    @field_validator("deal_tranche_map")
    @classmethod
    def validate_deal_tranche_map_not_empty(cls, v):
        """Validate at least one deal is specified"""
        if not v:
            raise ValueError("At least one deal must be specified")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "calculation_requests": [
                    {"calc_type": "static_field", "field_path": "deal.dl_nbr", "alias": "deal_number"},
                    {"calc_type": "user_calculation", "calc_id": 1, "alias": "total_balance"},
                    {"calc_type": "system_calculation", "calc_id": 1, "alias": "issuer_type"}
                ],
                "deal_tranche_map": {
                    1001: ["A", "B"],  # Specific tranches
                    1002: []  # All tranches
                },
                "cycle_code": 202404
            }
        }


class ReportExecutionResponse(BaseModel):
    """Schema for report execution responses"""
    data: List[Dict[str, Any]]
    metadata: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "data": [
                    {
                        "deal_number": 1001,
                        "cycle_code": 202404,
                        "tranche_id": "A",
                        "total_balance": 1000000.00,
                        "issuer_type": "GSE"
                    }
                ],
                "metadata": {
                    "total_rows": 1,
                    "calculations_executed": 3,
                    "debug_info": {
                        "total_calculations": 3,
                        "static_fields": 1,
                        "user_calculations": 1,
                        "system_calculations": 1,
                        "errors": []
                    },
                    "individual_sql_queries": {
                        "deal_number": "SELECT DISTINCT deal.dl_nbr AS deal_number...",
                        "total_balance": "SELECT deal.dl_nbr AS deal_number, SUM(...)...",
                        "issuer_type": "SELECT deal.dl_nbr, CASE WHEN..."
                    }
                }
            }
        }


# ===== SQL PREVIEW SCHEMAS =====

class SQLPreviewResponse(BaseModel):
    """Schema for SQL preview responses"""
    sql_previews: Dict[str, Dict[str, Any]]
    parameters: Dict[str, Any]
    summary: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "sql_previews": {
                    "deal_number": {
                        "sql": "SELECT DISTINCT deal.dl_nbr AS deal_number...",
                        "columns": ["deal_number", "cycle_code"],
                        "calculation_type": "static_field"
                    },
                    "total_balance": {
                        "sql": "SELECT deal.dl_nbr AS deal_number, SUM(...)...",
                        "columns": ["deal_number", "cycle_code", "total_balance"],
                        "calculation_type": "user_calculation",
                        "group_level": "deal"
                    }
                },
                "parameters": {
                    "deal_tranche_map": {1001: ["A", "B"]},
                    "cycle_code": 202404
                },
                "summary": {
                    "total_calculations": 2,
                    "static_fields": 1,
                    "user_calculations": 1,
                    "system_calculations": 0
                }
            }
        }


# ===== CONFIGURATION SCHEMAS =====

class CalculationConfigResponse(BaseModel):
    """Schema for calculation configuration responses"""
    aggregation_functions: List[Dict[str, str]]
    source_models: List[Dict[str, str]]
    group_levels: List[Dict[str, str]]
    static_fields: List[StaticFieldInfo]

    class Config:
        json_schema_extra = {
            "example": {
                "aggregation_functions": [
                    {"value": "SUM", "label": "SUM - Total amount", "description": "Add all values together"}
                ],
                "source_models": [
                    {"value": "Deal", "label": "Deal", "description": "Base deal information"}
                ],
                "group_levels": [
                    {"value": "deal", "label": "Deal Level", "description": "Aggregate to deal level"}
                ],
                "static_fields": [
                    {
                        "field_path": "deal.dl_nbr",
                        "name": "Deal Number",
                        "description": "Unique identifier for the deal",
                        "type": "number",
                        "required_models": ["Deal"],
                        "nullable": False
                    }
                ]
            }
        }


# ===== USAGE INFORMATION SCHEMAS =====

class CalculationUsageResponse(BaseModel):
    """Response schema for calculation usage information"""
    calculation_id: Union[int, str]  # Can be numeric (legacy) or string (new format)
    calculation_name: str
    is_in_use: bool
    report_count: int
    reports: List[Dict[str, Any]]


class AvailableCalculationResponse(BaseModel):
    """Response schema for available calculations with new format"""
    id: str  # Always string with new format: "user.{source_field}", "system.{result_column}", "static_{table}.{field}"
    name: str
    description: Optional[str] = None
    aggregation_function: Optional[str] = None
    source_model: Optional[str] = None
    source_field: Optional[str] = None
    group_level: str
    weight_field: Optional[str] = None
    scope: str
    category: str
    is_default: bool
    calculation_type: Literal["USER_DEFINED", "SYSTEM_SQL", "STATIC_FIELD"]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "user.current_balance",
                    "name": "Current Balance Sum",
                    "description": "Sum of current balances",
                    "aggregation_function": "SUM",
                    "source_model": "TrancheBal", 
                    "source_field": "current_balance",
                    "group_level": "deal",
                    "weight_field": None,
                    "scope": "DEAL",
                    "category": "Balance & Amount Calculations",
                    "is_default": False,
                    "calculation_type": "USER_DEFINED"
                },
                {
                    "id": "system.total_wac",
                    "name": "Total Weighted Average Coupon",
                    "description": "Custom calculated WAC",
                    "aggregation_function": None,
                    "source_model": None,
                    "source_field": "total_wac",
                    "group_level": "deal", 
                    "weight_field": None,
                    "scope": "DEAL",
                    "category": "System Calculations",
                    "is_default": False,
                    "calculation_type": "SYSTEM_SQL"
                },
                {
                    "id": "static_deal.dl_nbr",
                    "name": "Deal Number",
                    "description": "Unique deal identifier",
                    "aggregation_function": None,
                    "source_model": None,
                    "source_field": "deal.dl_nbr",
                    "group_level": "deal",
                    "weight_field": None,
                    "scope": "DEAL", 
                    "category": "Deal Information",
                    "is_default": True,
                    "calculation_type": "STATIC_FIELD"
                }
            ]
        }
    )


# ===== READ SCHEMAS (for backward compatibility) =====

# Alias for backward compatibility
UserCalculationRead = UserCalculationResponse
SystemCalculationRead = SystemCalculationResponse
StaticFieldRead = StaticFieldInfo
CalculationConfigRead = CalculationConfigResponse

# ===== MISSING SCHEMAS FOR ROUTER COMPATIBILITY =====

class UserCalculationStats(BaseModel):
    """Statistics for user calculations"""
    total_count: int
    active_count: int
    approved_count: int
    in_use_count: int

class SystemCalculationStats(BaseModel):
    """Statistics for system calculations"""
    total_count: int
    active_count: int
    approved_count: int
    in_use_count: int

class CalculationExecutionRequest(BaseModel):
    """Request schema for calculation execution"""
    calculation_requests: List[CalculationRequestSchema]
    deal_tranche_map: Dict[int, List[str]]
    cycle_code: int

class CalculationExecutionResponse(BaseModel):
    """Response schema for calculation execution"""
    data: List[Dict[str, Any]]
    metadata: Dict[str, Any]

class CalculationExecutionSQLResponse(BaseModel):
    """SQL preview response for calculation execution"""
    sql_previews: Dict[str, Dict[str, Any]]
    parameters: Dict[str, Any]
    summary: Dict[str, Any]