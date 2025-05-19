"""Pydantic schemas for the resources module API."""

from typing import Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict


class SubscriptionTier(str, Enum):
    """Enumeration of available subscription tiers."""

    FREE = "FREE"
    BASIC = "BASIC"
    PREMIUM = "PREMIUM"
    ENTERPRISE = "ENTERPRISE"


# Base Pydantic models
class UserBase(BaseModel):
    """Base schema for user objects with common fields."""

    username: str
    email: EmailStr
    full_name: str

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace("_", "").isalnum():
            raise ValueError("Username must be alphanumeric (underscores allowed)")
        return v


class EmployeeBase(BaseModel):
    """Base schema for employee objects with common fields."""

    employee_id: str
    email: EmailStr
    full_name: str
    department: str
    position: str

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    @field_validator("employee_id")
    @classmethod
    def employee_id_format(cls, v: str) -> str:
        if not v.startswith("EMP-"):
            raise ValueError("Employee ID must start with EMP-")
        return v


class SubscriberBase(BaseModel):
    """Base schema for subscriber objects with common fields."""

    email: EmailStr
    full_name: str
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    signup_date: datetime = datetime.now()
    is_active: bool = True
    last_billing_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    @field_validator("email")
    @classmethod
    def email_validator(cls, v: EmailStr) -> EmailStr:
        if not v:
            raise ValueError("Email is required")
        return v

    @field_validator("last_billing_date", mode="before")
    @classmethod
    def validate_last_billing_date(cls, v: Any) -> Optional[Any]:
        if v == "":
            return None
        return v


# Create/Read schema models
class UserCreate(UserBase):
    pass


class UserRead(UserBase):
    id: int


# Update schema model - currently identical to Create but can be customized in the future
class UserUpdate(UserBase):
    pass


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeRead(EmployeeBase):
    id: int


# Update schema model - currently identical to Create but can be customized in the future
class EmployeeUpdate(EmployeeBase):
    pass


class SubscriberCreate(SubscriberBase):
    pass


class SubscriberRead(SubscriberBase):
    id: int


# Update schema model - currently identical to Create but can be customized in the future
class SubscriberUpdate(SubscriberBase):
    pass
