"""Pydantic schemas for the reporting module."""

from typing import Optional, List, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, field_validator, model_validator, ConfigDict


class ReportScope(str, Enum):
    """Enumeration of report scope options."""

    DEAL = "DEAL"
    TRANCHE = "TRANCHE"


class FieldType(str, Enum):
    """Enumeration of field types for reporting."""
    
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    PERCENTAGE = "percentage"


class ReportFieldBase(BaseModel):
    """Base schema for report field configurations."""
    field_name: str
    display_name: str
    field_type: FieldType
    is_required: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class ReportFieldCreate(ReportFieldBase):
    pass


class ReportField(ReportFieldBase):
    id: int
    report_id: int


class ReportTrancheBase(BaseModel):
    """Base schema for report tranche associations."""
    dl_nbr: int
    tr_id: str

class ReportTrancheCreate(ReportTrancheBase):
    pass

class ReportTranche(ReportTrancheBase):
    id: int
    report_deal_id: int
    
    model_config = ConfigDict(from_attributes=True)


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
    """Create schema for reports with normalized structure."""
    selected_deals: List[ReportDealCreate] = []
    selected_fields: List[ReportFieldCreate] = []
    
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

    @field_validator("selected_fields")
    @classmethod
    def validate_selected_fields(cls, v: List[ReportFieldCreate]) -> List[ReportFieldCreate]:
        if not v:
            raise ValueError("At least one field must be selected")
        
        # Check for duplicate field names
        field_names = [field.field_name for field in v]
        if len(set(field_names)) != len(field_names):
            raise ValueError("Duplicate field names are not allowed")
        
        return v

    @field_validator("selected_deals")
    @classmethod
    def validate_tranche_selections(cls, v: List[ReportDealCreate], info) -> List[ReportDealCreate]:
        # Get scope from the data being validated
        if hasattr(info, "data") and info.data and info.data.get("scope") == ReportScope.TRANCHE:
            # For tranche-level reports, ensure at least one deal has tranches selected
            has_tranches = any(deal.selected_tranches for deal in v)
            if not has_tranches:
                raise ValueError("Tranche-level reports must have at least one tranche selected")
              # Check for duplicate tranche ID within each deal
            for deal in v:
                tranche_keys = [(tranche.dl_nbr, tranche.tr_id) for tranche in deal.selected_tranches]
                if len(set(tranche_keys)) != len(tranche_keys):
                    raise ValueError(f"Duplicate tranche keys found for deal {deal.dl_nbr}")

        return v

    @model_validator(mode='after')
    def validate_with_database_context(self):
        """Placeholder for database validation - will be handled by service with dependency injection."""
        # This validator can be extended to accept database context if needed in the future
        return self


class ReportRead(ReportBase):
    """Read schema for reports with normalized structure."""
    id: int
    created_date: datetime
    updated_date: datetime
    selected_deals: List[ReportDeal] = []
    selected_fields: List[ReportField] = []


class ReportUpdate(BaseModel):
    """Update schema - allows partial updates."""

    name: Optional[str] = None
    description: Optional[str] = None
    scope: Optional[ReportScope] = None
    selected_deals: Optional[List[ReportDealCreate]] = None
    selected_fields: Optional[List[ReportFieldCreate]] = None
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

    @model_validator(mode='after')
    def validate_update_logic(self):
        """Validate update-specific business rules."""
        # If scope is being changed to TRANCHE, ensure deals have tranches
        if (self.scope == ReportScope.TRANCHE and 
            self.selected_deals is not None and 
            self.selected_deals):
            has_tranches = any(deal.selected_tranches for deal in self.selected_deals)
            if not has_tranches:
                raise ValueError("When changing to tranche-level scope, at least one tranche must be selected")
        return self


class AvailableField(BaseModel):
    """Schema for available fields that can be selected for reports."""
    
    field_name: str
    display_name: str
    field_type: FieldType
    description: Optional[str] = None
    scope: ReportScope  # Which report scope this field is available for
    category: str  # e.g., "Deal", "Tranche", "Cycle Data"
    is_default: bool = False  # Whether this field should be selected by default


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
    field_count: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class RunReportRequest(BaseModel):
    """Request schema for running a saved report."""

    report_id: int
    cycle_code: int

    model_config = ConfigDict(extra="forbid")

