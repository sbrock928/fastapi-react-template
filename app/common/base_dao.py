from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import (
    TypeVar,
    Generic,
    Type,
    List,
    Optional,
    Any,
    Dict,
    Protocol,
    cast,
    Dict,
)


# Protocol for models with common attributes
class UserModel(Protocol):
    username: str


class EmailModel(Protocol):
    email: str


class EmployeeModel(Protocol):
    employee_id: str


class DepartmentModel(Protocol):
    department: str


class PositionModel(Protocol):
    position: str


class SubscriptionModel(Protocol):
    subscription_tier: str


class ActiveModel(Protocol):
    is_active: bool


# Type variable for our generic class
T = TypeVar("T")  # SQLAlchemy model


class GenericDAO(Generic[T]):
    """Generic Data Access Object with basic CRUD operations"""

    def __init__(self, session: Session, model_class: Type[T]):
        self.session = session
        self.model_class = model_class

    async def get_all(self) -> List[T]:
        """Get all records"""
        result = self.session.execute(select(self.model_class))
        items = result.scalars().all()
        return items

    async def get_by_id(self, item_id: int) -> Optional[T]:
        """Get a record by ID"""
        item = self.session.get(self.model_class, item_id)
        return item

    async def create(self, item_dict: Dict[str, Any]) -> T:
        """Create a new record directly from a dictionary of values"""
        # Create SQLAlchemy model instance
        item = self.model_class(**item_dict)

        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    async def update(self, item_id: int, update_dict: Dict[str, Any]) -> Optional[T]:
        """Update an existing record using dictionary of values"""
        item = await self.get_by_id(item_id)
        if not item:
            return None

        # Update only the provided fields
        for key, value in update_dict.items():
            setattr(item, key, value)

        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    async def delete(self, item_id: int) -> bool:
        """Delete a record"""
        item = await self.get_by_id(item_id)
        if not item:
            return False

        self.session.delete(item)
        self.session.commit()
        return True

    # Extended methods needed by services based on mypy errors
    async def get_by_username(self, username: str) -> Optional[T]:
        """Get a user by username"""
        stmt = select(self.model_class).where(getattr(self.model_class, "username") == username)
        result = self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_email(self, email: str) -> Optional[T]:
        """Get a record by email"""
        stmt = select(self.model_class).where(getattr(self.model_class, "email") == email)
        result = self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_employee_id(self, employee_id: str) -> Optional[T]:
        """Get an employee by employee_id"""
        stmt = select(self.model_class).where(
            getattr(self.model_class, "employee_id") == employee_id
        )
        result = self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_department(self, department: str) -> List[T]:
        """Get employees by department"""
        stmt = select(self.model_class).where(getattr(self.model_class, "department") == department)
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_position(self, position: str) -> List[T]:
        """Get employees by position"""
        stmt = select(self.model_class).where(getattr(self.model_class, "position") == position)
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_subscription_tier(self, subscription_tier: str) -> List[T]:
        """Get subscribers by subscription tier"""
        stmt = select(self.model_class).where(
            getattr(self.model_class, "subscription_tier") == subscription_tier
        )
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_subscribers(self) -> List[T]:
        """Get all active subscribers"""
        stmt = select(self.model_class).where(getattr(self.model_class, "is_active") == True)
        result = self.session.execute(stmt)
        return list(result.scalars().all())
