from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import TypeVar, Generic, Type, List, Optional, Any, Dict
from fastapi import HTTPException
from app.common.base_dao import GenericDAO

T = TypeVar("T")  # SQLAlchemy model
CreateT = TypeVar("CreateT", bound=BaseModel)  # Pydantic create model
UpdateT = TypeVar("UpdateT", bound=BaseModel)  # Pydantic update model
ReadT = TypeVar("ReadT", bound=BaseModel)  # Pydantic read model


class GenericService(Generic[T, CreateT, UpdateT, ReadT]):
    """Generic Service with basic CRUD operations and validation hooks"""

    def __init__(
        self, 
        session: Session, 
        model_class: Type[T], 
        create_model_class: Type[CreateT],
        update_model_class: Type[UpdateT],
        read_model_class: Type[ReadT]
    ):
        self.session = session
        self.model_class = model_class
        self.create_model_class = create_model_class
        self.update_model_class = update_model_class
        self.read_model_class = read_model_class
        self.dao = GenericDAO[T](session, model_class)

    # Hook methods for validation - can be overridden by subclasses
    async def before_create(self, item_data: CreateT) -> CreateT:
        """Hook to run before creating a record - override for validation"""
        return item_data

    async def before_update(self, item_id: int, item_data: UpdateT) -> UpdateT:
        """Hook to run before updating a record - override for validation"""
        return item_data

    # Conversion methods
    def to_db_model_dict(self, item_data: BaseModel) -> Dict[str, Any]:
        """Convert Pydantic schema to dictionary compatible with SQLAlchemy model"""
        return item_data.model_dump(exclude_unset=True)

    def to_read_model(self, db_model: T) -> ReadT:
        """Convert SQLAlchemy model to Pydantic read model"""
        return self.read_model_class.model_validate(db_model)

    def to_read_model_list(self, db_models: List[T]) -> List[ReadT]:
        """Convert a list of SQLAlchemy models to Pydantic read models"""
        return [self.to_read_model(model) for model in db_models]

    # CRUD methods with schema conversions
    async def get_all(self) -> List[ReadT]:
        """Get all records as Pydantic schemas"""
        db_items = await self.dao.get_all()
        return self.to_read_model_list(db_items)

    async def get_by_id(self, item_id: int) -> Optional[ReadT]:
        """Get a record by ID as Pydantic schema"""
        db_item = await self.dao.get_by_id(item_id)
        if not db_item:
            return None
        return self.to_read_model(db_item)

    async def create(self, item_data: CreateT) -> ReadT:
        """Create a new record with validation and return as Pydantic schema"""
        # Run pre-create hook for validation
        validated_data = await self.before_create(item_data)
        
        # Convert to dictionary suitable for SQLAlchemy model
        db_dict = self.to_db_model_dict(validated_data)
        
        # Create DB model through DAO
        db_item = await self.dao.create(db_dict)
        
        # Convert back to Pydantic schema for response
        return self.to_read_model(db_item)

    async def update(self, item_id: int, item_data: UpdateT) -> Optional[ReadT]:
        """Update an existing record with validation and return as Pydantic schema"""
        # Run pre-update hook for validation
        validated_data = await self.before_update(item_id, item_data)
        
        # Convert to dictionary suitable for SQLAlchemy model
        db_dict = self.to_db_model_dict(validated_data)
        
        # Update DB model through DAO
        db_item = await self.dao.update(item_id, db_dict)
        
        if not db_item:
            return None
            
        # Convert back to Pydantic schema for response
        return self.to_read_model(db_item)

    async def delete(self, item_id: int) -> bool:
        """Delete a record"""
        return await self.dao.delete(item_id)
