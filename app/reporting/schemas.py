"""Pydantic schemas for the reporting module."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, field_validator, ConfigDict


class ReportScope(str, Enum):
    """Enumeration of report scope options."""
    DEAL = "DEAL"
    TRANCHE = "TRANCHE"


class ReportBase(BaseModel):
    """Base schema for report configuration objects."""
    
    name: str
    scope: ReportScope  
    created_by: str
    selected_deals: List[int] = []
    selected_tranches: Dict[str, List[int]] = {}  # Keys are deal_id as strings
    selected_columns: List[str] = []  # NEW FIELD
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

    @field_validator("selected_deals")
    @classmethod
    def validate_selected_deals(cls, v: List[int]) -> List[int]:
        if not v:
            raise ValueError("At least one deal must be selected")
        if len(set(v)) != len(v):
            raise ValueError("Duplicate deal IDs are not allowed")
        return v

    @field_validator("selected_tranches")
    @classmethod
    def validate_selected_tranches(cls, v: Dict[str, List[int]], info) -> Dict[str, List[int]]:
        # Get scope from the data being validated
        if hasattr(info, 'data') and info.data and info.data.get('scope') == ReportScope.TRANCHE:
            if not v or not any(v.values()):
                raise ValueError("At least one tranche must be selected for tranche-level reports")
            
            # Validate that deal IDs in tranches match selected deals
            if hasattr(info, 'data') and info.data:
                selected_deals = info.data.get('selected_deals', [])
                tranche_deal_ids = set(int(deal_id) for deal_id in v.keys())
                if not tranche_deal_ids.issubset(set(selected_deals)):
                    raise ValueError("Tranche selections contain deal IDs not in selected deals")
                    
            # Check for duplicate tranche IDs within each deal
            for deal_id, tranche_ids in v.items():
                if len(set(tranche_ids)) != len(tranche_ids):
                    raise ValueError(f"Duplicate tranche IDs found for deal {deal_id}")
        
        return v

    @field_validator("selected_columns")
    @classmethod
    def validate_selected_columns(cls, v: List[str], info) -> List[str]:
        if not v:
            # If no columns specified, use defaults
            from app.reporting.column_registry import get_default_columns, ColumnScope
            scope = info.data.get('scope') if hasattr(info, 'data') and info.data else None
            if scope:
                return get_default_columns(ColumnScope(scope))
            return []
        
        # Validate that all specified columns exist
        from app.reporting.column_registry import COLUMN_REGISTRY
        invalid_columns = [col for col in v if col not in COLUMN_REGISTRY]
        if invalid_columns:
            raise ValueError(f"Invalid columns: {', '.join(invalid_columns)}")
        
        return v
    
class ReportCreate(ReportBase):
    pass


class ReportRead(ReportBase):
    id: int
    created_date: datetime
    updated_date: datetime


class ReportUpdate(BaseModel):
    """Update schema - allows partial updates."""
    name: Optional[str] = None
    scope: Optional[ReportScope] = None
    selected_deals: Optional[List[int]] = None
    selected_tranches: Optional[Dict[str, List[int]]] = None
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


class ReportSummary(BaseModel):
    """Summary schema for report listings."""
    id: int
    name: str
    scope: ReportScope
    created_by: str
    created_date: datetime
    deal_count: int
    tranche_count: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class RunReportRequest(BaseModel):
    """Request schema for running a saved report."""
    report_id: int
    cycle_code: str

    model_config = ConfigDict(extra="forbid")

    @field_validator("cycle_code")
    @classmethod
    def validate_cycle_code(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Cycle code cannot be empty")
        return v.strip()
    

