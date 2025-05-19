from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.core.dependencies import SessionDep
from app.resources.schemas import (
    UserRead,
    UserCreate,
    UserUpdate,
    EmployeeRead,
    EmployeeCreate,
    EmployeeUpdate,
    SubscriberRead,
    SubscriberCreate,
    SubscriberUpdate,
    SubscriptionTier,
)
from app.resources.service import UserService, EmployeeService, SubscriberService
from app.resources.dao import UserDAO, EmployeeDAO, SubscriberDAO

router = APIRouter(tags=["Resources"])


# Service factory functions for dependency injection
def get_user_service(session: SessionDep) -> UserService:
    return UserService(UserDAO(session))


def get_employee_service(session: SessionDep) -> EmployeeService:
    return EmployeeService(EmployeeDAO(session))


def get_subscriber_service(session: SessionDep) -> SubscriberService:
    return SubscriberService(SubscriberDAO(session))


# User routes
@router.get("/users", response_model=List[UserRead], tags=["Users"])
async def get_all_users(service=Depends(get_user_service)):
    """Get all users"""
    return await service.get_all()


@router.get("/users/{user_id}", response_model=UserRead, tags=["Users"])
async def get_user_by_id(user_id: int, service=Depends(get_user_service)):
    """Get a user by ID"""
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/users", response_model=UserRead, tags=["Users"])
async def create_user(user_data: UserCreate, service=Depends(get_user_service)):
    """Create a new user"""
    return await service.create(user_data)


@router.patch("/users/{user_id}", response_model=UserRead, tags=["Users"])
async def update_user(user_id: int, user_data: UserUpdate, service=Depends(get_user_service)):
    """Update a user"""
    user = await service.update(user_id, user_data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete("/users/{user_id}", tags=["Users"])
async def delete_user(user_id: int, service=Depends(get_user_service)):
    """Delete a user"""
    result = await service.delete(user_id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}


@router.get("/users/by-username/{username}", response_model=UserRead, tags=["Users"])
async def get_user_by_username(username: str, service=Depends(get_user_service)):
    """Get a user by username"""
    user = await service.get_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# Employee routes
@router.get("/employees", response_model=List[EmployeeRead], tags=["Employees"])
async def get_all_employees(service=Depends(get_employee_service)):
    """Get all employees"""
    return await service.get_all()


@router.get("/employees/{employee_id}", response_model=EmployeeRead, tags=["Employees"])
async def get_employee_by_id(employee_id: int, service=Depends(get_employee_service)):
    """Get an employee by ID"""
    employee = await service.get_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.post("/employees", response_model=EmployeeRead, tags=["Employees"])
async def create_employee(employee_data: EmployeeCreate, service=Depends(get_employee_service)):
    """Create a new employee"""
    return await service.create(employee_data)


@router.patch("/employees/{employee_id}", response_model=EmployeeRead, tags=["Employees"])
async def update_employee(
    employee_id: int, employee_data: EmployeeUpdate, service=Depends(get_employee_service)
):
    """Update an employee"""
    employee = await service.update(employee_id, employee_data)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.delete("/employees/{employee_id}", tags=["Employees"])
async def delete_employee(employee_id: int, service=Depends(get_employee_service)):
    """Delete an employee"""
    result = await service.delete(employee_id)
    if not result:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {"message": "Employee deleted successfully"}


@router.get(
    "/employees/by-department/{department}", response_model=List[EmployeeRead], tags=["Employees"]
)
async def get_employees_by_department(department: str, service=Depends(get_employee_service)):
    """Get employees by department"""
    employees = await service.get_employees_by_department(department)
    return employees


@router.get(
    "/employees/by-position/{position}", response_model=List[EmployeeRead], tags=["Employees"]
)
async def get_employees_by_position(position: str, service=Depends(get_employee_service)):
    """Get employees by position"""
    employees = await service.get_employees_by_position(position)
    return employees


# Subscriber routes
@router.get("/subscribers", response_model=List[SubscriberRead], tags=["Subscribers"])
async def get_all_subscribers(service=Depends(get_subscriber_service)):
    """Get all subscribers"""
    return await service.get_all()


@router.get("/subscribers/{subscriber_id}", response_model=SubscriberRead, tags=["Subscribers"])
async def get_subscriber_by_id(subscriber_id: int, service=Depends(get_subscriber_service)):
    """Get a subscriber by ID"""
    subscriber = await service.get_by_id(subscriber_id)
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return subscriber


@router.post("/subscribers", response_model=SubscriberRead, tags=["Subscribers"])
async def create_subscriber(
    subscriber_data: SubscriberCreate, service=Depends(get_subscriber_service)
):
    """Create a new subscriber"""
    return await service.create(subscriber_data)


@router.patch("/subscribers/{subscriber_id}", response_model=SubscriberRead, tags=["Subscribers"])
async def update_subscriber(
    subscriber_id: int, subscriber_data: SubscriberUpdate, service=Depends(get_subscriber_service)
):
    """Update a subscriber"""
    subscriber = await service.update(subscriber_id, subscriber_data)
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return subscriber


@router.delete("/subscribers/{subscriber_id}", tags=["Subscribers"])
async def delete_subscriber(subscriber_id: int, service=Depends(get_subscriber_service)):
    """Delete a subscriber"""
    result = await service.delete(subscriber_id)
    if not result:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return {"message": "Subscriber deleted successfully"}


@router.get("/subscribers/by-email/{email}", response_model=SubscriberRead, tags=["Subscribers"])
async def get_subscriber_by_email(email: str, service=Depends(get_subscriber_service)):
    """Get a subscriber by email"""
    subscriber = await service.get_by_email(email)
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return subscriber


@router.get(
    "/subscribers/by-tier/{tier}", response_model=List[SubscriberRead], tags=["Subscribers"]
)
async def get_subscribers_by_tier(tier: SubscriptionTier, service=Depends(get_subscriber_service)):
    """Get subscribers by tier"""
    subscribers = await service.get_by_subscription_tier(tier)
    return subscribers


@router.get("/subscribers/active", response_model=List[SubscriberRead], tags=["Subscribers"])
async def get_active_subscribers(service=Depends(get_subscriber_service)):
    """Get active subscribers"""
    subscribers = await service.get_active_subscribers()
    return subscribers
