"""Pydantic schemas for the datawarehouse module."""

from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, field_validator, ConfigDict


# Deal Schemas
class DealBase(BaseModel):
    """Base schema for deal objects with common fields."""

    name: str
    originator: str
    deal_type: str
    closing_date: date
    total_principal: Decimal
    credit_rating: Optional[str] = None
    yield_rate: Optional[Decimal] = None
    duration: Optional[Decimal] = None
    cycle_code: str
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    @field_validator("name", "originator", "deal_type", "cycle_code")
    @classmethod
    def validate_required_strings(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    @field_validator("total_principal")
    @classmethod
    def validate_total_principal(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Total principal must be positive")
        return v

    @field_validator("yield_rate")
    @classmethod
    def validate_yield_rate(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None:
            if v < 0 or v > 1:
                raise ValueError("Yield rate should be between 0 and 1 (e.g., 0.0485 for 4.85%)")
        return v

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("Duration must be positive")
        return v


class DealCreate(DealBase):
    pass


class DealRead(DealBase):
    id: int
    created_date: datetime
    updated_date: datetime


class DealUpdate(BaseModel):
    """Update schema - allows partial updates."""

    name: Optional[str] = None
    originator: Optional[str] = None
    deal_type: Optional[str] = None
    closing_date: Optional[date] = None
    total_principal: Optional[Decimal] = None
    credit_rating: Optional[str] = None
    yield_rate: Optional[Decimal] = None
    duration: Optional[Decimal] = None
    cycle_code: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")


# Tranche Schemas
class TrancheBase(BaseModel):
    """Base schema for tranche objects with common fields."""

    deal_id: int
    name: str
    class_name: str
    subordination_level: int = 1
    principal_amount: Decimal
    interest_rate: Decimal
    credit_rating: Optional[str] = None
    payment_priority: int = 1
    maturity_date: Optional[date] = None
    cycle_code: str
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    @field_validator("name", "class_name", "cycle_code")
    @classmethod
    def validate_required_strings(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    @field_validator("deal_id")
    @classmethod
    def validate_deal_id(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Deal ID must be positive")
        return v

    @field_validator("principal_amount")
    @classmethod
    def validate_principal_amount(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Principal amount must be positive")
        return v

    @field_validator("interest_rate")
    @classmethod
    def validate_interest_rate(cls, v: Decimal) -> Decimal:
        if v < 0 or v > 1:
            raise ValueError("Interest rate should be between 0 and 1 (e.g., 0.0485 for 4.85%)")
        return v

    @field_validator("subordination_level", "payment_priority")
    @classmethod
    def validate_positive_integers(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Value must be positive")
        return v


class TrancheCreate(TrancheBase):
    pass


class TrancheRead(TrancheBase):
    id: int
    created_date: datetime
    updated_date: datetime


class TrancheUpdate(BaseModel):
    """Update schema - allows partial updates."""

    deal_id: Optional[int] = None
    name: Optional[str] = None
    class_name: Optional[str] = None
    subordination_level: Optional[int] = None
    principal_amount: Optional[Decimal] = None
    interest_rate: Optional[Decimal] = None
    credit_rating: Optional[str] = None
    payment_priority: Optional[int] = None
    maturity_date: Optional[date] = None
    cycle_code: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")


# Combined schemas
class DealWithTranches(DealRead):
    """Deal schema that includes its tranches."""

    tranches: List[TrancheRead] = []


class TrancheWithDeal(TrancheRead):
    """Tranche schema that includes its parent deal."""

    deal: DealRead


# Summary schemas for API responses
class DealSummary(BaseModel):
    """Summary schema for deal listings."""

    id: int
    name: str
    originator: str
    deal_type: str
    total_principal: Decimal
    credit_rating: Optional[str]
    yield_rate: Optional[Decimal]
    cycle_code: str
    tranche_count: int

    model_config = ConfigDict(from_attributes=True)


class TrancheSummary(BaseModel):
    """Summary schema for tranche listings."""

    id: int
    deal_id: int
    deal_name: str
    name: str
    class_name: str
    principal_amount: Decimal
    interest_rate: Decimal
    credit_rating: Optional[str]
    cycle_code: str

    model_config = ConfigDict(from_attributes=True)
