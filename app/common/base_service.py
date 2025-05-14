from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import TypeVar, Generic, Type, List, Optional, Any, Dict
from fastapi import HTTPException
from app.common.base_dao import GenericDAO

T = TypeVar("T")  # SQLAlchemy model
CreateT = TypeVar("CreateT", bound=BaseModel)  # Pydantic model


class GenericService(Generic[T, CreateT]):
    """Generic Service with basic CRUD operations and validation hooks"""

    def __init__(
        self, session: Session, model_class: Type[T], create_model_class: Type[CreateT]
    ):
        self.session = session
        self.model_class = model_class
        self.create_model_class = create_model_class
        self.dao = GenericDAO[T, CreateT](session, model_class)

    # Hook methods for validation - can be overridden by subclasses
    async def before_create(self, item_data: CreateT) -> CreateT:
        """Hook to run before creating a record - override for validation"""
        return item_data

    async def before_update(self, item_id: int, item_data: CreateT) -> CreateT:
        """Hook to run before updating a record - override for validation"""
        return item_data

    # CRUD methods that use the DAO
    async def get_all(self) -> List[T]:
        """Get all records"""
        return await self.dao.get_all()

    async def get_by_id(self, item_id: int) -> Optional[T]:
        """Get a record by ID"""
        return await self.dao.get_by_id(item_id)

    async def create(self, item_data: CreateT) -> T:
        """Create a new record with validation"""
        # Run pre-create hook for validation
        validated_data = await self.before_create(item_data)
        return await self.dao.create(validated_data)

    async def update(self, item_id: int, item_data: CreateT) -> Optional[T]:
        """Update an existing record with validation"""
        # Run pre-update hook for validation
        validated_data = await self.before_update(item_id, item_data)
        return await self.dao.update(item_id, validated_data)

    async def delete(self, item_id: int) -> bool:
        """Delete a record"""
        return await self.dao.delete(item_id)
