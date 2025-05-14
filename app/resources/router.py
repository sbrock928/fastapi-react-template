from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Type, Callable, Any, Dict, Optional, Union, cast, TypeVar, Generic
from app.core.dependencies import SessionDep
from app.resources.models import (
    UserRead,
    UserCreate,
    EmployeeRead,
    EmployeeCreate,
    SubscriberRead,
    SubscriberCreate,
    SubscriptionTier,
)
from app.resources.registry import registry, ResourceConfig
from pydantic import BaseModel

router = APIRouter(tags=["Resources"])

# Type for SQLAlchemy model
T = TypeVar('T')
# Type for Pydantic read model
ReadT = TypeVar('ReadT', bound=BaseModel)

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

    for config in registry.get_all_configs():
        resource_name = config.name
        read_model_cls = config.read_model_cls
        create_model_cls = config.create_model_cls
        tag = config.tag

        # Create a dependency that returns this resource name
        resource_dependency = Depends(get_resource_name(resource_name))

        # GET all
        @router.get(
            f"/{resource_name}", response_model=List[read_model_cls], tags=[tag]
        )
        async def get_all(
            session: SessionDep,
            resource: str = resource_dependency,
        ):
            config = registry.get_config(resource)
            if not config:
                raise HTTPException(
                    status_code=404, detail=f"Resource {resource} not configured"
                )
            service = config.get_service(session)
            db_items = await service.get_all()
            # Convert SQLAlchemy models to Pydantic models
            return convert_list_to_pydantic(db_items, config.read_model_cls)

        # POST - create
        @router.post(f"/{resource_name}", response_model=read_model_cls, tags=[tag])
        async def create(
            session: SessionDep,
            item_data: Any = Body(...),
            resource: str = resource_dependency,
        ):
            config = registry.get_config(resource)
            if not config:
                raise HTTPException(
                    status_code=404, detail=f"Resource {resource} not configured"
                )
            service = config.get_service(session)

            # Convert dict to Pydantic model if needed
            if isinstance(item_data, dict):
                create_model = config.create_model_cls.model_validate(item_data)
                db_item = await service.create(create_model)
            else:
                db_item = await service.create(item_data)
                
            # Convert SQLAlchemy model to Pydantic model
            return convert_to_pydantic(db_item, config.read_model_cls)

        # GET by ID
        @router.get(
            f"/{resource_name}/{{item_id}}", response_model=read_model_cls, tags=[tag]
        )
        async def get_by_id(
            session: SessionDep,
            item_id: int,
            resource: str = resource_dependency,
        ):
            config = registry.get_config(resource)
            if not config:
                raise HTTPException(
                    status_code=404, detail=f"Resource {resource} not configured"
                )
            service = config.get_service(session)
            db_item = await service.get_by_id(item_id)
            if not db_item:
                raise HTTPException(status_code=404, detail=f"{tag} not found")
            
            # Convert SQLAlchemy model to Pydantic model
            return convert_to_pydantic(db_item, config.read_model_cls)

        # PATCH - update
        @router.patch(
            f"/{resource_name}/{{item_id}}", response_model=read_model_cls, tags=[tag]
        )
        async def update(
            session: SessionDep,
            item_id: int,
            item_data: Any = Body(...),
            resource: str = resource_dependency,
        ):
            config = registry.get_config(resource)
            if not config:
                raise HTTPException(
                    status_code=404, detail=f"Resource {resource} not configured"
                )
            service = config.get_service(session)

            # Convert dict to Pydantic model if needed
            if isinstance(item_data, dict):
                create_model = config.create_model_cls.model_validate(item_data)
                db_item = await service.update(item_id, create_model)
            else:
                db_item = await service.update(item_id, item_data)

            if not db_item:
                raise HTTPException(status_code=404, detail=f"{tag} not found")
                
            # Convert SQLAlchemy model to Pydantic model
            return convert_to_pydantic(db_item, config.read_model_cls)

        # DELETE
        @router.delete(f"/{resource_name}/{{item_id}}", tags=[tag])
        async def delete(
            session: SessionDep,
            item_id: int,
            resource: str = resource_dependency,
        ):
            config = registry.get_config(resource)
            if not config:
                raise HTTPException(
                    status_code=404, detail=f"Resource {resource} not configured"
                )
            service = config.get_service(session)
            result = await service.delete(item_id)
            if not result:
                raise HTTPException(status_code=404, detail=f"{tag} not found")
            return {"message": f"{tag} deleted successfully"}


# Create all the dynamic routes
create_dynamic_resource_routes()

# Add custom resource-specific routes that don't fit the CRUD pattern
@router.get("/users/by-username/{username}", response_model=UserRead, tags=["Users"])
async def get_user_by_username(username: str, session: SessionDep):
    config = registry.get_config("users")
    if not config:
        raise HTTPException(status_code=404, detail="Users resource not configured")
    service = config.get_service(session)
    db_user = await service.get_by_username(username)
    # Convert SQLAlchemy model to Pydantic model
    return convert_to_pydantic(db_user, UserRead)


@router.get(
    "/employees/by-department/{department}",
    response_model=List[EmployeeRead],
    tags=["Employees"],
)
async def get_employees_by_department(
    department: str, session: SessionDep
):
    config = registry.get_config("employees")
    if not config:
        raise HTTPException(status_code=404, detail="Employees resource not configured")
    service = config.get_service(session)
    db_employees = await service.get_employees_by_department(department)
    # Convert SQLAlchemy models to Pydantic models
    return convert_list_to_pydantic(db_employees, EmployeeRead)


@router.get(
    "/employees/by-position/{position}",
    response_model=List[EmployeeRead],
    tags=["Employees"],
)
async def get_employees_by_position(
    position: str, session: SessionDep
):
    config = registry.get_config("employees")
    if not config:
        raise HTTPException(status_code=404, detail="Employees resource not configured")
    service = config.get_service(session)
    db_employees = await service.get_employees_by_position(position)
    # Convert SQLAlchemy models to Pydantic models
    return convert_list_to_pydantic(db_employees, EmployeeRead)


# Custom routes for Subscribers
@router.get(
    "/subscribers/by-email/{email}", response_model=SubscriberRead, tags=["Subscribers"]
)
async def get_subscriber_by_email(email: str, session: SessionDep):
    config = registry.get_config("subscribers")
    if not config:
        raise HTTPException(
            status_code=404, detail="Subscribers resource not configured"
        )
    service = config.get_service(session)
    db_subscriber = await service.get_by_email(email)
    # Convert SQLAlchemy model to Pydantic model
    return convert_to_pydantic(db_subscriber, SubscriberRead)


@router.get(
    "/subscribers/by-tier/{tier}",
    response_model=List[SubscriberRead],
    tags=["Subscribers"],
)
async def get_subscribers_by_tier(
    tier: SubscriptionTier, session: SessionDep
):
    config = registry.get_config("subscribers")
    if not config:
        raise HTTPException(
            status_code=404, detail="Subscribers resource not configured"
        )
    service = config.get_service(session)
    db_subscribers = await service.get_by_subscription_tier(tier)
    # Convert SQLAlchemy models to Pydantic models
    return convert_list_to_pydantic(db_subscribers, SubscriberRead)


@router.get(
    "/subscribers/active", response_model=List[SubscriberRead], tags=["Subscribers"]
)
async def get_active_subscribers(session: SessionDep):
    config = registry.get_config("subscribers")
    if not config:
        raise HTTPException(
            status_code=404, detail="Subscribers resource not configured"
        )
    service = config.get_service(session)
    db_subscribers = await service.get_active_subscribers()
    # Convert SQLAlchemy models to Pydantic models
    return convert_list_to_pydantic(db_subscribers, SubscriberRead)
