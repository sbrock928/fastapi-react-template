"""Pydantic schemas for the reporting module."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, field_validator, ConfigDict
import json

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
    selected_columns: List[str] = []  # Column names in desired display order
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

    @field_validator("selected_columns")
    @classmethod
    def validate_selected_columns(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one column must be selected")
        if len(set(v)) != len(v):
            raise ValueError("Duplicate column names are not allowed")
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
    selected_columns: Optional[List[str]] = None
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

    @field_validator("selected_columns")
    @classmethod
    def validate_selected_columns(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            if not v:
                raise ValueError("At least one column must be selected")
            if len(set(v)) != len(v):
                raise ValueError("Duplicate column names are not allowed")
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
    column_count: int
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
    

    class OverrideType(str, Enum):
        """Types of overrides available."""
        MANUAL = "manual"
        CALCULATED = "calculated"
        MAPPED = "mapped"


class OverrideableColumn(BaseModel):
    """Schema for columns that can be overridden."""
    key: str
    label: str
    data_type: str  # 'string', 'number', 'currency', 'percentage', 'date'
    can_override: bool = True
    calculation_description: Optional[str] = None
    category: str = "General"

    model_config = ConfigDict(from_attributes=True)


class TrancheOverrideBase(BaseModel):
    """Base schema for tranche override objects."""
    
    tranche_id: int
    column_name: str
    override_value: Optional[Any] = None
    override_type: OverrideType = OverrideType.MANUAL
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    @field_validator("column_name")
    @classmethod
    def validate_column_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Column name cannot be empty")
        return v.strip()

    @field_validator("tranche_id")
    @classmethod
    def validate_tranche_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Tranche ID must be positive")
        return v

    @field_validator("override_value")
    @classmethod
    def validate_override_value(cls, v: Any) -> Optional[str]:
        """Convert override value to JSON string for storage."""
        if v is None:
            return None
        # Convert to JSON string for storage
        try:
            return json.dumps(v)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Override value must be JSON serializable: {e}")


class TrancheOverrideCreate(TrancheOverrideBase):
    """Schema for creating tranche overrides."""
    created_by: str

    @field_validator("created_by")
    @classmethod
    def validate_created_by(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Created by cannot be empty")
        return v.strip()


class TrancheOverrideUpdate(BaseModel):
    """Schema for updating tranche overrides."""
    override_value: Optional[Any] = None
    override_type: Optional[OverrideType] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    @field_validator("override_value")
    @classmethod
    def validate_override_value(cls, v: Any) -> Optional[str]:
        """Convert override value to JSON string for storage."""
        if v is None:
            return None
        try:
            return json.dumps(v)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Override value must be JSON serializable: {e}")


class TrancheOverrideRead(TrancheOverrideBase):
    """Schema for reading tranche override objects with all fields."""
    
    id: int
    report_id: int
    created_by: str
    created_date: datetime
    updated_date: datetime

    @field_validator("override_value", mode="before")
    @classmethod
    def parse_override_value(cls, v: Any) -> Any:
        """Parse JSON string back to Python object."""
        if v is None or v == "":
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return v
        return v


class BulkOverrideRequest(BaseModel):
    """Schema for bulk override operations."""
    overrides: List[TrancheOverrideCreate]
    replace_existing: bool = False

    model_config = ConfigDict(extra="forbid")


class OverrideSummary(BaseModel):
    """Summary of overrides for a report."""
    report_id: int
    total_overrides: int
    overrides_by_type: dict  # {override_type: count}
    overrides_by_column: dict  # {column_name: count}
    last_updated: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)