from typing import Optional
from sqlmodel import Field, SQLModel
from pydantic import EmailStr, validator
from sqlalchemy.exc import IntegrityError

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, min_length=3)
    email: EmailStr = Field(unique=True)
    full_name: str = Field(min_length=2)

    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.replace('_', '').isalnum():
            raise ValueError('Username must be alphanumeric (underscores allowed)')
        return v

class Employee(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: str = Field(unique=True)
    email: EmailStr = Field(unique=True)
    full_name: str = Field(min_length=2)
    department: str
    position: str
    
    @validator('employee_id')
    def employee_id_format(cls, v):
        if not v.startswith('EMP-'):
            raise ValueError('Employee ID must start with EMP-')
        return v