"""Data Access Objects for the datawarehouse module (data warehouse database)."""

from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.datawarehouse.models import Deal, Tranche


class DealDAO:
    """DB functionality for interaction with `Deal` objects in data warehouse."""

    def __init__(self, dw_session: Session):
        self.db = dw_session

    async def get_all(self, cycle_code: Optional[str] = None) -> List[Deal]:
        """Get all deals, optionally filtered by cycle"""
        stmt = select(Deal).where(Deal.is_active == True)
        if cycle_code:
            stmt = stmt.where(Deal.cycle_code == cycle_code)
        stmt = stmt.order_by(Deal.name)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, deal_id: int) -> Optional[Deal]:
        """Get a deal by ID"""
        stmt = select(Deal).where(Deal.id == deal_id, Deal.is_active == True)
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_id_and_cycle(self, deal_id: int, cycle_code: str) -> Optional[Deal]:
        """Get a deal by ID and cycle code"""
        stmt = select(Deal).where(
            Deal.id == deal_id,
            Deal.cycle_code == cycle_code,
            Deal.is_active == True
        )
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_ids(self, deal_ids: List[int], cycle_code: Optional[str] = None) -> List[Deal]:
        """Get deals by list of IDs"""
        stmt = select(Deal).where(
            Deal.id.in_(deal_ids),
            Deal.is_active == True
        )
        if cycle_code:
            stmt = stmt.where(Deal.cycle_code == cycle_code)
        stmt = stmt.order_by(Deal.name)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_with_tranches(self, deal_id: int, cycle_code: Optional[str] = None) -> Optional[Deal]:
        """Get a deal with its tranches"""
        stmt = select(Deal).options(selectinload(Deal.tranches)).where(
            Deal.id == deal_id,
            Deal.is_active == True
        )
        if cycle_code:
            stmt = stmt.where(Deal.cycle_code == cycle_code)
        result = self.db.execute(stmt)
        deal = result.scalars().first()
        
        # Filter tranches by cycle if needed
        if deal and cycle_code:
            deal.tranches = [t for t in deal.tranches if t.cycle_code == cycle_code and t.is_active]
        
        return deal

    async def get_by_cycle_code(self, cycle_code: str) -> List[Deal]:
        """Get all active deals for a specific cycle"""
        stmt = select(Deal).where(
            Deal.cycle_code == cycle_code,
            Deal.is_active == True
        ).order_by(Deal.name)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_deal_type(self, deal_type: str, cycle_code: Optional[str] = None) -> List[Deal]:
        """Get deals by type (RMBS, CMBS, etc.)"""
        stmt = select(Deal).where(
            Deal.deal_type == deal_type,
            Deal.is_active == True
        )
        if cycle_code:
            stmt = stmt.where(Deal.cycle_code == cycle_code)
        stmt = stmt.order_by(Deal.name)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_originator(self, originator: str, cycle_code: Optional[str] = None) -> List[Deal]:
        """Get deals by originator"""
        stmt = select(Deal).where(
            Deal.originator == originator,
            Deal.is_active == True
        )
        if cycle_code:
            stmt = stmt.where(Deal.cycle_code == cycle_code)
        stmt = stmt.order_by(Deal.name)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, deal_obj: Deal) -> Deal:
        """Create a new deal"""
        self.db.add(deal_obj)
        self.db.commit()
        self.db.refresh(deal_obj)
        return deal_obj

    async def update(self, deal_obj: Deal) -> Deal:
        """Update an existing deal"""
        self.db.add(deal_obj)
        self.db.commit()
        self.db.refresh(deal_obj)
        return deal_obj

    async def delete(self, deal_id: int) -> bool:
        """Soft delete a deal by ID"""
        deal = await self.get_by_id(deal_id)
        if deal:
            deal.is_active = False
            await self.update(deal)
            return True
        return False

    async def get_deal_count(self, cycle_code: Optional[str] = None) -> int:
        """Get total count of active deals"""
        stmt = select(func.count()).select_from(Deal).where(Deal.is_active == True)
        if cycle_code:
            stmt = stmt.where(Deal.cycle_code == cycle_code)
        result = self.db.execute(stmt)
        return int(result.scalar_one() or 0)


class TrancheDAO:
    """DB functionality for interaction with `Tranche` objects in data warehouse."""

    def __init__(self, dw_session: Session):
        self.db = dw_session

    async def get_all(self, cycle_code: Optional[str] = None) -> List[Tranche]:
        """Get all tranches, optionally filtered by cycle"""
        stmt = select(Tranche).where(Tranche.is_active == True)
        if cycle_code:
            stmt = stmt.where(Tranche.cycle_code == cycle_code)
        stmt = stmt.order_by(Tranche.deal_id, Tranche.payment_priority)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, tranche_id: int) -> Optional[Tranche]:
        """Get a tranche by ID"""
        stmt = select(Tranche).where(Tranche.id == tranche_id, Tranche.is_active == True)
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_id_and_cycle(self, tranche_id: int, cycle_code: str) -> Optional[Tranche]:
        """Get a tranche by ID and cycle code"""
        stmt = select(Tranche).where(
            Tranche.id == tranche_id,
            Tranche.cycle_code == cycle_code,
            Tranche.is_active == True
        )
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_ids(self, tranche_ids: List[int], cycle_code: Optional[str] = None) -> List[Tranche]:
        """Get tranches by list of IDs"""
        stmt = select(Tranche).where(
            Tranche.id.in_(tranche_ids),
            Tranche.is_active == True
        )
        if cycle_code:
            stmt = stmt.where(Tranche.cycle_code == cycle_code)
        stmt = stmt.order_by(Tranche.deal_id, Tranche.payment_priority)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_deal_id(self, deal_id: int, cycle_code: Optional[str] = None) -> List[Tranche]:
        """Get tranches by deal ID"""
        stmt = select(Tranche).where(
            Tranche.deal_id == deal_id,
            Tranche.is_active == True
        )
        if cycle_code:
            stmt = stmt.where(Tranche.cycle_code == cycle_code)
        stmt = stmt.order_by(Tranche.payment_priority)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_deal_ids(self, deal_ids: List[int], cycle_code: Optional[str] = None) -> List[Tranche]:
        """Get tranches for multiple deals"""
        stmt = select(Tranche).where(
            Tranche.deal_id.in_(deal_ids),
            Tranche.is_active == True
        )
        if cycle_code:
            stmt = stmt.where(Tranche.cycle_code == cycle_code)
        stmt = stmt.order_by(Tranche.deal_id, Tranche.payment_priority)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_class_name(self, class_name: str, cycle_code: Optional[str] = None) -> List[Tranche]:
        """Get tranches by class name (A, B, C, etc.)"""
        stmt = select(Tranche).where(
            Tranche.class_name == class_name,
            Tranche.is_active == True
        )
        if cycle_code:
            stmt = stmt.where(Tranche.cycle_code == cycle_code)
        stmt = stmt.order_by(Tranche.deal_id, Tranche.payment_priority)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, tranche_obj: Tranche) -> Tranche:
        """Create a new tranche"""
        self.db.add(tranche_obj)
        self.db.commit()
        self.db.refresh(tranche_obj)
        return tranche_obj

    async def update(self, tranche_obj: Tranche) -> Tranche:
        """Update an existing tranche"""
        self.db.add(tranche_obj)
        self.db.commit()
        self.db.refresh(tranche_obj)
        return tranche_obj

    async def delete(self, tranche_id: int) -> bool:
        """Soft delete a tranche by ID"""
        tranche = await self.get_by_id(tranche_id)
        if tranche:
            tranche.is_active = False
            await self.update(tranche)
            return True
        return False

    async def get_tranche_count(self, cycle_code: Optional[str] = None) -> int:
        """Get total count of active tranches"""
        stmt = select(func.count()).select_from(Tranche).where(Tranche.is_active == True)
        if cycle_code:
            stmt = stmt.where(Tranche.cycle_code == cycle_code)
        result = self.db.execute(stmt)
        return int(result.scalar_one() or 0)