from typing import Optional
from sqlmodel import Field, SQLModel
from pydantic import EmailStr, validator
from datetime import datetime

class EmployeeBase(SQLModel):
    employee_id: str = Field(unique=True)
    email: EmailStr = Field(unique=True)
    full_name: str = Field(min_length=2)
    department: str
    position: str
    
    class Config:
        orm_mode = True
        extra = "forbid"
    
    @validator('employee_id')
    def employee_id_format(cls, v):
        if not v.startswith('EMP-'):
            raise ValueError('Employee ID must start with EMP-')
        return v


# Base models (for request/response schemas)
class UserBase(SQLModel):
    username: str = Field(unique=True, min_length=3)
    email: EmailStr = Field(unique=True)
    full_name: str = Field(min_length=2)
    
    class Config:
        orm_mode = True  # For compatibility with older SQLModel versions
        extra = "forbid"  # Prevents extra fields from being included
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.replace('_', '').isalnum():
            raise ValueError('Username must be alphanumeric (underscores allowed)')
        return v

# Database table models (inherit from base models)
class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)


# Database table model (inherits from base model)
class Employee(EmployeeBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)