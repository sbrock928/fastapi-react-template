from sqlmodel import Session, select
from typing import List, Optional, Dict, Any
from app.resources.models import User, Employee
from sqlalchemy.exc import IntegrityError

class ResourcesDAO:
    def __init__(self, session: Session):
        self.session = session
    
    # User DAO methods
    async def get_all_users(self) -> List[User]:
        """Get all users from the database"""
        users = self.session.exec(select(User)).all()
        return users
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get a user by ID"""
        user = self.session.get(User, user_id)
        return user
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by username"""
        user_query = select(User).where(User.username == username)
        user = self.session.exec(user_query).first()
        return user
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email"""
        user_query = select(User).where(User.email == email)
        user = self.session.exec(user_query).first()
        return user
    
    async def create_user(self, user: User) -> User:
        """Create a new user"""
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
    
    async def update_user(self, user: User) -> User:
        """Update an existing user"""
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
    
    async def delete_user(self, user: User) -> None:
        """Delete a user"""
        self.session.delete(user)
        self.session.commit()
    
    # Employee DAO methods
    async def get_all_employees(self) -> List[Employee]:
        """Get all employees from the database"""
        employees = self.session.exec(select(Employee)).all()
        return employees
    
    async def get_employee_by_id(self, employee_id: int) -> Optional[Employee]:
        """Get an employee by ID"""
        employee = self.session.get(Employee, employee_id)
        return employee
    
    async def get_employee_by_employee_id(self, employee_id: str) -> Optional[Employee]:
        """Get an employee by employee_id field"""
        employee_query = select(Employee).where(Employee.employee_id == employee_id)
        employee = self.session.exec(employee_query).first()
        return employee
    
    async def get_employee_by_email(self, email: str) -> Optional[Employee]:
        """Get an employee by email"""
        employee_query = select(Employee).where(Employee.email == email)
        employee = self.session.exec(employee_query).first()
        return employee
    
    async def create_employee(self, employee: Employee) -> Employee:
        """Create a new employee"""
        self.session.add(employee)
        self.session.commit()
        self.session.refresh(employee)
        return employee
    
    async def update_employee(self, employee: Employee) -> Employee:
        """Update an existing employee"""
        self.session.add(employee)
        self.session.commit()
        self.session.refresh(employee)
        return employee
    
    async def delete_employee(self, employee: Employee) -> None:
        """Delete an employee"""
        self.session.delete(employee)
        self.session.commit()