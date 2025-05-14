from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Type, Callable, Any
from app.database import get_session
from app.resources.models import (
    UserRead, UserCreate,
    EmployeeRead, EmployeeCreate,
    SubscriberRead, SubscriberCreate,
    SubscriptionTier,
)
from app.resources.registry import registry

router = APIRouter(tags=["Resources"])


# Helper function to create a dependency that returns a resource name
def get_resource_name(name: str):
    def _get_resource_name():
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
        @router.get(f"/{resource_name}", response_model=List[read_model_cls], tags=[tag])
        async def get_all(
            session: Session = Depends(get_session),
            resource: str = resource_dependency,
        ):
            config = registry.get_config(resource)
            service = config.get_service(session)
            return await service.get_all()

        # POST - create
        @router.post(f"/{resource_name}", response_model=read_model_cls, tags=[tag])
        async def create(
            item_data: Any = Body(...),
            session: Session = Depends(get_session),
            resource: str = resource_dependency,
        ):
            config = registry.get_config(resource)
            service = config.get_service(session)
            
            # Convert dict to Pydantic model if needed
            if isinstance(item_data, dict):
                create_model = config.create_model_cls.model_validate(item_data)
                return await service.create(create_model)
            
            return await service.create(item_data)

        # GET by ID
        @router.get(
            f"/{resource_name}/{{item_id}}", response_model=read_model_cls, tags=[tag]
        )
        async def get_by_id(
            item_id: int,
            session: Session = Depends(get_session),
            resource: str = resource_dependency,
        ):
            config = registry.get_config(resource)
            service = config.get_service(session)
            item = await service.get_by_id(item_id)
            if not item:
                raise HTTPException(status_code=404, detail=f"{tag} not found")
            return item

        # PATCH - update
        @router.patch(
            f"/{resource_name}/{{item_id}}", response_model=read_model_cls, tags=[tag]
        )
        async def update(
            item_id: int,
            item_data: Any = Body(...),
            session: Session = Depends(get_session),
            resource: str = resource_dependency,
        ):
            config = registry.get_config(resource)
            service = config.get_service(session)
            
            # Convert dict to Pydantic model if needed
            if isinstance(item_data, dict):
                create_model = config.create_model_cls.model_validate(item_data)
                updated_item = await service.update(item_id, create_model)
            else:
                updated_item = await service.update(item_id, item_data)
                
            if not updated_item:
                raise HTTPException(status_code=404, detail=f"{tag} not found")
            return updated_item

        # DELETE
        @router.delete(f"/{resource_name}/{{item_id}}", tags=[tag])
        async def delete(
            item_id: int,
            session: Session = Depends(get_session),
            resource: str = resource_dependency,
        ):
            config = registry.get_config(resource)
            service = config.get_service(session)
            result = await service.delete(item_id)
            if not result:
                raise HTTPException(status_code=404, detail=f"{tag} not found")
            return {"message": f"{tag} deleted successfully"}

# Create all the dynamic routes
create_dynamic_resource_routes()

# Add custom resource-specific routes that don't fit the CRUD pattern
@router.get("/users/by-username/{username}", response_model=UserRead, tags=["Users"])
async def get_user_by_username(username: str, session: Session = Depends(get_session)):
    config = registry.get_config("users")
    service = config.get_service(session)
    return await service.get_by_username(username)


@router.get(
    "/employees/by-department/{department}",
    response_model=List[EmployeeRead],
    tags=["Employees"],
)
async def get_employees_by_department(
    department: str, session: Session = Depends(get_session)
):
    config = registry.get_config("employees")
    service = config.get_service(session)
    return await service.get_employees_by_department(department)


@router.get(
    "/employees/by-position/{position}",
    response_model=List[EmployeeRead],
    tags=["Employees"],
)
async def get_employees_by_position(
    position: str, session: Session = Depends(get_session)
):
    config = registry.get_config("employees")
    service = config.get_service(session)
    return await service.get_employees_by_position(position)


# Custom routes for Subscribers
@router.get(
    "/subscribers/by-email/{email}", response_model=SubscriberRead, tags=["Subscribers"]
)
async def get_subscriber_by_email(email: str, session: Session = Depends(get_session)):
    config = registry.get_config("subscribers")
    service = config.get_service(session)
    return await service.get_by_email(email)


@router.get(
    "/subscribers/by-tier/{tier}", response_model=List[SubscriberRead], tags=["Subscribers"]
)
async def get_subscribers_by_tier(
    tier: SubscriptionTier, session: Session = Depends(get_session)
):
    config = registry.get_config("subscribers")
    service = config.get_service(session)
    return await service.get_by_subscription_tier(tier)


@router.get(
    "/subscribers/active", response_model=List[SubscriberRead], tags=["Subscribers"]
)
async def get_active_subscribers(session: Session = Depends(get_session)):
    config = registry.get_config("subscribers")
    service = config.get_service(session)
    return await service.get_active_subscribers()
