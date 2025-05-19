from fastapi import APIRouter, Depends, HTTPException
from typing import List, Annotated

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


# Dependency factories
def get_user_service(session: SessionDep) -> UserService:
    return UserService(UserDAO(session))


def get_employee_service(session: SessionDep) -> EmployeeService:
    return EmployeeService(EmployeeDAO(session))


def get_subscriber_service(session: SessionDep) -> SubscriberService:
    return SubscriberService(SubscriberDAO(session))


# Type aliases for dependencies
UserDep = Annotated[UserService, Depends(get_user_service)]
EmployeeDep = Annotated[EmployeeService, Depends(get_employee_service)]
SubscriberDep = Annotated[SubscriberService, Depends(get_subscriber_service)]

# --- User routes ---


@router.get("/users", response_model=List[UserRead])
async def get_all_users(service: UserDep) -> List[UserRead]:
    return await service.get_all()


@router.get("/users/{user_id}", response_model=UserRead)
async def get_user_by_id(user_id: int, service: UserDep) -> UserRead:
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/users", response_model=UserRead)
async def create_user(user_data: UserCreate, service: UserDep) -> UserRead:
    return await service.create(user_data)


@router.patch("/users/{user_id}", response_model=UserRead)
async def update_user(user_id: int, user_data: UserUpdate, service: UserDep) -> UserRead:
    user = await service.update(user_id, user_data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, service: UserDep) -> dict[str, str]:
    result = await service.delete(user_id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}


@router.get("/users/by-username/{username}", response_model=UserRead)
async def get_user_by_username(username: str, service: UserDep) -> UserRead:
    user = await service.get_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# --- Employee routes ---


@router.get("/employees", response_model=List[EmployeeRead])
async def get_all_employees(service: EmployeeDep) -> List[EmployeeRead]:
    return await service.get_all()


@router.get("/employees/{employee_id}", response_model=EmployeeRead)
async def get_employee_by_id(employee_id: int, service: EmployeeDep) -> EmployeeRead:
    employee = await service.get_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.post("/employees", response_model=EmployeeRead)
async def create_employee(employee_data: EmployeeCreate, service: EmployeeDep) -> EmployeeRead:
    return await service.create(employee_data)


@router.patch("/employees/{employee_id}", response_model=EmployeeRead)
async def update_employee(
    employee_id: int, employee_data: EmployeeUpdate, service: EmployeeDep
) -> EmployeeRead:
    employee = await service.update(employee_id, employee_data)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.delete("/employees/{employee_id}")
async def delete_employee(employee_id: int, service: EmployeeDep) -> dict[str, str]:
    result = await service.delete(employee_id)
    if not result:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {"message": "Employee deleted successfully"}


@router.get("/employees/by-department/{department}", response_model=List[EmployeeRead])
async def get_employees_by_department(department: str, service: EmployeeDep) -> List[EmployeeRead]:
    return await service.get_employees_by_department(department)


@router.get("/employees/by-position/{position}", response_model=List[EmployeeRead])
async def get_employees_by_position(position: str, service: EmployeeDep) -> List[EmployeeRead]:
    return await service.get_employees_by_position(position)


# --- Subscriber routes ---


@router.get("/subscribers", response_model=List[SubscriberRead])
async def get_all_subscribers(service: SubscriberDep) -> List[SubscriberRead]:
    return await service.get_all()


@router.get("/subscribers/{subscriber_id}", response_model=SubscriberRead)
async def get_subscriber_by_id(subscriber_id: int, service: SubscriberDep) -> SubscriberRead:
    subscriber = await service.get_by_id(subscriber_id)
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return subscriber


@router.post("/subscribers", response_model=SubscriberRead)
async def create_subscriber(
    subscriber_data: SubscriberCreate, service: SubscriberDep
) -> SubscriberRead:
    return await service.create(subscriber_data)


@router.patch("/subscribers/{subscriber_id}", response_model=SubscriberRead)
async def update_subscriber(
    subscriber_id: int, subscriber_data: SubscriberUpdate, service: SubscriberDep
) -> SubscriberRead:
    subscriber = await service.update(subscriber_id, subscriber_data)
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return subscriber


@router.delete("/subscribers/{subscriber_id}")
async def delete_subscriber(subscriber_id: int, service: SubscriberDep) -> dict[str, str]:
    result = await service.delete(subscriber_id)
    if not result:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return {"message": "Subscriber deleted successfully"}


@router.get("/subscribers/by-email/{email}", response_model=SubscriberRead)
async def get_subscriber_by_email(email: str, service: SubscriberDep) -> SubscriberRead:
    subscriber = await service.get_by_email(email)
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return subscriber


@router.get("/subscribers/by-tier/{tier}", response_model=List[SubscriberRead])
async def get_subscribers_by_tier(
    tier: SubscriptionTier, service: SubscriberDep
) -> List[SubscriberRead]:
    return await service.get_by_subscription_tier(tier)


@router.get("/subscribers/active", response_model=List[SubscriberRead])
async def get_active_subscribers(service: SubscriberDep) -> List[SubscriberRead]:
    return await service.get_active_subscribers()
