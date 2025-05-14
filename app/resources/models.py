from typing import Optional
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict

# SQLAlchemy Base
from app.database import Base

# SQLAlchemy models
class User(Base):
    __tablename__ = "user"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)


class Employee(Base):
    __tablename__ = "employee"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    department = Column(String)
    position = Column(String)


class Subscriber(Base):
    __tablename__ = "subscriber"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    subscription_tier = Column(String, default="free")
    signup_date = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)
    last_billing_date = Column(DateTime, nullable=True)


# Pydantic models for API schemas
class SubscriptionTier(str, Enum):
    FREE = "FREE"
    BASIC = "BASIC"
    PREMIUM = "PREMIUM"
    ENTERPRISE = "ENTERPRISE"


# Base Pydantic models
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid"
    )

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v):
        if not v.replace("_", "").isalnum():
            raise ValueError("Username must be alphanumeric (underscores allowed)")
        return v


class EmployeeBase(BaseModel):
    employee_id: str
    email: EmailStr
    full_name: str
    department: str
    position: str

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid"
    )

    @field_validator("employee_id")
    @classmethod
    def employee_id_format(cls, v):
        if not v.startswith("EMP-"):
            raise ValueError("Employee ID must start with EMP-")
        return v


class SubscriberBase(BaseModel):
    email: EmailStr
    full_name: str
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    signup_date: datetime = datetime.now()
    is_active: bool = True
    last_billing_date: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid"
    )

    @field_validator("email")
    @classmethod
    def email_validator(cls, v):
        if not v:
            raise ValueError("Email is required")
        return v

    @field_validator("last_billing_date", mode='before')
    @classmethod
    def validate_last_billing_date(cls, v):
        if v == "":
            return None
        return v


# Create/Read schema models
class UserCreate(UserBase):
    pass


class UserRead(UserBase):
    id: int


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeRead(EmployeeBase):
    id: int


class SubscriberCreate(SubscriberBase):
    pass


class SubscriberRead(SubscriberBase):
    id: int
