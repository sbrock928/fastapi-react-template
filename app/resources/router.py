from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List, Type, Callable, Any
from app.database import get_session
from app.resources.models import User, UserBase, Employee, EmployeeBase
from app.resources.registry import registry  # Import registry instead of ResourcesService

router = APIRouter(tags=["Resources"])

# Function to create dynamic routes for all registered resources
def create_dynamic_resource_routes():
    """Create routes for all registered resources"""
    
    for config in registry.get_all_configs():
        resource_name = config.name
        model_cls = config.model_cls
        base_model_cls = config.base_model_cls
        tag = config.tag
        
        # GET all
        @router.get(
            f"/{resource_name}", 
            response_model=List[model_cls], 
            tags=[tag]
        )
        async def get_all(
            resource=resource_name,  # Capture the resource name in the closure
            session: Session = Depends(get_session)
        ):
            config = registry.get_config(resource)
            service = config.get_service(session)
            return await service.get_all()
        
        # POST - create
        @router.post(
            f"/{resource_name}", 
            response_model=model_cls, 
            tags=[tag]
        )
        async def create(
            item_data: base_model_cls,
            resource=resource_name,  # Capture the resource name in the closure
            session: Session = Depends(get_session)
        ):
            config = registry.get_config(resource)
            service = config.get_service(session)
            return await service.create(item_data)
        
        # GET by ID
        @router.get(
            f"/{resource_name}/{{item_id}}", 
            response_model=model_cls, 
            tags=[tag]
        )
        async def get_by_id(
            item_id: int,
            resource=resource_name,  # Capture the resource name in the closure
            session: Session = Depends(get_session)
        ):
            config = registry.get_config(resource)
            service = config.get_service(session)
            item = await service.get_by_id(item_id)
            if not item:
                raise HTTPException(status_code=404, detail=f"{tag} not found")
            return item
        
        # PATCH - update
        @router.patch(
            f"/{resource_name}/{{item_id}}", 
            response_model=model_cls, 
            tags=[tag]
        )
        async def update(
            item_id: int,
            item_data: base_model_cls,
            resource=resource_name,  # Capture the resource name in the closure
            session: Session = Depends(get_session)
        ):
            config = registry.get_config(resource)
            service = config.get_service(session)
            updated_item = await service.update(item_id, item_data)
            if not updated_item:
                raise HTTPException(status_code=404, detail=f"{tag} not found")
            return updated_item
        
        # DELETE
        @router.delete(
            f"/{resource_name}/{{item_id}}", 
            tags=[tag]
        )
        async def delete(
            item_id: int,
            resource=resource_name,  # Capture the resource name in the closure
            session: Session = Depends(get_session)
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
@router.get("/users/by-username/{username}", response_model=User, tags=["Users"])
async def get_user_by_username(
    username: str,
    session: Session = Depends(get_session)
):
    config = registry.get_config("users")
    service = config.get_service(session)
    return await service.get_by_username(username)

@router.get("/employees/by-department/{department}", response_model=List[Employee], tags=["Employees"])
async def get_employees_by_department(
    department: str,
    session: Session = Depends(get_session)
):
    config = registry.get_config("employees")
    service = config.get_service(session)
    return await service.get_employees_by_department(department)

@router.get("/employees/by-position/{position}", response_model=List[Employee], tags=["Employees"])
async def get_employees_by_position(
    position: str,
    session: Session = Depends(get_session)
):
    config = registry.get_config("employees")
    service = config.get_service(session)
    return await service.get_employees_by_position(position)