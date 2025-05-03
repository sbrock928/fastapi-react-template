from sqlmodel import Session
from typing import List, Optional
from fastapi import HTTPException
from app.resources.models import User, UserBase, Employee, EmployeeBase
from app.resources.dao import UserDAO, EmployeeDAO
from app.common.base_service import GenericService

class UserService(GenericService[User, UserBase]):
    """User-specific service with custom validations"""
    
    def __init__(self, session: Session):
        super().__init__(session, User, UserBase)
        self.dao = UserDAO(session, User)
    
    async def before_create(self, user_data: UserBase) -> UserBase:
        """Custom validation before user creation"""
        # Check if username already exists
        existing_user = await self.dao.get_by_username(user_data.username)
        if existing_user:
            raise HTTPException(status_code=409, detail="Username already taken")
            
        # Check if email already exists
        existing_email = await self.dao.get_by_email(user_data.email)
        if existing_email:
            raise HTTPException(status_code=409, detail="Email already registered")
            
        return user_data
    
    async def before_update(self, user_id: int, user_data: UserBase) -> UserBase:
        """Custom validation before user update"""
        # Get fields that were provided for update
        update_data = user_data.dict(exclude_unset=True)
        
        # If username was provided, check if it's unique
        if "username" in update_data:
            existing_user = await self.dao.get_by_username(update_data["username"])
            if existing_user and existing_user.id != user_id:
                raise HTTPException(status_code=409, detail="Username already taken")
                
        # If email was provided, check if it's unique
        if "email" in update_data:
            existing_email = await self.dao.get_by_email(update_data["email"])
            if existing_email and existing_email.id != user_id:
                raise HTTPException(status_code=409, detail="Email already registered")
                
        return user_data

    # Custom methods that don't fit the CRUD pattern
    async def get_by_username(self, username: str) -> User:
        """Get a user by username with proper error handling"""
        user = await self.dao.get_by_username(username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user


class EmployeeService(GenericService[Employee, EmployeeBase]):
    """Employee-specific service with custom validations"""
    
    def __init__(self, session: Session):
        super().__init__(session, Employee, EmployeeBase)
        self.dao = EmployeeDAO(session, Employee)
    
    async def before_create(self, employee_data: EmployeeBase) -> EmployeeBase:
        """Custom validation before employee creation"""
        # Check if employee_id already exists
        existing_emp = await self.dao.get_by_employee_id(employee_data.employee_id)
        if existing_emp:
            raise HTTPException(status_code=409, detail="Employee ID already exists")
            
        # Check if email already exists
        existing_email = await self.dao.get_by_email(employee_data.email)
        if existing_email:
            raise HTTPException(status_code=409, detail="Email already registered")
            
        return employee_data
    
    async def before_update(self, employee_id: int, employee_data: EmployeeBase) -> EmployeeBase:
        """Custom validation before employee update"""
        # Get fields that were provided for update
        update_data = employee_data.dict(exclude_unset=True)
        
        # If employee_id was provided, check if it's unique
        if "employee_id" in update_data:
            existing_emp = await self.dao.get_by_employee_id(update_data["employee_id"])
            if existing_emp and existing_emp.id != employee_id:
                raise HTTPException(status_code=409, detail="Employee ID already exists")
                
        # If email was provided, check if it's unique
        if "email" in update_data:
            existing_email = await self.dao.get_by_email(update_data["email"])
            if existing_email and existing_email.id != employee_id:
                raise HTTPException(status_code=409, detail="Email already registered")
                
        return employee_data
        
    # Custom methods for employee-specific operations
    async def get_employees_by_department(self, department: str) -> List[Employee]:
        """Get all employees in a specific department"""
        return await self.dao.get_by_department(department)
        
    async def get_employees_by_position(self, position: str) -> List[Employee]:
        """Get all employees with a specific position"""
        return await self.dao.get_by_position(position)