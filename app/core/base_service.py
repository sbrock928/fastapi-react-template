# app/core/base_service.py
"""Generic base service for business logic orchestration."""

from typing import Generic, TypeVar, List, Optional, Dict, Any, Type
from pydantic import BaseModel
from abc import ABC
from app.core.base_dao import BaseDAO, BaseAuditDAO

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
ResponseSchemaType = TypeVar("ResponseSchemaType", bound=BaseModel)


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType], ABC):
    """Generic service for business logic orchestration."""
    
    def __init__(self, dao: BaseDAO[ModelType]):
        self.dao = dao
    
    def get_all(self, skip: int = 0, limit: int = 100, **filters) -> List[ResponseSchemaType]:
        """Get all records with business logic applied."""
        records = self.dao.get_all(skip=skip, limit=limit, **filters)
        return [self._to_response(record) for record in records]
    
    def get_by_id(self, id: int) -> Optional[ResponseSchemaType]:
        """Get record by ID with business logic applied."""
        record = self.dao.get_by_id(id)
        if record:
            return self._to_response(record)
        return None
    
    def create(self, create_data: CreateSchemaType, **extra_data) -> ResponseSchemaType:
        """Create new record with validation and business logic."""
        # Pre-creation validation
        self._validate_create(create_data)
        
        # Convert schema to dict
        data = create_data.model_dump() if hasattr(create_data, 'model_dump') else create_data.dict()
        data.update(extra_data)
        
        # Create record
        record = self.dao.create(**data)
        
        # Post-creation business logic
        self._post_create(record, create_data)
        
        return self._to_response(record)
    
    def update(self, id: int, update_data: UpdateSchemaType, **extra_data) -> Optional[ResponseSchemaType]:
        """Update existing record with validation and business logic."""
        # Get existing record
        record = self.dao.get_by_id(id)
        if not record:
            return None
        
        # Pre-update validation
        self._validate_update(record, update_data)
        
        # Convert schema to dict, excluding unset values
        data = update_data.model_dump(exclude_unset=True) if hasattr(update_data, 'model_dump') else update_data.dict(exclude_unset=True)
        data.update(extra_data)
        
        # Update record
        updated_record = self.dao.update(record, **data)
        
        # Post-update business logic
        self._post_update(updated_record, update_data)
        
        return self._to_response(updated_record)
    
    def delete(self, id: int) -> bool:
        """Delete record with business logic."""
        # Pre-deletion validation
        record = self.dao.get_by_id(id)
        if not record:
            return False
        
        self._validate_delete(record)
        
        # Perform deletion
        success = self.dao.delete(id)
        
        if success:
            self._post_delete(record)
        
        return success
    
    def soft_delete(self, id: int) -> bool:
        """Soft delete record with business logic."""
        # Pre-deletion validation
        record = self.dao.get_by_id(id)
        if not record:
            return False
        
        self._validate_delete(record)
        
        # Perform soft deletion
        success = self.dao.soft_delete(id)
        
        if success:
            self._post_delete(record)
        
        return success
    
    def count(self, **filters) -> int:
        """Count records with filters."""
        return self.dao.count(**filters)
    
    def exists(self, **filters) -> bool:
        """Check if record exists."""
        return self.dao.exists(**filters)
    
    # ===== ABSTRACT METHODS (OVERRIDE IN SUBCLASSES) =====
    
    def _to_response(self, record: ModelType) -> ResponseSchemaType:
        """Convert database model to response schema."""
        # Default implementation - override for complex transformations
        if hasattr(self, 'response_model'):
            return self.response_model.model_validate(record)
        raise NotImplementedError("Must implement _to_response or set response_model")
    
    def _validate_create(self, create_data: CreateSchemaType) -> None:
        """Validate data before creation. Override for custom validation."""
        pass
    
    def _validate_update(self, record: ModelType, update_data: UpdateSchemaType) -> None:
        """Validate data before update. Override for custom validation."""
        pass
    
    def _validate_delete(self, record: ModelType) -> None:
        """Validate before deletion. Override for custom validation."""
        pass
    
    def _post_create(self, record: ModelType, create_data: CreateSchemaType) -> None:
        """Business logic after creation. Override for side effects."""
        pass
    
    def _post_update(self, record: ModelType, update_data: UpdateSchemaType) -> None:
        """Business logic after update. Override for side effects."""
        pass
    
    def _post_delete(self, record: ModelType) -> None:
        """Business logic after deletion. Override for side effects."""
        pass


class BaseAuditService(BaseService[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType]):
    """Base service with audit trail and approval support."""
    
    def __init__(self, dao: BaseAuditDAO[ModelType]):
        super().__init__(dao)
        self.audit_dao = dao  # Type hint for audit methods
    
    def create(self, create_data: CreateSchemaType, created_by: str = "api_user", **extra_data) -> ResponseSchemaType:
        """Create new record with audit info."""
        # Pre-creation validation
        self._validate_create(create_data)
        
        # Convert schema to dict
        data = create_data.model_dump() if hasattr(create_data, 'model_dump') else create_data.dict()
        data.update(extra_data)
        
        # Create record with audit info
        record = self.audit_dao.create(created_by=created_by, **data)
        
        # Post-creation business logic
        self._post_create(record, create_data)
        
        return self._to_response(record)
    
    def update(self, id: int, update_data: UpdateSchemaType, updated_by: str = "api_user", **extra_data) -> Optional[ResponseSchemaType]:
        """Update existing record with audit info."""
        # Get existing record
        record = self.audit_dao.get_by_id(id)
        if not record:
            return None
        
        # Pre-update validation
        self._validate_update(record, update_data)
        
        # Convert schema to dict, excluding unset values
        data = update_data.model_dump(exclude_unset=True) if hasattr(update_data, 'model_dump') else update_data.dict(exclude_unset=True)
        data.update(extra_data)
        
        # Update record with audit info
        updated_record = self.audit_dao.update(record, updated_by=updated_by, **data)
        
        # Post-update business logic
        self._post_update(updated_record, update_data)
        
        return self._to_response(updated_record)
    
    # ===== APPROVAL METHODS =====
    
    def approve(self, id: int, approved_by: str) -> Optional[ResponseSchemaType]:
        """Approve a record with business validation."""
        # Get existing record
        record = self.audit_dao.get_by_id(id)
        if not record:
            return None
        
        # Pre-approval validation
        self._validate_approval(record, approved_by)
        
        # Approve using DAO
        approved_record = self.audit_dao.approve(id, approved_by)
        
        if approved_record:
            # Post-approval business logic
            self._post_approval(approved_record, approved_by)
            return self._to_response(approved_record)
        
        return None
    
    def revoke_approval(self, id: int, revoked_by: str = "api_user") -> Optional[ResponseSchemaType]:
        """Revoke approval with business validation."""
        # Get existing record
        record = self.audit_dao.get_by_id(id)
        if not record:
            return None
        
        # Pre-revocation validation
        self._validate_revocation(record, revoked_by)
        
        # Revoke using DAO
        revoked_record = self.audit_dao.revoke_approval(id)
        
        if revoked_record:
            # Post-revocation business logic
            self._post_revocation(revoked_record, revoked_by)
            return self._to_response(revoked_record)
        
        return None
    
    def get_approved(self, skip: int = 0, limit: int = 100) -> List[ResponseSchemaType]:
        """Get all approved records."""
        records = self.audit_dao.get_approved(skip=skip, limit=limit)
        return [self._to_response(record) for record in records]
    
    def get_pending_approval(self, skip: int = 0, limit: int = 100) -> List[ResponseSchemaType]:
        """Get all records pending approval."""
        records = self.audit_dao.get_pending_approval(skip=skip, limit=limit)
        return [self._to_response(record) for record in records]
    
    def get_approved_by_user(self, approved_by: str, skip: int = 0, limit: int = 100) -> List[ResponseSchemaType]:
        """Get all records approved by a specific user."""
        records = self.audit_dao.get_approved_by_user(approved_by, skip=skip, limit=limit)
        return [self._to_response(record) for record in records]
    
    def get_approval_stats(self) -> Dict[str, int]:
        """Get approval statistics."""
        return self.audit_dao.count_by_approval_status()
    
    # ===== APPROVAL VALIDATION HOOKS (OVERRIDE IN SUBCLASSES) =====
    
    def _validate_approval(self, record: ModelType, approved_by: str) -> None:
        """Validate approval request. Override for custom business rules."""
        pass
    
    def _validate_revocation(self, record: ModelType, revoked_by: str) -> None:
        """Validate revocation request. Override for custom business rules."""
        pass
    
    def _post_approval(self, record: ModelType, approved_by: str) -> None:
        """Business logic after approval. Override for side effects."""
        pass
    
    def _post_revocation(self, record: ModelType, revoked_by: str) -> None:
        """Business logic after revocation. Override for side effects."""
        pass


class SimpleService(BaseService[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType]):
    """Simple service for basic CRUD with minimal setup."""
    
    def __init__(self, dao: BaseDAO[ModelType], response_model: Type[ResponseSchemaType]):
        super().__init__(dao)
        self.response_model = response_model