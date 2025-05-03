from sqlmodel import Session, select
from typing import List, Optional, Dict, Any
from app.models.base import Employee
from sqlalchemy.exc import IntegrityError

class EmployeeDAO:
    def __init__(self, session: Session):
        self.session = session
    
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