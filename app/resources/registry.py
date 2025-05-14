from typing import Dict, Type, Callable, Optional, List, Any
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.common.base_service import GenericService
from app.resources.models import (
    User,
    UserCreate,
    UserRead,
    Employee,
    EmployeeCreate,
    EmployeeRead,
    Subscriber,
    SubscriberCreate,
    SubscriberRead,
)
from app.resources.service import UserService, EmployeeService, SubscriberService


class ResourceConfig:
    """Configuration for a resource"""

    def __init__(
        self,
        name: str,
        model_cls: Type,  # SQLAlchemy model
        create_model_cls: Type[BaseModel],  # Pydantic create model
        read_model_cls: Type[BaseModel],  # Pydantic read model
        tag: str,
        service_cls: Optional[Type[GenericService]] = None,
        service_factory: Optional[Callable[[Session], Any]] = None,
    ):
        self.name = name
        self.model_cls = model_cls
        self.create_model_cls = create_model_cls
        self.read_model_cls = read_model_cls
        self.tag = tag
        self.service_cls = service_cls
        self.service_factory = service_factory

    def get_service(self, session: Session) -> Any:
        """Get the service instance for this resource"""
        if self.service_factory:
            return self.service_factory(session)
        elif self.service_cls:
            return self.service_cls(session)
        else:
            # Default to generic service if none specified
            return GenericService(session, self.model_cls, self.create_model_cls)


# Registry of all resources
class ResourceRegistry:
    """Registry of all resources in the application"""

    def __init__(self):
        self.resources: Dict[str, ResourceConfig] = {}

    def register(self, config: ResourceConfig) -> None:
        """Register a resource"""
        self.resources[config.name] = config

    def get_config(self, name: str) -> Optional[ResourceConfig]:
        """Get a resource configuration by name"""
        return self.resources.get(name)

    def get_all_configs(self) -> List[ResourceConfig]:
        """Get all resource configurations"""
        return list(self.resources.values())


# Create the global registry
registry = ResourceRegistry()

# Register User resource
registry.register(
    ResourceConfig(
        name="users",
        model_cls=User,
        create_model_cls=UserCreate,
        read_model_cls=UserRead,
        tag="Users",
        service_cls=UserService,
    )
)

# Register Employee resource
registry.register(
    ResourceConfig(
        name="employees",
        model_cls=Employee,
        create_model_cls=EmployeeCreate,
        read_model_cls=EmployeeRead,
        tag="Employees",
        service_cls=EmployeeService,
    )
)

# Register Subscriber resource
registry.register(
    ResourceConfig(
        name="subscribers",
        model_cls=Subscriber,
        create_model_cls=SubscriberCreate,
        read_model_cls=SubscriberRead,
        tag="Subscribers",
        service_cls=SubscriberService,
    )
)
