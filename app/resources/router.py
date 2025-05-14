from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import (
    List,
    Type,
    Callable,
    Any,
    Dict,
    Optional,
    Union,
    cast,
    TypeVar,
    Generic,
)
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
from app.resources.registry import registry, ResourceConfig
from app.resources.service import UserService, EmployeeService, SubscriberService
from app.resources.dao import UserDAO, EmployeeDAO, SubscriberDAO
from app.resources.models import User, Employee, Subscriber
from pydantic import BaseModel

router = APIRouter(tags=["Resources"])

# Type for SQLAlchemy model
T = TypeVar("T")
# Type for Pydantic read model
ReadT = TypeVar("ReadT", bound=BaseModel)
# Type for Pydantic create model
CreateT = TypeVar("CreateT", bound=BaseModel)
# Type for Pydantic update model
UpdateT = TypeVar("UpdateT", bound=BaseModel)


# Service factory functions for dependency injection
def get_user_service(session: SessionDep) -> UserService:
    return UserService(session, UserDAO(session, User))


def get_employee_service(session: SessionDep) -> EmployeeService:
    return EmployeeService(session, EmployeeDAO(session, Employee))


def get_subscriber_service(session: SessionDep) -> SubscriberService:
    return SubscriberService(session, SubscriberDAO(session, Subscriber))


# Helper function to create a service factory for dynamic resources
def get_resource_service_factory(resource_name: str):
    def _get_service(session: SessionDep):
        config = registry.get_config(resource_name)
        if not config:
            raise HTTPException(status_code=404, detail=f"Resource {resource_name} not configured")
        return config.get_service(session)

    return _get_service


# Helper function to convert SQLAlchemy models to Pydantic models
def convert_to_pydantic(db_model: T, pydantic_model_cls: Type[ReadT]) -> ReadT:
    """Convert a SQLAlchemy model instance to a Pydantic model instance"""
    if db_model is None:
        return None
    # Use from_orm for compatibility with older Pydantic versions
    if hasattr(pydantic_model_cls, "from_orm"):
        return pydantic_model_cls.from_orm(db_model)
    # Use model_validate for Pydantic v2
    return pydantic_model_cls.model_validate(db_model)


def convert_list_to_pydantic(db_models: List[T], pydantic_model_cls: Type[ReadT]) -> List[ReadT]:
    """Convert a list of SQLAlchemy model instances to a list of Pydantic model instances"""
    return [convert_to_pydantic(model, pydantic_model_cls) for model in db_models]


# Helper function to create a dependency that returns a resource name
def get_resource_name(name: str):
    def _get_resource_name() -> str:
        return name

    return _get_resource_name


# Function to create dynamic routes for all registered resources
def create_dynamic_resource_routes():
    """Create routes for all registered resources"""

    # Define route creation functions to avoid closure variable capture issues
    def create_get_all_route(resource_name, read_model_cls, tag, service_factory):
        @router.get(f"/{resource_name}", response_model=List[read_model_cls], tags=[tag])
        async def get_all(service=Depends(service_factory)):
            db_items = await service.get_all()
            return convert_list_to_pydantic(db_items, read_model_cls)

        return get_all

    def create_create_route(resource_name, read_model_cls, create_model_cls, tag, service_factory):
        @router.post(f"/{resource_name}", response_model=read_model_cls, tags=[tag])
        async def create(item_data: create_model_cls, service=Depends(service_factory)):
            db_item = await service.create(item_data)
            return convert_to_pydantic(db_item, read_model_cls)

        return create

    def create_get_by_id_route(resource_name, read_model_cls, tag, service_factory):
        @router.get(f"/{resource_name}/{{item_id}}", response_model=read_model_cls, tags=[tag])
        async def get_by_id(item_id: int, service=Depends(service_factory)):
            db_item = await service.get_by_id(item_id)
            if not db_item:
                raise HTTPException(status_code=404, detail=f"{tag} not found")
            return convert_to_pydantic(db_item, read_model_cls)

        return get_by_id

    def create_update_route(resource_name, read_model_cls, update_model_cls, tag, service_factory):
        @router.patch(f"/{resource_name}/{{item_id}}", response_model=read_model_cls, tags=[tag])
        async def update(
            item_id: int, item_data: update_model_cls, service=Depends(service_factory)
        ):
            db_item = await service.update(item_id, item_data)
            if not db_item:
                raise HTTPException(status_code=404, detail=f"{tag} not found")
            return convert_to_pydantic(db_item, read_model_cls)

        return update

    def create_delete_route(resource_name, tag, service_factory):
        @router.delete(f"/{resource_name}/{{item_id}}", tags=[tag])
        async def delete(item_id: int, service=Depends(service_factory)):
            result = await service.delete(item_id)
            if not result:
                raise HTTPException(status_code=404, detail=f"{tag} not found")
            return {"message": f"{tag} deleted successfully"}

        return delete

    # Register routes for each resource
    for config in registry.get_all_configs():
        resource_name = config.name
        read_model_cls = config.read_model_cls
        create_model_cls = config.create_model_cls
        update_model_cls = config.update_model_cls
        tag = config.tag

        # Create a service factory for this resource
        service_factory = get_resource_service_factory(resource_name)

        # Register the routes using the route creation functions
        create_get_all_route(resource_name, read_model_cls, tag, service_factory)
        create_create_route(resource_name, read_model_cls, create_model_cls, tag, service_factory)
        create_get_by_id_route(resource_name, read_model_cls, tag, service_factory)
        create_update_route(resource_name, read_model_cls, update_model_cls, tag, service_factory)
        create_delete_route(resource_name, tag, service_factory)


# Create all the dynamic routes
create_dynamic_resource_routes()


# Add custom resource-specific routes that don't fit the CRUD pattern
@router.get("/users/by-username/{username}", response_model=UserRead, tags=["Users"])
async def get_user_by_username(username: str, service=Depends(get_user_service)):
    """Get a user by username"""
    return await service.get_by_username(username)


@router.get(
    "/employees/by-department/{department}",
    response_model=List[EmployeeRead],
    tags=["Employees"],
)
async def get_employees_by_department(department: str, service=Depends(get_employee_service)):
    """Get employees by department"""
    return await service.get_employees_by_department(department)


@router.get(
    "/employees/by-position/{position}",
    response_model=List[EmployeeRead],
    tags=["Employees"],
)
async def get_employees_by_position(position: str, service=Depends(get_employee_service)):
    """Get employees by position"""
    return await service.get_employees_by_position(position)


# Custom routes for Subscribers
@router.get("/subscribers/by-email/{email}", response_model=SubscriberRead, tags=["Subscribers"])
async def get_subscriber_by_email(email: str, service=Depends(get_subscriber_service)):
    """Get a subscriber by email"""
    return await service.get_by_email(email)


@router.get(
    "/subscribers/by-tier/{tier}",
    response_model=List[SubscriberRead],
    tags=["Subscribers"],
)
async def get_subscribers_by_tier(tier: SubscriptionTier, service=Depends(get_subscriber_service)):
    """Get subscribers by tier"""
    return await service.get_by_subscription_tier(tier)


@router.get("/subscribers/active", response_model=List[SubscriberRead], tags=["Subscribers"])
async def get_active_subscribers(service=Depends(get_subscriber_service)):
    """Get active subscribers"""
    return await service.get_active_subscribers()
