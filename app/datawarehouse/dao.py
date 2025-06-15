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

    def get_tranchebal_by_keys(
        self, dl_nbr: int, tr_id: str, cycle_date: Optional[int] = None
    ) -> Optional[TrancheBal]:
        """Get tranche cycle data by DL number, tranche ID, and optionally cycle date"""
        if cycle_date:
            stmt = select(TrancheBal).where(
                TrancheBal.dl_nbr == dl_nbr,
                TrancheBal.tr_id == tr_id,
                TrancheBal.cycle_cde == cycle_date,
            )
        else:
            # Get the most recent cycle data if no cycle date specified
            stmt = (
                select(TrancheBal)
                .where(TrancheBal.dl_nbr == dl_nbr, TrancheBal.tr_id == tr_id)
                .order_by(TrancheBal.cycle_cde.desc())
                .limit(1)
            )

        result = self.db.execute(stmt)
        return result.scalars().first()

    def get_available_cycles(self) -> List[Dict[str, Any]]:
        """Get available cycle codes from the data warehouse."""
        try:
            # Get distinct cycle codes from TrancheBal table
            stmt = select(TrancheBal.cycle_cde).distinct().order_by(TrancheBal.cycle_cde.desc())
            result = self.db.execute(stmt)
            cycle_codes = result.scalars().all()

            # Convert to the expected format with both label and value
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

                cycles.append(
                    {
                        "label": label,
                        "value": cycle_code,  # Use the actual cycle code from the database
                    }
                )

            return cycles

        except Exception as e:
            print(f"Error fetching cycles from database: {e}")
            # Return empty list instead of dummy data
            return []

    def get_available_tranches_for_deals(self, deal_ids: List[int], cycle_code: int = None) -> Dict[int, List[Dict[str, Any]]]:
        """Get available tranches for specific deals."""
        result = {}
        
        for deal_id in deal_ids:
            # Get tranches for this deal
            tranches = self.get_tranches_by_dl_nbr(deal_id)
            
            tranche_list = []
            for tranche in tranches:
                # Get balance data for this tranche
                if cycle_code:
                    balance = self.get_tranchebal_by_keys(deal_id, tranche.tr_id, cycle_code)
                else:
                    balance = self.get_tranchebal_by_keys(deal_id, tranche.tr_id)
                
                if balance:  # Only include tranches that have balance data
                    tranche_list.append({
                        "tr_id": tranche.tr_id,
                        "dl_nbr": tranche.dl_nbr,
                        "cycle_cde": balance.cycle_cde if balance else None,
                        "balance": float(balance.tr_end_bal_amt) if balance and balance.tr_end_bal_amt else 0.0
                    })
            
            result[deal_id] = tranche_list
        
        return result
