from typing import List, Optional, Dict, Any
from fastapi import HTTPException
from sqlmodel import Session
from app.resources.dao import ResourcesDAO
from app.resources.models import User, UserBase, Employee, EmployeeBase

class ResourcesService:
    def __init__(self, session: Session):
        self.resources_dao = ResourcesDAO(session)
        self.session = session
    
    # User service methods
    async def get_all_users(self) -> List[User]:
        """Get all users"""
        return await self.resources_dao.get_all_users()
    
    async def get_user_by_id(self, user_id: int) -> User:
        """Get a user by ID, raising an exception if not found"""
        user = await self.resources_dao.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    
    async def check_user_exists(self, username: str, email: str, exclude_id: int = None) -> None:
        """Check if a user with the given username or email already exists"""
        # Check username
        existing_username = await self.resources_dao.get_user_by_username(username)
        if existing_username and (exclude_id is None or existing_username.id != exclude_id):
            raise HTTPException(status_code=400, detail={"username": "Username already exists"})
        
        # Check email
        existing_email = await self.resources_dao.get_user_by_email(email)
        if existing_email and (exclude_id is None or existing_email.id != exclude_id):
            raise HTTPException(status_code=400, detail={"email": "Email already exists"})
    
    async def create_user(self, user_data: UserBase) -> User:
        """Create a new user after validating data"""
        # Create a User instance from UserBase
        user = User.from_orm(user_data) if hasattr(User, "from_orm") else User(**user_data.dict())
        
        # Check if username or email already exists
        await self.check_user_exists(user.username, user.email)
        
        try:
            return await self.resources_dao.create_user(user)
        except Exception as e:
            self.session.rollback()
            if isinstance(e, Exception):
                raise HTTPException(status_code=400, detail="Database constraint violated")
            raise HTTPException(status_code=400, detail=str(e))
    
    async def update_user(self, user_id: int, user_update: UserBase) -> User:
        """Update a user after validating data"""
        # Get the existing user
        db_user = await self.get_user_by_id(user_id)
        
        # Get only the fields that were provided in the request
        try:
            update_data = user_update.dict(exclude_unset=True)
        except AttributeError:
            # For newer versions of SQLModel/Pydantic
            update_data = user_update.model_dump(exclude_unset=True)
        
        # Remove id from update data to prevent changing it
        if "id" in update_data:
            del update_data["id"]
        
        # Check uniqueness for username and email if they are being updated
        if update_data.get('username') or update_data.get('email'):
            await self.check_user_exists(
                username=update_data.get('username', db_user.username),
                email=update_data.get('email', db_user.email),
                exclude_id=user_id
            )
        
        # Update the user object with the provided fields
        for key, value in update_data.items():
            setattr(db_user, key, value)
        
        try:
            return await self.resources_dao.update_user(db_user)
        except Exception as e:
            self.session.rollback()
            if isinstance(e, Exception):
                raise HTTPException(status_code=400, detail="Database constraint violated")
            raise HTTPException(status_code=400, detail=str(e))
    
    async def delete_user(self, user_id: int) -> Dict[str, str]:
        """Delete a user"""
        user = await self.get_user_by_id(user_id)
        
        await self.resources_dao.delete_user(user)
        return {"status": "success"}
    
    # Employee service methods
    async def get_all_employees(self) -> List[Employee]:
        """Get all employees"""
        return await self.resources_dao.get_all_employees()
    
    async def get_employee_by_id(self, employee_id: int) -> Employee:
        """Get an employee by ID, raising an exception if not found"""
        employee = await self.resources_dao.get_employee_by_id(employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        return employee
    
    async def check_employee_exists(self, employee_id: str, email: str, exclude_id: int = None) -> None:
        """Check if an employee with the given employee_id or email already exists"""
        # Check employee_id
        existing_employee_id = await self.resources_dao.get_employee_by_employee_id(employee_id)
        if existing_employee_id and (exclude_id is None or existing_employee_id.id != exclude_id):
            raise HTTPException(status_code=400, detail={"employee_id": "Employee ID already exists"})
        
        # Check email
        existing_email = await self.resources_dao.get_employee_by_email(email)
        if existing_email and (exclude_id is None or existing_email.id != exclude_id):
            raise HTTPException(status_code=400, detail={"email": "Email already exists"})
    
    async def create_employee(self, employee_data: EmployeeBase) -> Employee:
        """Create a new employee after validating data"""
        # Create an Employee instance from EmployeeBase
        employee = Employee.from_orm(employee_data) if hasattr(Employee, "from_orm") else Employee(**employee_data.dict())
        
        # Check if employee_id or email already exists
        await self.check_employee_exists(employee.employee_id, employee.email)
        
        try:
            return await self.resources_dao.create_employee(employee)
        except Exception as e:
            self.session.rollback()
            if isinstance(e, Exception):
                raise HTTPException(status_code=400, detail="Database constraint violated")
            raise HTTPException(status_code=400, detail=str(e))
    
    async def update_employee(self, employee_id: int, employee_update: EmployeeBase) -> Employee:
        """Update an employee after validating data"""
        # Get the existing employee
        db_employee = await self.get_employee_by_id(employee_id)
        
        # Get only the fields that were provided in the request
        try:
            update_data = employee_update.dict(exclude_unset=True)
        except AttributeError:
            # For newer versions of SQLModel/Pydantic
            update_data = employee_update.model_dump(exclude_unset=True)
        
        # Check uniqueness for employee_id and email if they are being updated
        if update_data.get('employee_id') or update_data.get('email'):
            await self.check_employee_exists(
                employee_id=update_data.get('employee_id', db_employee.employee_id),
                email=update_data.get('email', db_employee.email),
                exclude_id=employee_id
            )
        
        # Update the employee object with the provided fields
        for key, value in update_data.items():
            setattr(db_employee, key, value)
        
        try:
            return await self.resources_dao.update_employee(db_employee)
        except Exception as e:
            self.session.rollback()
            if isinstance(e, Exception):
                raise HTTPException(status_code=400, detail="Database constraint violated")
            raise HTTPException(status_code=400, detail=str(e))
    
    async def delete_employee(self, employee_id: int) -> Dict[str, str]:
        """Delete an employee"""
        employee = await self.get_employee_by_id(employee_id)
        
        await self.resources_dao.delete_employee(employee)
        return {"status": "success"}