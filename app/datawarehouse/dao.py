"""Data Access Objects for the datawarehouse module (data warehouse database)."""

from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import List, Optional, Dict
from app.datawarehouse.models import Deal, Tranche, TrancheHistorical, Cycle


class DWDao:
    """Unified Data Access Object for all data warehouse operations."""

    def __init__(self, dw_session: Session):
        self.db = dw_session

    # ===== DEAL METHODS =====

    async def get_all_deals(self) -> List[Deal]:
        """Get all active deals"""
        stmt = select(Deal).where(Deal.is_active == True).order_by(Deal.name)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_deal_by_id(self, deal_id: int) -> Optional[Deal]:
        """Get a deal by ID"""
        stmt = select(Deal).where(Deal.id == deal_id, Deal.is_active == True)
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def get_deals_by_ids(self, deal_ids: List[int]) -> List[Deal]:
        """Get deals by list of IDs"""
        stmt = select(Deal).where(Deal.id.in_(deal_ids), Deal.is_active == True).order_by(Deal.name)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    # ===== TRANCHE METHODS =====

    async def get_tranches_by_ids(self, tranche_ids: List[int]) -> List[Tranche]:
        """Get tranches by list of IDs"""
        stmt = select(Tranche).where(Tranche.id.in_(tranche_ids), Tranche.is_active == True).order_by(Tranche.deal_id, Tranche.payment_priority)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_tranches_by_deal_id(self, deal_id: int) -> List[Tranche]:
        """Get tranches by deal ID (static data only)"""
        stmt = select(Tranche).where(Tranche.deal_id == deal_id, Tranche.is_active == True).order_by(Tranche.payment_priority)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    # ===== TRANCHE HISTORICAL METHODS =====

    async def get_historical_by_tranche_and_cycle(
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

    async def get_historical_by_tranche_ids_and_cycle(
        self, tranche_ids: List[int], cycle_code: str
    ) -> List[TrancheHistorical]:
        """Get historical records for multiple tranches in a specific cycle"""
        stmt = select(TrancheHistorical).where(
            TrancheHistorical.tranche_id.in_(tranche_ids),
            TrancheHistorical.cycle_code == cycle_code,
            TrancheHistorical.is_active == True,
        ).order_by(TrancheHistorical.tranche_id, TrancheHistorical.cycle_code)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_historical_by_tranche_id(self, tranche_id: int) -> Optional[TrancheHistorical]:
        """Get the most recent historical record for a tranche"""
        stmt = (
            select(TrancheHistorical)
            .where(TrancheHistorical.tranche_id == tranche_id, TrancheHistorical.is_active == True)
            .order_by(TrancheHistorical.cycle_code.desc())
        )
        result = self.db.execute(stmt)
        return result.scalars().first()

    # ===== CYCLE METHODS =====

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
