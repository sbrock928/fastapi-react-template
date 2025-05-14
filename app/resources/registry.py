from typing import Dict, Type, Callable, Optional, List, Any, TypeVar, Generic, cast
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.common.base_service import GenericService
from app.resources.models import User, Employee, Subscriber
from app.resources.schemas import (
    UserCreate,
    UserUpdate,
    UserRead,
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeRead,
    SubscriberCreate,
    SubscriberUpdate,
    SubscriberRead,
)
from app.resources.service import UserService, EmployeeService, SubscriberService

# Type variables for models
ModelType = TypeVar("ModelType")
CreateModelType = TypeVar("CreateModelType", bound=BaseModel)
UpdateModelType = TypeVar("UpdateModelType", bound=BaseModel)
ReadModelType = TypeVar("ReadModelType", bound=BaseModel)

# Specialized type for services
ServiceType = TypeVar("ServiceType", bound=GenericService)


class ResourceConfig(Generic[ModelType, CreateModelType, UpdateModelType, ReadModelType]):
    """Configuration for a resource"""

    def __init__(
        self,
        name: str,
        model_cls: Type[ModelType],  # SQLAlchemy model
        create_model_cls: Type[CreateModelType],  # Pydantic create model
        update_model_cls: Type[UpdateModelType],  # Pydantic update model
        read_model_cls: Type[ReadModelType],  # Pydantic read model
        tag: str,
        service_cls: Optional[Type[Any]] = None,
        service_factory: Optional[Callable[[Session], Any]] = None,
    ):
        self.name = name
        self.model_cls = model_cls
        self.create_model_cls = create_model_cls
        self.update_model_cls = update_model_cls
        self.read_model_cls = read_model_cls
        self.tag = tag
        self.service_cls = service_cls
        self.service_factory = service_factory

    def get_service(self, session: Session) -> Any:
        """Get the service instance for this resource"""
        if self.service_factory:
            return self.service_factory(session)
        elif self.service_cls:
            try:
                # Some services expect only the session parameter
                return self.service_cls(session)
            except TypeError:
                # For services that need more parameters
                return self.service_cls(session, self.model_cls, self.create_model_cls, self.read_model_cls)
        else:
            # Default to generic service if none specified
            return GenericService(
                session=session,
                model_class=self.model_cls,
                create_model_class=self.create_model_cls,
                read_model_class=self.read_model_cls,
            )


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
        update_model_cls=UserUpdate,
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
        update_model_cls=EmployeeUpdate,
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
        update_model_cls=SubscriberUpdate,
        read_model_cls=SubscriberRead,
        tag="Subscribers",
        service_cls=SubscriberService,
    )
)
