# app/core/base_dao.py
"""Generic base DAO for common database operations."""

from typing import Generic, TypeVar, List, Optional, Dict, Any, Type
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func, desc
from abc import ABC
from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseDAO(Generic[ModelType], ABC):
    """Generic DAO for common database operations."""
    
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db
    
    def get_all(self, skip: int = 0, limit: int = 100, **filters) -> List[ModelType]:
        """Get all records with optional filtering."""
        query = select(self.model)
        
        # Apply filters
        if filters:
            filter_conditions = []
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    filter_conditions.append(getattr(self.model, key) == value)
            if filter_conditions:
                query = query.where(and_(*filter_conditions))
        
        query = query.offset(skip).limit(limit)
        result = self.db.execute(query)
        return list(result.scalars().all())
    
    def get_by_id(self, id: int) -> Optional[ModelType]:
        """Get record by ID."""
        return self.db.get(self.model, id)
    
    def get_by_field(self, field_name: str, value: Any) -> Optional[ModelType]:
        """Get single record by field value."""
        if not hasattr(self.model, field_name):
            return None
        
        query = select(self.model).where(getattr(self.model, field_name) == value)
        result = self.db.execute(query)
        return result.scalars().first()
    
    def get_all_by_field(self, field_name: str, value: Any) -> List[ModelType]:
        """Get all records by field value."""
        if not hasattr(self.model, field_name):
            return []
        
        query = select(self.model).where(getattr(self.model, field_name) == value)
        result = self.db.execute(query)
        return list(result.scalars().all())
    
    def create(self, **data) -> ModelType:
        """Create new record."""
        db_obj = self.model(**data)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def update(self, db_obj: ModelType, **data) -> ModelType:
        """Update existing record."""
        for field, value in data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def delete(self, id: int) -> bool:
        """Delete record by ID."""
        db_obj = self.get_by_id(id)
        if db_obj:
            self.db.delete(db_obj)
            self.db.commit()
            return True
        return False
    
    def soft_delete(self, id: int) -> bool:
        """Soft delete record (set is_active = False)."""
        db_obj = self.get_by_id(id)
        if db_obj and hasattr(db_obj, 'is_active'):
            db_obj.is_active = False
            self.db.commit()
            return True
        return False
    
    def count(self, **filters) -> int:
        """Count records with optional filtering."""
        query = select(func.count(self.model.id))
        
        if filters:
            filter_conditions = []
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    filter_conditions.append(getattr(self.model, key) == value)
            if filter_conditions:
                query = query.where(and_(*filter_conditions))
        
        result = self.db.execute(query)
        return result.scalar()
    
    def exists(self, **filters) -> bool:
        """Check if record exists with given filters."""
        return self.count(**filters) > 0


class BaseAuditDAO(BaseDAO[ModelType]):
    """Base DAO with audit trail and approval support."""
    
    def create(self, created_by: str = "system", **data) -> ModelType:
        """Create with audit info."""
        if hasattr(self.model, 'created_by'):
            data['created_by'] = created_by
        return super().create(**data)
    
    def update(self, db_obj: ModelType, updated_by: str = "system", **data) -> ModelType:
        """Update with audit info."""
        if hasattr(db_obj, 'updated_by'):
            data['updated_by'] = updated_by
        return super().update(db_obj, **data)
    
    # ===== APPROVAL METHODS =====
    
    def approve(self, id: int, approved_by: str) -> Optional[ModelType]:
        """Approve a record by setting approved_by and approval_date."""
        from datetime import datetime
        
        db_obj = self.get_by_id(id)
        if not db_obj:
            return None
        
        # Only approve if model has approval fields
        if hasattr(db_obj, 'approved_by') and hasattr(db_obj, 'approval_date'):
            db_obj.approved_by = approved_by
            db_obj.approval_date = datetime.now()
            self.db.commit()
            self.db.refresh(db_obj)
        
        return db_obj
    
    def revoke_approval(self, id: int) -> Optional[ModelType]:
        """Revoke approval by clearing approved_by and approval_date."""
        db_obj = self.get_by_id(id)
        if not db_obj:
            return None
        
        # Only revoke if model has approval fields
        if hasattr(db_obj, 'approved_by') and hasattr(db_obj, 'approval_date'):
            db_obj.approved_by = None
            db_obj.approval_date = None
            self.db.commit()
            self.db.refresh(db_obj)
        
        return db_obj
    
    def get_approved(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all approved records."""
        # Only query if model has approval fields
        if not (hasattr(self.model, 'approved_by') and hasattr(self.model, 'approval_date')):
            return self.get_all(skip=skip, limit=limit)
        
        query = select(self.model).where(
            and_(
                self.model.approved_by.isnot(None),
                self.model.approval_date.isnot(None)
            )
        ).offset(skip).limit(limit)
        
        result = self.db.execute(query)
        return list(result.scalars().all())
    
    def get_pending_approval(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all records pending approval."""
        # Only query if model has approval fields
        if not (hasattr(self.model, 'approved_by') and hasattr(self.model, 'approval_date')):
            return []
        
        query = select(self.model).where(
            and_(
                self.model.approved_by.is_(None),
                # Optionally filter by is_active if it exists
                getattr(self.model, 'is_active', True) == True
            )
        ).offset(skip).limit(limit)
        
        result = self.db.execute(query)
        return list(result.scalars().all())
    
    def get_approved_by_user(self, approved_by: str, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all records approved by a specific user."""
        # Only query if model has approval fields
        if not hasattr(self.model, 'approved_by'):
            return []
        
        query = select(self.model).where(
            self.model.approved_by == approved_by
        ).offset(skip).limit(limit)
        
        result = self.db.execute(query)
        return list(result.scalars().all())
    
    def count_by_approval_status(self) -> Dict[str, int]:
        """Get counts by approval status."""
        # Only count if model has approval fields
        if not (hasattr(self.model, 'approved_by') and hasattr(self.model, 'approval_date')):
            total = self.count()
            return {"total": total, "approved": total, "pending": 0}
        
        # Count approved
        approved_count = self.db.execute(
            select(func.count(self.model.id)).where(
                self.model.approved_by.isnot(None)
            )
        ).scalar()
        
        # Count pending (assuming is_active filter if available)
        pending_query = select(func.count(self.model.id)).where(
            self.model.approved_by.is_(None)
        )
        if hasattr(self.model, 'is_active'):
            pending_query = pending_query.where(self.model.is_active == True)
        
        pending_count = self.db.execute(pending_query).scalar()
        
        return {
            "total": approved_count + pending_count,
            "approved": approved_count,
            "pending": pending_count
        }