"""Data Access Objects for the datawarehouse module (data warehouse database)."""

from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, TypeVar, Generic, Type, Dict
from app.datawarehouse.models import Deal, Tranche, Cycle

# Type variable for generic DAO
T = TypeVar('T')


class DWDao(Generic[T]):
    """Base Data Access Object for data warehouse operations."""

    def __init__(self, dw_session: Session, model_class: Type[T]):
        self.db = dw_session
        self.model_class = model_class

    async def get_all(self, cycle_code: Optional[str] = None) -> List[T]:
        """Get all records, optionally filtered by cycle"""
        stmt = select(self.model_class).where(self.model_class.is_active == True)
        if cycle_code:
            stmt = stmt.where(self.model_class.cycle_code == cycle_code)
        stmt = self._add_default_ordering(stmt)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, record_id: int) -> Optional[T]:
        """Get a record by ID"""
        stmt = select(self.model_class).where(
            self.model_class.id == record_id, 
            self.model_class.is_active == True
        )
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_id_and_cycle(self, record_id: int, cycle_code: str) -> Optional[T]:
        """Get a record by ID and cycle code"""
        stmt = select(self.model_class).where(
            self.model_class.id == record_id, 
            self.model_class.cycle_code == cycle_code, 
            self.model_class.is_active == True
        )
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_ids(self, record_ids: List[int], cycle_code: Optional[str] = None) -> List[T]:
        """Get records by list of IDs"""
        stmt = select(self.model_class).where(
            self.model_class.id.in_(record_ids), 
            self.model_class.is_active == True
        )
        if cycle_code:
            stmt = stmt.where(self.model_class.cycle_code == cycle_code)
        stmt = self._add_default_ordering(stmt)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_cycle_code(self, cycle_code: str) -> List[T]:
        """Get all active records for a specific cycle"""
        stmt = select(self.model_class).where(
            self.model_class.cycle_code == cycle_code, 
            self.model_class.is_active == True
        )
        stmt = self._add_default_ordering(stmt)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, record_obj: T) -> T:
        """Create a new record"""
        self.db.add(record_obj)
        self.db.commit()
        self.db.refresh(record_obj)
        return record_obj

    async def update(self, record_obj: T) -> T:
        """Update an existing record"""
        self.db.add(record_obj)
        self.db.commit()
        self.db.refresh(record_obj)
        return record_obj

    async def delete(self, record_id: int) -> bool:
        """Soft delete a record by ID"""
        record = await self.get_by_id(record_id)
        if record:
            record.is_active = False
            await self.update(record)
            return True
        return False

    async def get_count(self, cycle_code: Optional[str] = None) -> int:
        """Get total count of active records"""
        stmt = select(func.count()).select_from(self.model_class).where(self.model_class.is_active == True)
        if cycle_code:
            stmt = stmt.where(self.model_class.cycle_code == cycle_code)
        result = self.db.execute(stmt)
        return int(result.scalar_one() or 0)

    async def get_available_cycles(self) -> List[Dict[str, str]]:
        """Get available cycles from the cycles table.
        
        This is a cross-cutting method available to all DAO instances since 
        cycles are used throughout the data warehouse.
        """
        try:
            # Query the cycles table directly
            stmt = select(Cycle).order_by(Cycle.code)
            result = self.db.execute(stmt)
            cycles = list(result.scalars().all())
            
            # Format as expected by frontend
            return [
                {"code": cycle.code, "label": f"{cycle.code} ({cycle.description or cycle.code})"}
                for cycle in cycles
            ]
            
        except Exception as e:
            # Fallback to extracting cycles from current model if cycles table unavailable
            print(f"Warning: Could not query cycles table: {e}")
            
            # If current model has cycle_code field, extract unique codes
            if hasattr(self.model_class, 'cycle_code'):
                stmt = select(self.model_class.cycle_code).distinct()
                if hasattr(self.model_class, 'is_active'):
                    stmt = stmt.where(self.model_class.is_active == True)
                result = self.db.execute(stmt)
                cycle_codes = sorted([code for code in result.scalars().all() if code])
                
                return [
                    {"code": code, "label": f"{code} ({code})"}
                    for code in cycle_codes
                ]
            
            # Final fallback
            return []

    async def get_cycle_by_code(self, code: str) -> Optional[Cycle]:
        """Get a specific cycle by its code.
        
        Cross-cutting method available to all DAO instances.
        """
        try:
            stmt = select(Cycle).where(Cycle.code == code)
            result = self.db.execute(stmt)
            return result.scalars().first()
        except Exception:
            return None

    def _add_default_ordering(self, stmt):
        """Add default ordering to statement - to be overridden by subclasses"""
        return stmt


class DealDAO(DWDao[Deal]):
    """DB functionality for interaction with `Deal` objects in data warehouse."""

    def __init__(self, dw_session: Session):
        super().__init__(dw_session, Deal)

    def _add_default_ordering(self, stmt):
        """Add default ordering for deals"""
        return stmt.order_by(Deal.name)

    # Deal-specific methods
    async def get_with_tranches(
        self, deal_id: int, cycle_code: Optional[str] = None
    ) -> Optional[Deal]:
        """Get a deal with its tranches"""
        stmt = (
            select(Deal)
            .options(selectinload(Deal.tranches))
            .where(Deal.id == deal_id, Deal.is_active == True)
        )
        if cycle_code:
            stmt = stmt.where(Deal.cycle_code == cycle_code)
        result = self.db.execute(stmt)
        deal = result.scalars().first()

        # Filter tranches by cycle if needed
        if deal and cycle_code:
            deal.tranches = [t for t in deal.tranches if t.cycle_code == cycle_code and t.is_active]

        return deal

    async def get_by_deal_type(
        self, deal_type: str, cycle_code: Optional[str] = None
    ) -> List[Deal]:
        """Get deals by type (RMBS, CMBS, etc.)"""
        stmt = select(Deal).where(Deal.deal_type == deal_type, Deal.is_active == True)
        if cycle_code:
            stmt = stmt.where(Deal.cycle_code == cycle_code)
        stmt = self._add_default_ordering(stmt)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_originator(
        self, originator: str, cycle_code: Optional[str] = None
    ) -> List[Deal]:
        """Get deals by originator"""
        stmt = select(Deal).where(Deal.originator == originator, Deal.is_active == True)
        if cycle_code:
            stmt = stmt.where(Deal.cycle_code == cycle_code)
        stmt = self._add_default_ordering(stmt)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_deal_count(self, cycle_code: Optional[str] = None) -> int:
        """Get total count of active deals (alias for get_count)"""
        return await self.get_count(cycle_code)


class TrancheDAO(DWDao[Tranche]):
    """DB functionality for interaction with `Tranche` objects in data warehouse."""

    def __init__(self, dw_session: Session):
        super().__init__(dw_session, Tranche)

    def _add_default_ordering(self, stmt):
        """Add default ordering for tranches"""
        return stmt.order_by(Tranche.deal_id, Tranche.payment_priority)

    # Tranche-specific methods
    async def get_by_deal_id(self, deal_id: int, cycle_code: Optional[str] = None) -> List[Tranche]:
        """Get tranches by deal ID"""
        stmt = select(Tranche).where(Tranche.deal_id == deal_id, Tranche.is_active == True)
        if cycle_code:
            stmt = stmt.where(Tranche.cycle_code == cycle_code)
        stmt = stmt.order_by(Tranche.payment_priority)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_deal_ids(
        self, deal_ids: List[int], cycle_code: Optional[str] = None
    ) -> List[Tranche]:
        """Get tranches for multiple deals"""
        stmt = select(Tranche).where(Tranche.deal_id.in_(deal_ids), Tranche.is_active == True)
        if cycle_code:
            stmt = stmt.where(Tranche.cycle_code == cycle_code)
        stmt = self._add_default_ordering(stmt)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_class_name(
        self, class_name: str, cycle_code: Optional[str] = None
    ) -> List[Tranche]:
        """Get tranches by class name (A, B, C, etc.)"""
        stmt = select(Tranche).where(Tranche.class_name == class_name, Tranche.is_active == True)
        if cycle_code:
            stmt = stmt.where(Tranche.cycle_code == cycle_code)
        stmt = self._add_default_ordering(stmt)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_tranche_count(self, cycle_code: Optional[str] = None) -> int:
        """Get total count of active tranches (alias for get_count)"""
        return await self.get_count(cycle_code)
