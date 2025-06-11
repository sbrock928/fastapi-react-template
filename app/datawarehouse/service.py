# app/datawarehouse/service.py
"""Service layer for the datawarehouse module using BaseService."""

from typing import List, Optional, Dict, Any
from fastapi import HTTPException

from app.core.base_service import BaseService
from app.datawarehouse.dao import DealDAO, TrancheDAO, TrancheBalDAO, DatawarehouseDAO
from app.datawarehouse.models import Deal, Tranche, TrancheBal
from app.datawarehouse.schemas import (
    DealRead, DealCreate, DealUpdate,
    TrancheRead, TrancheCreate, TrancheUpdate,
    TrancheBalRead, TrancheBalCreate, TrancheBalUpdate,
    DealWithTranches, TrancheWithBals, TrancheWithDeal, TrancheBalWithTranche
)


class DealService(BaseService[Deal, DealCreate, DealUpdate, DealRead]):
    """Service for Deal operations using BaseService."""

    def __init__(self, deal_dao: DealDAO):
        super().__init__(deal_dao)
        self.deal_dao = deal_dao  # Type hint for specialized methods

    def _to_response(self, record: Deal) -> DealRead:
        """Convert Deal model to DealRead schema."""
        return DealRead.model_validate(record)

    def _validate_create(self, create_data: DealCreate) -> None:
        """Validate deal creation data."""
        # Check if deal with same dl_nbr already exists
        if self.deal_dao.get_by_dl_nbr(create_data.dl_nbr):
            raise HTTPException(
                status_code=400, 
                detail=f"Deal with dl_nbr {create_data.dl_nbr} already exists"
            )
        
        # Check if deal with same CUSIP already exists
        if self.deal_dao.get_by_cusip(create_data.deal_cusip_id):
            raise HTTPException(
                status_code=400,
                detail=f"Deal with CUSIP {create_data.deal_cusip_id} already exists"
            )

    def _validate_update(self, record: Deal, update_data: DealUpdate) -> None:
        """Validate deal update data."""
        # If updating CUSIP, ensure it doesn't conflict with existing deals
        if update_data.deal_cusip_id is not None:
            existing_deal = self.deal_dao.get_by_cusip(update_data.deal_cusip_id)
            if existing_deal and existing_deal.dl_nbr != record.dl_nbr:
                raise HTTPException(
                    status_code=400,
                    detail=f"Deal with CUSIP {update_data.deal_cusip_id} already exists"
                )

    # ===== SPECIALIZED METHODS =====

    def get_by_dl_nbr(self, dl_nbr: int) -> Optional[DealRead]:
        """Get deal by DL number."""
        deal = self.deal_dao.get_by_dl_nbr(dl_nbr)
        return self._to_response(deal) if deal else None

    def get_by_cusip(self, deal_cusip_id: str) -> Optional[DealRead]:
        """Get deal by CUSIP."""
        deal = self.deal_dao.get_by_cusip(deal_cusip_id)
        return self._to_response(deal) if deal else None

    def get_deals_by_issuer(self, issr_cde: str) -> List[DealRead]:
        """Get deals by issuer code."""
        deals = self.deal_dao.get_deals_by_issuer(issr_cde)
        return [self._to_response(deal) for deal in deals]

    def get_all_ordered(self) -> List[DealRead]:
        """Get all deals ordered by dl_nbr."""
        deals = self.deal_dao.get_all_ordered()
        return [self._to_response(deal) for deal in deals]


class TrancheService(BaseService[Tranche, TrancheCreate, TrancheUpdate, TrancheRead]):
    """Service for Tranche operations using BaseService."""

    def __init__(self, tranche_dao: TrancheDAO):
        super().__init__(tranche_dao)
        self.tranche_dao = tranche_dao  # Type hint for specialized methods

    def _to_response(self, record: Tranche) -> TrancheRead:
        """Convert Tranche model to TrancheRead schema."""
        return TrancheRead.model_validate(record)

    def _validate_create(self, create_data: TrancheCreate) -> None:
        """Validate tranche creation data."""
        # Check if tranche with same composite key already exists
        if self.tranche_dao.get_by_composite_key(create_data.dl_nbr, create_data.tr_id):
            raise HTTPException(
                status_code=400,
                detail=f"Tranche with dl_nbr {create_data.dl_nbr} and tr_id {create_data.tr_id} already exists"
            )
        
        # Check if tranche with same CUSIP already exists
        if self.tranche_dao.get_by_cusip(create_data.tr_cusip_id):
            raise HTTPException(
                status_code=400,
                detail=f"Tranche with CUSIP {create_data.tr_cusip_id} already exists"
            )

    def _validate_update(self, record: Tranche, update_data: TrancheUpdate) -> None:
        """Validate tranche update data."""
        # If updating CUSIP, ensure it doesn't conflict
        if update_data.tr_cusip_id is not None:
            existing_tranche = self.tranche_dao.get_by_cusip(update_data.tr_cusip_id)
            if existing_tranche and (existing_tranche.dl_nbr != record.dl_nbr or existing_tranche.tr_id != record.tr_id):
                raise HTTPException(
                    status_code=400,
                    detail=f"Tranche with CUSIP {update_data.tr_cusip_id} already exists"
                )

    # ===== SPECIALIZED METHODS =====

    def get_by_composite_key(self, dl_nbr: int, tr_id: str) -> Optional[TrancheRead]:
        """Get tranche by composite key."""
        tranche = self.tranche_dao.get_by_composite_key(dl_nbr, tr_id)
        return self._to_response(tranche) if tranche else None

    def get_by_cusip(self, tr_cusip_id: str) -> Optional[TrancheRead]:
        """Get tranche by CUSIP."""
        tranche = self.tranche_dao.get_by_cusip(tr_cusip_id)
        return self._to_response(tranche) if tranche else None

    def get_tranches_by_deal(self, dl_nbr: int) -> List[TrancheRead]:
        """Get tranches by deal number."""
        tranches = self.tranche_dao.get_tranches_by_deal(dl_nbr)
        return [self._to_response(tranche) for tranche in tranches]


class TrancheBalService(BaseService[TrancheBal, TrancheBalCreate, TrancheBalUpdate, TrancheBalRead]):
    """Service for TrancheBal operations using BaseService."""

    def __init__(self, tranche_bal_dao: TrancheBalDAO):
        super().__init__(tranche_bal_dao)
        self.tranche_bal_dao = tranche_bal_dao  # Type hint for specialized methods

    def _to_response(self, record: TrancheBal) -> TrancheBalRead:
        """Convert TrancheBal model to TrancheBalRead schema."""
        return TrancheBalRead.model_validate(record)

    def _validate_create(self, create_data: TrancheBalCreate) -> None:
        """Validate tranche balance creation data."""
        # Check if balance record already exists for this tranche and cycle
        if self.tranche_bal_dao.get_by_composite_key(create_data.dl_nbr, create_data.tr_id, create_data.cycle_cde):
            raise HTTPException(
                status_code=400,
                detail=f"Balance record already exists for dl_nbr {create_data.dl_nbr}, tr_id {create_data.tr_id}, cycle {create_data.cycle_cde}"
            )

    def _validate_update(self, record: TrancheBal, update_data: TrancheBalUpdate) -> None:
        """Validate tranche balance update data."""
        # Generally, updates to balance records should be allowed
        # Add specific business validation rules here if needed
        pass

    # ===== SPECIALIZED METHODS =====

    def get_by_composite_key(self, dl_nbr: int, tr_id: str, cycle_cde: int) -> Optional[TrancheBalRead]:
        """Get tranche balance by composite key."""
        balance = self.tranche_bal_dao.get_by_composite_key(dl_nbr, tr_id, cycle_cde)
        return self._to_response(balance) if balance else None

    def get_balances_by_tranche(self, dl_nbr: int, tr_id: str) -> List[TrancheBalRead]:
        """Get all balances for a tranche."""
        balances = self.tranche_bal_dao.get_balances_by_tranche(dl_nbr, tr_id)
        return [self._to_response(balance) for balance in balances]

    def get_latest_balance_by_tranche(self, dl_nbr: int, tr_id: str) -> Optional[TrancheBalRead]:
        """Get the most recent balance for a tranche."""
        balance = self.tranche_bal_dao.get_latest_balance_by_tranche(dl_nbr, tr_id)
        return self._to_response(balance) if balance else None

    def get_balances_by_cycle(self, cycle_cde: int) -> List[TrancheBalRead]:
        """Get all balances for a specific cycle."""
        balances = self.tranche_bal_dao.get_balances_by_cycle(cycle_cde)
        return [self._to_response(balance) for balance in balances]

    def get_available_cycles(self) -> List[int]:
        """Get available cycle codes."""
        return self.tranche_bal_dao.get_available_cycles()


class DatawarehouseService:
    """Composite service that provides a unified interface to all datawarehouse operations."""

    def __init__(self, datawarehouse_dao: DatawarehouseDAO):
        self.dao = datawarehouse_dao
        
        # Create individual services
        self.deal_service = DealService(datawarehouse_dao.deal_dao)
        self.tranche_service = TrancheService(datawarehouse_dao.tranche_dao)
        self.tranche_bal_service = TrancheBalService(datawarehouse_dao.tranche_bal_dao)

    # ===== DIRECT DELEGATION METHODS (for backward compatibility) =====

    def get_all_deals(self) -> List[DealRead]:
        """Get all deals ordered by dl_nbr."""
        return self.deal_service.get_all_ordered()

    def get_deal_by_dl_nbr(self, dl_nbr: int) -> Optional[DealRead]:
        """Get a deal by DL number."""
        return self.deal_service.get_by_dl_nbr(dl_nbr)

    def get_tranches_by_dl_nbr(self, dl_nbr: int) -> List[TrancheRead]:
        """Get tranches by DL number."""
        return self.tranche_service.get_tranches_by_deal(dl_nbr)

    def get_tranche_by_keys(self, dl_nbr: int, tr_id: str) -> Optional[TrancheRead]:
        """Get a tranche by composite key."""
        return self.tranche_service.get_by_composite_key(dl_nbr, tr_id)

    def get_tranchebals_by_tranche(self, dl_nbr: int, tr_id: str) -> List[TrancheBalRead]:
        """Get tranche balance data by tranche."""
        return self.tranche_bal_service.get_balances_by_tranche(dl_nbr, tr_id)

    def get_tranchebal_by_keys(
        self, dl_nbr: int, tr_id: str, cycle_cde: Optional[int] = None
    ) -> Optional[TrancheBalRead]:
        """Get tranche balance data by keys."""
        if cycle_cde:
            return self.tranche_bal_service.get_by_composite_key(dl_nbr, tr_id, cycle_cde)
        else:
            return self.tranche_bal_service.get_latest_balance_by_tranche(dl_nbr, tr_id)

    def get_available_cycles(self) -> List[Dict[str, Any]]:
        """Get available cycle codes formatted for UI."""
        return self.dao.get_available_cycles()

    # ===== ENHANCED COMPOSITE METHODS =====

    def get_deal_with_tranches(self, dl_nbr: int) -> Optional[DealWithTranches]:
        """Get a deal with its tranches loaded."""
        deal = self.deal_service.get_by_dl_nbr(dl_nbr)
        if not deal:
            return None

        tranches = self.tranche_service.get_tranches_by_deal(dl_nbr)
        
        # Convert to DealWithTranches schema
        deal_data = deal.model_dump()
        deal_data["tranches"] = [tranche.model_dump() for tranche in tranches]
        
        return DealWithTranches.model_validate(deal_data)

    def get_tranche_with_deal(self, dl_nbr: int, tr_id: str) -> Optional[TrancheWithDeal]:
        """Get a tranche with its parent deal loaded."""
        tranche = self.tranche_service.get_by_composite_key(dl_nbr, tr_id)
        if not tranche:
            return None

        deal = self.deal_service.get_by_dl_nbr(dl_nbr)
        if not deal:
            return None

        # Convert to TrancheWithDeal schema
        tranche_data = tranche.model_dump()
        tranche_data["deal"] = deal.model_dump()
        
        return TrancheWithDeal.model_validate(tranche_data)

    def get_tranche_with_balances(self, dl_nbr: int, tr_id: str) -> Optional[TrancheWithBals]:
        """Get a tranche with its balance history loaded."""
        tranche = self.tranche_service.get_by_composite_key(dl_nbr, tr_id)
        if not tranche:
            return None

        balances = self.tranche_bal_service.get_balances_by_tranche(dl_nbr, tr_id)
        
        # Convert to TrancheWithBals schema
        tranche_data = tranche.model_dump()
        tranche_data["tranchebals"] = [balance.model_dump() for balance in balances]
        
        return TrancheWithBals.model_validate(tranche_data)

    def get_tranchebal_with_tranche(self, dl_nbr: int, tr_id: str, cycle_cde: int) -> Optional[TrancheBalWithTranche]:
        """Get a tranche balance with its parent tranche loaded."""
        balance = self.tranche_bal_service.get_by_composite_key(dl_nbr, tr_id, cycle_cde)
        if not balance:
            return None

        tranche = self.tranche_service.get_by_composite_key(dl_nbr, tr_id)
        if not tranche:
            return None

        # Convert to TrancheBalWithTranche schema
        balance_data = balance.model_dump()
        balance_data["tranche"] = tranche.model_dump()
        
        return TrancheBalWithTranche.model_validate(balance_data)

    # ===== BUSINESS LOGIC METHODS =====

    def get_deals_by_issuer(self, issr_cde: str) -> List[DealRead]:
        """Get deals by issuer code."""
        return self.deal_service.get_deals_by_issuer(issr_cde)

    def get_unique_issuer_codes(self) -> List[str]:
        """Get unique issuer codes for filtering."""
        deals = self.deal_service.get_all_ordered()
        issuer_codes = list(set(deal.issr_cde for deal in deals))
        return sorted(issuer_codes)

    def get_portfolio_summary(self, cycle_cde: Optional[int] = None) -> Dict[str, Any]:
        """Get portfolio summary statistics."""
        try:
            deals = self.get_all_deals()
            
            if cycle_cde:
                balances = self.tranche_bal_service.get_balances_by_cycle(cycle_cde)
            else:
                # Get latest balances for all tranches
                balances = []
                for deal in deals:
                    tranches = self.get_tranches_by_dl_nbr(deal.dl_nbr)
                    for tranche in tranches:
                        latest_balance = self.tranche_bal_service.get_latest_balance_by_tranche(
                            deal.dl_nbr, tranche.tr_id
                        )
                        if latest_balance:
                            balances.append(latest_balance)

            # Calculate summary statistics
            total_ending_balance = sum(balance.tr_end_bal_amt for balance in balances)
            total_interest_distribution = sum(balance.tr_int_dstrb_amt for balance in balances)
            total_principal_distribution = sum(balance.tr_prin_dstrb_amt for balance in balances)
            
            # Calculate weighted average pass through rate
            if balances:
                weighted_rate_sum = sum(
                    balance.tr_pass_thru_rte * balance.tr_end_bal_amt 
                    for balance in balances
                )
                avg_pass_thru_rate = weighted_rate_sum / total_ending_balance if total_ending_balance > 0 else 0
            else:
                avg_pass_thru_rate = 0

            return {
                "deal_count": len(deals),
                "tranche_count": len(balances),
                "total_ending_balance": total_ending_balance,
                "total_interest_distribution": total_interest_distribution,
                "total_principal_distribution": total_principal_distribution,
                "weighted_avg_pass_thru_rate": avg_pass_thru_rate,
                "cycle_code": cycle_cde,
                "unique_issuers": len(self.get_unique_issuer_codes()),
            }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error calculating portfolio summary: {str(e)}"
            )