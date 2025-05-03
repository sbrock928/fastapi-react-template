from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List
from app.database import get_session
from app.resources.models import User, UserBase, Employee, EmployeeBase
from app.resources.service import ResourcesService

router = APIRouter(tags=["Resources"])

# User routes
@router.get("/users", response_model=List[User], tags=["Users"])
async def list_users(session: Session = Depends(get_session)):
    resource_service = ResourcesService(session)
    return await resource_service.get_all_users()

@router.post("/users", response_model=User, tags=["Users"])
async def create_user(user_data: UserBase, session: Session = Depends(get_session)):
    resource_service = ResourcesService(session)
    return await resource_service.create_user(user_data)

@router.get("/users/{user_id}", response_model=User, tags=["Users"])
async def get_user(user_id: int, session: Session = Depends(get_session)):
    resource_service = ResourcesService(session)
    return await resource_service.get_user_by_id(user_id)

@router.patch("/users/{user_id}", response_model=User,  tags=["Users"])
async def update_user(
    user_id: int,
    user_update: UserBase,
    session: Session = Depends(get_session)
):
    resource_service = ResourcesService(session)
    return await resource_service.update_user(user_id, user_update)

@router.delete("/users/{user_id}", tags=["Users"])  
async def delete_user(user_id: int, session: Session = Depends(get_session)):
    resource_service = ResourcesService(session)
    return await resource_service.delete_user(user_id)

# Employee routes
@router.get("/employees", response_model=List[Employee], tags=["Employees"])    
async def list_employees(session: Session = Depends(get_session)):
    resource_service = ResourcesService(session)
    return await resource_service.get_all_employees()

@router.post("/employees", response_model=Employee, tags=["Employees"])
async def create_employee(employee_data: EmployeeBase, session: Session = Depends(get_session)):
    resource_service = ResourcesService(session)
    return await resource_service.create_employee(employee_data)

@router.get("/employees/{employee_id}", response_model=Employee, tags=["Employees"])
async def get_employee(employee_id: int, session: Session = Depends(get_session)):
    resource_service = ResourcesService(session)
    return await resource_service.get_employee_by_id(employee_id)

@router.patch("/employees/{employee_id}", response_model=Employee,  tags=["Employees"])
async def update_employee(
    employee_id: int,
    employee_update: EmployeeBase,
    session: Session = Depends(get_session)
):
    resource_service = ResourcesService(session)
    return await resource_service.update_employee(employee_id, employee_update)

@router.delete("/employees/{employee_id}", tags=["Employees"])
async def delete_employee(employee_id: int, session: Session = Depends(get_session)):
    resource_service = ResourcesService(session)
    return await resource_service.delete_employee(employee_id)