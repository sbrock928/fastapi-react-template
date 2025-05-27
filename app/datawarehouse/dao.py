"""Data Access Objects for the datawarehouse module (data warehouse database)."""

from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, TypeVar, Generic, Type, Dict
from app.datawarehouse.models import Deal, Tranche, TrancheHistorical, Cycle

# Type variable for generic DAO
T = TypeVar("T")


class DWDao(Generic[T]):
    """Base Data Access Object for data warehouse operations."""

    def __init__(self, dw_session: Session, model_class: Type[T]):
        self.db = dw_session
        self.model_class = model_class

    async def get_all(self) -> List[T]:
        """Get all active records"""
        stmt = select(self.model_class).where(self.model_class.is_active == True)
        stmt = self._add_default_ordering(stmt)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, record_id: int) -> Optional[T]:
        """Get a record by ID"""
        stmt = select(self.model_class).where(
            self.model_class.id == record_id, self.model_class.is_active == True
        )
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_ids(self, record_ids: List[int]) -> List[T]:
        """Get records by list of IDs"""
        stmt = select(self.model_class).where(
            self.model_class.id.in_(record_ids), self.model_class.is_active == True
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

    async def get_count(self) -> int:
        """Get total count of active records"""
        stmt = (
            select(func.count())
            .select_from(self.model_class)
            .where(self.model_class.is_active == True)
        )
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
            # Fallback to extracting cycles from TrancheHistorical table
            print(f"Warning: Could not query cycles table: {e}")

            try:
                stmt = (
                    select(TrancheHistorical.cycle_code)
                    .distinct()
                    .where(TrancheHistorical.is_active == True)
                )
                result = self.db.execute(stmt)
                cycle_codes = sorted([code for code in result.scalars().all() if code])

                return [{"code": code, "label": f"{code} ({code})"} for code in cycle_codes]
            except Exception:
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
    async def get_with_tranches(self, deal_id: int) -> Optional[Deal]:
        """Get a deal with its tranches (static data only)"""
        stmt = (
            select(Deal)
            .options(selectinload(Deal.tranches))
            .where(Deal.id == deal_id, Deal.is_active == True)
        )
        result = self.db.execute(stmt)
        deal = result.scalars().first()

        # Filter out inactive tranches
        if deal:
            deal.tranches = [t for t in deal.tranches if t.is_active]

        return deal

    async def get_by_deal_type(self, deal_type: str) -> List[Deal]:
        """Get deals by type (RMBS, CMBS, etc.)"""
        stmt = select(Deal).where(Deal.deal_type == deal_type, Deal.is_active == True)
        stmt = self._add_default_ordering(stmt)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_originator(self, originator: str) -> List[Deal]:
        """Get deals by originator"""
        stmt = select(Deal).where(Deal.originator == originator, Deal.is_active == True)
        stmt = self._add_default_ordering(stmt)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_deal_count(self) -> int:
        """Get total count of active deals (alias for get_count)"""
        return await self.get_count()


class TrancheDAO(DWDao[Tranche]):
    """DB functionality for interaction with `Tranche` objects in data warehouse."""

    def __init__(self, dw_session: Session):
        super().__init__(dw_session, Tranche)

    def _add_default_ordering(self, stmt):
        """Add default ordering for tranches"""
        return stmt.order_by(Tranche.deal_id, Tranche.payment_priority)

    # Tranche-specific methods
    async def get_by_deal_id(self, deal_id: int) -> List[Tranche]:
        """Get tranches by deal ID (static data only)"""
        stmt = select(Tranche).where(Tranche.deal_id == deal_id, Tranche.is_active == True)
        stmt = stmt.order_by(Tranche.payment_priority)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_deal_ids(self, deal_ids: List[int]) -> List[Tranche]:
        """Get tranches for multiple deals (static data only)"""
        stmt = select(Tranche).where(Tranche.deal_id.in_(deal_ids), Tranche.is_active == True)
        stmt = self._add_default_ordering(stmt)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_class_name(self, class_name: str) -> List[Tranche]:
        """Get tranches by class name (A, B, C, etc.)"""
        stmt = select(Tranche).where(Tranche.class_name == class_name, Tranche.is_active == True)
        stmt = self._add_default_ordering(stmt)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_tranche_count(self) -> int:
        """Get total count of active tranches (alias for get_count)"""
        return await self.get_count()

    async def get_with_historical_data(self, tranche_id: int) -> Optional[Tranche]:
        """Get a tranche with its historical data"""
        stmt = (
            select(Tranche)
            .options(selectinload(Tranche.historical_data))
            .where(Tranche.id == tranche_id, Tranche.is_active == True)
        )
        result = self.db.execute(stmt)
        tranche = result.scalars().first()

        # Filter out inactive historical records
        if tranche:
            tranche.historical_data = [h for h in tranche.historical_data if h.is_active]

        return tranche


class TrancheHistoricalDAO(DWDao[TrancheHistorical]):
    """DB functionality for interaction with `TrancheHistorical` objects in data warehouse."""

    def __init__(self, dw_session: Session):
        super().__init__(dw_session, TrancheHistorical)

    def _add_default_ordering(self, stmt):
        """Add default ordering for tranche historical records"""
        return stmt.order_by(TrancheHistorical.tranche_id, TrancheHistorical.cycle_code)

    # TrancheHistorical-specific methods
    async def get_by_cycle_code(self, cycle_code: str) -> List[TrancheHistorical]:
        """Get all tranche historical records for a specific cycle"""
        stmt = select(TrancheHistorical).where(
            TrancheHistorical.cycle_code == cycle_code, TrancheHistorical.is_active == True
        )
        stmt = self._add_default_ordering(stmt)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_tranche_id(
        self, tranche_id: int, cycle_code: Optional[str] = None
    ) -> List[TrancheHistorical]:
        """Get historical records for a specific tranche, optionally filtered by cycle"""
        stmt = select(TrancheHistorical).where(
            TrancheHistorical.tranche_id == tranche_id, TrancheHistorical.is_active == True
        )
        if cycle_code:
            stmt = stmt.where(TrancheHistorical.cycle_code == cycle_code)
        stmt = stmt.order_by(TrancheHistorical.cycle_code)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_tranche_and_cycle(
        self, tranche_id: int, cycle_code: str
    ) -> Optional[TrancheHistorical]:
        """Get a specific tranche historical record by tranche ID and cycle code"""
        stmt = select(TrancheHistorical).where(
            TrancheHistorical.tranche_id == tranche_id,
            TrancheHistorical.cycle_code == cycle_code,
            TrancheHistorical.is_active == True,
        )
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_tranche_ids_and_cycle(
        self, tranche_ids: List[int], cycle_code: str
    ) -> List[TrancheHistorical]:
        """Get historical records for multiple tranches in a specific cycle"""
        stmt = select(TrancheHistorical).where(
            TrancheHistorical.tranche_id.in_(tranche_ids),
            TrancheHistorical.cycle_code == cycle_code,
            TrancheHistorical.is_active == True,
        )
        stmt = self._add_default_ordering(stmt)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_deal_ids_and_cycle(
        self, deal_ids: List[int], cycle_code: str
    ) -> List[TrancheHistorical]:
        """Get historical records for all tranches in specific deals for a cycle"""
        # First get tranche IDs for the deals
        tranche_stmt = select(Tranche.id).where(
            Tranche.deal_id.in_(deal_ids), Tranche.is_active == True
        )
        tranche_result = self.db.execute(tranche_stmt)
        tranche_ids = [row[0] for row in tranche_result.fetchall()]

        if not tranche_ids:
            return []

        # Then get historical records for those tranches
        return await self.get_by_tranche_ids_and_cycle(tranche_ids, cycle_code)

    async def get_latest_by_tranche_id(self, tranche_id: int) -> Optional[TrancheHistorical]:
        """Get the most recent historical record for a tranche"""
        stmt = (
            select(TrancheHistorical)
            .where(TrancheHistorical.tranche_id == tranche_id, TrancheHistorical.is_active == True)
            .order_by(TrancheHistorical.cycle_code.desc())
        )
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def get_cycles_for_tranche(self, tranche_id: int) -> List[str]:
        """Get all cycle codes that have data for a specific tranche"""
        stmt = (
            select(TrancheHistorical.cycle_code)
            .where(TrancheHistorical.tranche_id == tranche_id, TrancheHistorical.is_active == True)
            .distinct()
            .order_by(TrancheHistorical.cycle_code)
        )
        result = self.db.execute(stmt)
        return [row[0] for row in result.fetchall()]
