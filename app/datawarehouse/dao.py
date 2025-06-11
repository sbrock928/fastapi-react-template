# app/datawarehouse/dao.py
"""Refactored Data Access Objects for the datawarehouse module using BaseDAO."""

from sqlalchemy.orm import Session
from sqlalchemy import select, distinct
from typing import List, Optional, Dict, Any
from app.core.base_dao import BaseDAO
from app.datawarehouse.models import Deal, Tranche, TrancheBal


class DealDAO(BaseDAO[Deal]):
    """DAO for Deal operations using BaseDAO."""

    def __init__(self, dw_session: Session):
        super().__init__(Deal, dw_session)

    def get_by_dl_nbr(self, dl_nbr: int) -> Optional[Deal]:
        """Get a deal by DL number - specialized method."""
        return self.get_by_field("dl_nbr", dl_nbr)

    def get_by_cusip(self, deal_cusip_id: str) -> Optional[Deal]:
        """Get a deal by CUSIP ID - specialized method."""
        return self.get_by_field("deal_cusip_id", deal_cusip_id)

    def get_deals_by_issuer(self, issr_cde: str) -> List[Deal]:
        """Get deals by issuer code - specialized method."""
        return self.get_all_by_field("issr_cde", issr_cde)

    def get_all_ordered(self) -> List[Deal]:
        """Get all deals ordered by dl_nbr - specialized method."""
        query = select(self.model).order_by(self.model.dl_nbr)
        result = self.db.execute(query)
        return list(result.scalars().all())


class TrancheDAO(BaseDAO[Tranche]):
    """DAO for Tranche operations using BaseDAO."""

    def __init__(self, dw_session: Session):
        super().__init__(Tranche, dw_session)

    def get_by_composite_key(self, dl_nbr: int, tr_id: str) -> Optional[Tranche]:
        """Get a tranche by composite key (dl_nbr, tr_id) - specialized method."""
        query = select(self.model).where(
            self.model.dl_nbr == dl_nbr,
            self.model.tr_id == tr_id
        )
        result = self.db.execute(query)
        return result.scalars().first()

    def get_by_cusip(self, tr_cusip_id: str) -> Optional[Tranche]:
        """Get a tranche by CUSIP ID - specialized method."""
        return self.get_by_field("tr_cusip_id", tr_cusip_id)

    def get_tranches_by_deal(self, dl_nbr: int) -> List[Tranche]:
        """Get tranches by deal number - specialized method."""
        query = select(self.model).where(
            self.model.dl_nbr == dl_nbr
        ).order_by(self.model.tr_id)
        result = self.db.execute(query)
        return list(result.scalars().all())


class TrancheBalDAO(BaseDAO[TrancheBal]):
    """DAO for TrancheBal operations using BaseDAO."""

    def __init__(self, dw_session: Session):
        super().__init__(TrancheBal, dw_session)

    def get_by_composite_key(self, dl_nbr: int, tr_id: str, cycle_cde: int) -> Optional[TrancheBal]:
        """Get a tranche balance by composite key - specialized method."""
        query = select(self.model).where(
            self.model.dl_nbr == dl_nbr,
            self.model.tr_id == tr_id,
            self.model.cycle_cde == cycle_cde
        )
        result = self.db.execute(query)
        return result.scalars().first()

    def get_balances_by_tranche(self, dl_nbr: int, tr_id: str) -> List[TrancheBal]:
        """Get all balances for a tranche - specialized method."""
        query = select(self.model).where(
            self.model.dl_nbr == dl_nbr,
            self.model.tr_id == tr_id
        ).order_by(self.model.cycle_cde.desc())
        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_latest_balance_by_tranche(self, dl_nbr: int, tr_id: str) -> Optional[TrancheBal]:
        """Get the most recent balance for a tranche - specialized method."""
        query = select(self.model).where(
            self.model.dl_nbr == dl_nbr,
            self.model.tr_id == tr_id
        ).order_by(self.model.cycle_cde.desc()).limit(1)
        result = self.db.execute(query)
        return result.scalars().first()

    def get_balances_by_cycle(self, cycle_cde: int) -> List[TrancheBal]:
        """Get all balances for a specific cycle - specialized method."""
        return self.get_all_by_field("cycle_cde", cycle_cde)

    def get_available_cycles(self) -> List[int]:
        """Get available cycle codes - specialized method."""
        query = select(distinct(self.model.cycle_cde)).order_by(self.model.cycle_cde.desc())
        result = self.db.execute(query)
        return list(result.scalars().all())


class DatawarehouseDAO:
    """Composite DAO that provides a unified interface to all datawarehouse entities."""

    def __init__(self, dw_session: Session):
        self.db = dw_session
        self.deal_dao = DealDAO(dw_session)
        self.tranche_dao = TrancheDAO(dw_session)
        self.tranche_bal_dao = TrancheBalDAO(dw_session)

    # ===== DEAL METHODS (delegated to DealDAO) =====

    def get_all_deals(self) -> List[Deal]:
        """Get all deals ordered by dl_nbr."""
        return self.deal_dao.get_all_ordered()

    def get_deal_by_dl_nbr(self, dl_nbr: int) -> Optional[Deal]:
        """Get a deal by DL number."""
        return self.deal_dao.get_by_dl_nbr(dl_nbr)

    def get_deals_by_issuer(self, issr_cde: str) -> List[Deal]:
        """Get deals by issuer code."""
        return self.deal_dao.get_deals_by_issuer(issr_cde)

    # ===== TRANCHE METHODS (delegated to TrancheDAO) =====

    def get_tranches_by_dl_nbr(self, dl_nbr: int) -> List[Tranche]:
        """Get tranches by DL number."""
        return self.tranche_dao.get_tranches_by_deal(dl_nbr)

    def get_tranche_by_keys(self, dl_nbr: int, tr_id: str) -> Optional[Tranche]:
        """Get a tranche by DL number and tranche ID."""
        return self.tranche_dao.get_by_composite_key(dl_nbr, tr_id)

    # ===== TRANCHE BALANCE METHODS (delegated to TrancheBalDAO) =====

    def get_tranchebals_by_tranche(self, dl_nbr: int, tr_id: str) -> List[TrancheBal]:
        """Get tranche balance data by tranche DL number and tranche ID."""
        return self.tranche_bal_dao.get_balances_by_tranche(dl_nbr, tr_id)

    def get_tranchebal_by_keys(
        self, dl_nbr: int, tr_id: str, cycle_cde: Optional[int] = None
    ) -> Optional[TrancheBal]:
        """Get tranche balance data by keys, optionally for a specific cycle."""
        if cycle_cde:
            return self.tranche_bal_dao.get_by_composite_key(dl_nbr, tr_id, cycle_cde)
        else:
            return self.tranche_bal_dao.get_latest_balance_by_tranche(dl_nbr, tr_id)

    def get_available_cycles(self) -> List[Dict[str, Any]]:
        """Get available cycle codes formatted for UI."""
        try:
            cycle_codes = self.tranche_bal_dao.get_available_cycles()
            
            cycles = []
            for cycle_code in cycle_codes:
                # Format the cycle code for display (e.g., 202401 -> "2024 Q1")
                year = str(cycle_code)[:4]
                quarter_month = str(cycle_code)[4:]

                if quarter_month == "01":
                    label = f"{year} Q1"
                elif quarter_month == "02":
                    label = f"{year} Q2"
                elif quarter_month == "03":
                    label = f"{year} Q3"
                elif quarter_month == "04":
                    label = f"{year} Q4"
                else:
                    # For other formats, just show the raw cycle code
                    label = f"Cycle {cycle_code}"

                cycles.append({
                    "label": label,
                    "value": cycle_code,
                })

            return cycles

        except Exception as e:
            print(f"Error fetching cycles from database: {e}")
            return []

    # ===== CONVENIENCE METHODS =====

    def get_deal_with_tranches(self, dl_nbr: int) -> Optional[Deal]:
        """Get a deal with its tranches loaded."""
        deal = self.deal_dao.get_by_dl_nbr(dl_nbr)
        if deal:
            # The relationship should be loaded automatically, but this ensures it
            deal.tranches = self.tranche_dao.get_tranches_by_deal(dl_nbr)
        return deal

    def get_tranche_with_balances(self, dl_nbr: int, tr_id: str) -> Optional[Tranche]:
        """Get a tranche with its balance history loaded."""
        tranche = self.tranche_dao.get_by_composite_key(dl_nbr, tr_id)
        if tranche:
            tranche.tranchebals = self.tranche_bal_dao.get_balances_by_tranche(dl_nbr, tr_id)
        return tranche