# app/calculations/schemas.py
"""Pydantic schemas for the new separated calculation system"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
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
    created_by: str
    created_at: datetime
    updated_at: datetime
    is_active: bool

    def get_display_type(self) -> str:
        """Get display type for UI"""
        return f"User Defined ({self.aggregation_function.value})"

    def get_source_description(self) -> str:
        """Get source description for UI"""
        return f"{self.source_model.value}.{self.source_field}"

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
        """Basic SQL validation"""
        if not v or not v.strip():
            raise ValueError("raw_sql cannot be empty")
        
        sql_lower = v.lower().strip()
        if not sql_lower.startswith('select'):
            raise ValueError("SQL must be a SELECT statement")
        
        if 'from' not in sql_lower:
            raise ValueError("SQL must include a FROM clause")
        
        return v.strip()

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
    """Schema for calculation usage information"""
    calculation_id: int
    calculation_name: str
    is_in_use: bool
    report_count: int
    reports: List[Dict[str, Any]]

    class Config:
        json_schema_extra = {
            "example": {
                "calculation_id": 1,
                "calculation_name": "Total Ending Balance",
                "is_in_use": True,
                "report_count": 2,
                "reports": [
                    {
                        "report_id": 1,
                        "report_name": "Monthly Deal Summary",
                        "report_description": "Summary of all deals for the month"
                    }
                ]
            }
        }