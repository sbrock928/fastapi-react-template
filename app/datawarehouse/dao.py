"""Data Access Objects for the datawarehouse module (data warehouse database)."""

from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional, Dict, Any
from app.datawarehouse.models import Deal, Tranche, TrancheBal


class DatawarehouseDAO:
    """DAO for the new data warehouse schema."""

    def __init__(self, dw_session: Session):
        self.db = dw_session

    # ===== DEAL METHODS =====

    def get_all_deals(self) -> List[Deal]:
        """Get all deals"""
        stmt = select(Deal).order_by(Deal.dl_nbr)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    def get_deal_by_dl_nbr(self, dl_nbr: int) -> Optional[Deal]:
        """Get a deal by DL number"""
        stmt = select(Deal).where(Deal.dl_nbr == dl_nbr)
        result = self.db.execute(stmt)
        return result.scalars().first()

    # ===== TRANCHE METHODS =====

    def get_tranches_by_dl_nbr(self, dl_nbr: int) -> List[Tranche]:
        """Get tranches by DL number"""
        stmt = select(Tranche).where(Tranche.dl_nbr == dl_nbr).order_by(Tranche.tr_id)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    def get_tranche_by_keys(self, dl_nbr: int, tr_id: str) -> Optional[Tranche]:
        """Get a tranche by DL number and tranche ID"""
        stmt = select(Tranche).where(Tranche.dl_nbr == dl_nbr, Tranche.tr_id == tr_id)
        result = self.db.execute(stmt)
        return result.scalars().first()

    # ===== TRANCHE CYCLE DATA METHODS =====

    def get_tranchebals_by_tranche(self, dl_nbr: int, tr_id: str) -> List[TrancheBal]:
        """Get tranche cycle data by tranche DL number and tranche ID"""
        stmt = select(TrancheBal).where(TrancheBal.dl_nbr == dl_nbr, TrancheBal.tr_id == tr_id)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    def get_tranchebal_by_keys(self, dl_nbr: int, tr_id: str, cycle_date: Optional[int] = None) -> Optional[TrancheBal]:
        """Get tranche cycle data by DL number, tranche ID, and optionally cycle date"""
        if cycle_date:
            stmt = select(TrancheBal).where(
                TrancheBal.dl_nbr == dl_nbr, 
                TrancheBal.tr_id == tr_id,
                TrancheBal.cycle_date == cycle_date
            )
        else:
            # Get the most recent cycle data if no cycle date specified
            stmt = select(TrancheBal).where(
                TrancheBal.dl_nbr == dl_nbr, 
                TrancheBal.tr_id == tr_id
            ).order_by(TrancheBal.cycle_date.desc()).limit(1)
        
        result = self.db.execute(stmt)
        return result.scalars().first()

    def get_available_cycles(self) -> List[Dict[str, Any]]:

        """Get available cycle codes from the data warehouse.
        
        Returns dummy cycle data for now since cycle functionality is not yet implemented.
        """
        # Return dummy cycle data
        return [
            {"label": "2024 Q1", "value": 20241},
            {"label": "2024 Q2", "value": 20242},
            {"label": "2024 Q3", "value": 20243},
            {"label": "2024 Q4", "value": 20244},
            {"label": "2025 Q1", "value": 20251},
        ]
