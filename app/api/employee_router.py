from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List
from app.database import get_session
from app.models.base import Employee, EmployeeBase
from app.service.employee_service import EmployeeService

router = APIRouter()

@router.get("/employees", response_model=List[Employee])
async def list_employees(session: Session = Depends(get_session)):
    employee_service = EmployeeService(session)
    return await employee_service.get_all_employees()

@router.post("/employees", response_model=Employee)
async def create_employee(employee_data: EmployeeBase, session: Session = Depends(get_session)):
    employee_service = EmployeeService(session)
    return await employee_service.create_employee(employee_data)

@router.get("/employees/{employee_id}", response_model=Employee)
async def get_employee(employee_id: int, session: Session = Depends(get_session)):
    employee_service = EmployeeService(session)
    return await employee_service.get_employee_by_id(employee_id)

@router.patch("/employees/{employee_id}", response_model=Employee)
async def update_employee(
    employee_id: int,
    employee_update: EmployeeBase,
    session: Session = Depends(get_session)
):
    employee_service = EmployeeService(session)
    return await employee_service.update_employee(employee_id, employee_update)

@router.delete("/employees/{employee_id}")
async def delete_employee(employee_id: int, session: Session = Depends(get_session)):
    employee_service = EmployeeService(session)
    return await employee_service.delete_employee(employee_id)