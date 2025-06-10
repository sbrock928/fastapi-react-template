"""Simplified Pydantic schemas for the reporting module."""

from typing import Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, field_validator, ConfigDict


class ReportScope(str, Enum):
    """Report scope options."""
    DEAL = "DEAL"
    TRANCHE = "TRANCHE"


# ===== CALCULATION SCHEMAS =====

class ReportCalculationBase(BaseModel):
    """Base schema for report calculation associations."""
    calculation_id: int
    display_order: int = 0
    display_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class ReportCalculationCreate(ReportCalculationBase):
    pass


class ReportCalculation(ReportCalculationBase):
    id: int
    report_id: int


# ===== TRANCHE SCHEMAS =====

class ReportTrancheBase(BaseModel):
    """Base schema for report tranche associations."""
    tr_id: str
    dl_nbr: Optional[int] = None  # Auto-populated from parent deal

class ReportTrancheCreate(ReportTrancheBase):
    pass

class ReportTranche(ReportTrancheBase):
    id: int
    report_deal_id: int
    
    model_config = ConfigDict(from_attributes=True)


# ===== DEAL SCHEMAS =====

class ReportDealBase(BaseModel):
    """Base schema for report deal associations."""
    dl_nbr: int

class ReportDealCreate(ReportDealBase):
    selected_tranches: List[ReportTrancheCreate] = []

class ReportDeal(ReportDealBase):
    id: int
    report_id: int
    selected_tranches: List[ReportTranche] = []
    
    model_config = ConfigDict(from_attributes=True)


# ===== CORE REPORT SCHEMAS =====

class ReportBase(BaseModel):
    """Base schema for report configuration objects."""
    name: str
    description: Optional[str] = None
    scope: ReportScope
    created_by: Optional[str] = "system"
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Report name cannot be empty")
        if len(v.strip()) > 255:
            raise ValueError("Report name cannot exceed 255 characters")
        return v.strip()


class ReportCreate(ReportBase):
    """Create schema for reports."""
    selected_deals: List[ReportDealCreate] = []
    selected_calculations: List[ReportCalculationCreate] = []
    
    @field_validator("selected_deals")
    @classmethod
    def validate_selected_deals(cls, v: List[ReportDealCreate]) -> List[ReportDealCreate]:
        if not v:
            raise ValueError("At least one deal must be selected")
        
        # Check for duplicate deal numbers
        dl_nbrs = [deal.dl_nbr for deal in v]
        if len(set(dl_nbrs)) != len(dl_nbrs):
            raise ValueError("Duplicate deal numbers are not allowed")
        
        return v

    @field_validator("selected_calculations")
    @classmethod
    def validate_selected_calculations(cls, v: List[ReportCalculationCreate]) -> List[ReportCalculationCreate]:
        if not v:
            raise ValueError("At least one calculation must be selected")
        
        # Check for duplicate calculation IDs
        calc_ids = [calc.calculation_id for calc in v]
        if len(set(calc_ids)) != len(calc_ids):
            raise ValueError("Duplicate calculation IDs are not allowed")
        
        return v


class ReportRead(ReportBase):
    """Read schema for reports."""
    id: int
    created_date: datetime
    updated_date: datetime
    selected_deals: List[ReportDeal] = []
    selected_calculations: List[ReportCalculation] = []


class ReportUpdate(BaseModel):
    """Update schema - allows partial updates."""
    name: Optional[str] = None
    description: Optional[str] = None
    scope: Optional[ReportScope] = None
    selected_deals: Optional[List[ReportDealCreate]] = None
    selected_calculations: Optional[List[ReportCalculationCreate]] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v or not v.strip():
                raise ValueError("Report name cannot be empty")
            if len(v.strip()) > 255:
                raise ValueError("Report name cannot exceed 255 characters")
            return v.strip()
        return v


# ===== AVAILABLE CALCULATION SCHEMA =====

class AvailableCalculation(BaseModel):
    """Schema for available calculations that can be selected for reports."""
    id: int
    name: str
    description: Optional[str] = None
    aggregation_function: str
    source_model: str
    source_field: str
    group_level: str
    weight_field: Optional[str] = None
    scope: ReportScope
    category: str
    is_default: bool = False


# ===== SUMMARY SCHEMAS =====

class ReportSummary(BaseModel):
    """Summary schema for report listings."""
    id: int
    name: str
    description: Optional[str] = None
    scope: ReportScope
    created_by: str
    created_date: datetime
    deal_count: int
    tranche_count: int
    calculation_count: int
    is_active: bool
    # Execution statistics
    total_executions: int = 0
    last_executed: Optional[datetime] = None
    last_execution_success: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


# ===== EXECUTION SCHEMAS =====

class RunReportRequest(BaseModel):
    """Request schema for running a saved report."""
    report_id: int
    cycle_code: int

    model_config = ConfigDict(extra="forbid")


class ReportExecutionLog(BaseModel):
    """Schema for report execution logs."""
    id: int
    report_id: int
    cycle_code: int
    executed_by: Optional[str] = None
    execution_time_ms: Optional[float] = None
    row_count: Optional[int] = None
    success: bool
    error_message: Optional[str] = None
    executed_at: datetime
    
    model_config = ConfigDict(from_attributes=True)