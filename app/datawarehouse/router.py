# app/datawarehouse/router.py
"""API router for the datawarehouse module."""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.core.dependencies import DWSessionDep
from app.datawarehouse.service import DatawarehouseService, DealService, TrancheService, TrancheBalService
from app.datawarehouse.dao import DatawarehouseDAO, DealDAO, TrancheDAO, TrancheBalDAO
from app.datawarehouse.schemas import (
    DealRead, DealCreate, DealUpdate,
    TrancheRead, TrancheCreate, TrancheUpdate,
    TrancheBalRead, TrancheBalCreate, TrancheBalUpdate,
    DealWithTranches, TrancheWithBals, TrancheWithDeal, TrancheBalWithTranche
)

router = APIRouter(prefix="/datawarehouse", tags=["Data Warehouse"])


# ===== DEPENDENCY INJECTION =====

def get_datawarehouse_dao(dw_session: DWSessionDep) -> DatawarehouseDAO:
    """Get DatawarehouseDAO instance."""
    return DatawarehouseDAO(dw_session)

def get_deal_dao(dw_session: DWSessionDep) -> DealDAO:
    """Get DealDAO instance."""
    return DealDAO(dw_session)

def get_tranche_dao(dw_session: DWSessionDep) -> TrancheDAO:
    """Get TrancheDAO instance."""
    return TrancheDAO(dw_session)

def get_tranche_bal_dao(dw_session: DWSessionDep) -> TrancheBalDAO:
    """Get TrancheBalDAO instance."""
    return TrancheBalDAO(dw_session)

def get_datawarehouse_service(dao: DatawarehouseDAO = Depends(get_datawarehouse_dao)) -> DatawarehouseService:
    """Get DatawarehouseService instance."""
    return DatawarehouseService(dao)

def get_deal_service(dao: DealDAO = Depends(get_deal_dao)) -> DealService:
    """Get DealService instance."""
    return DealService(dao)

def get_tranche_service(dao: TrancheDAO = Depends(get_tranche_dao)) -> TrancheService:
    """Get TrancheService instance."""
    return TrancheService(dao)

def get_tranche_bal_service(dao: TrancheBalDAO = Depends(get_tranche_bal_dao)) -> TrancheBalService:
    """Get TrancheBalService instance."""
    return TrancheBalService(dao)


# ===== DEAL ENDPOINTS =====

@router.get("/deals", response_model=List[DealRead])
def get_all_deals(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    issr_cde: Optional[str] = Query(None, description="Filter by issuer code"),
    service: DatawarehouseService = Depends(get_datawarehouse_service)
) -> List[DealRead]:
    """Get all deals with optional filtering."""
    if issr_cde:
        return service.get_deals_by_issuer(issr_cde)
    else:
        deals = service.get_all_deals()
        return deals[skip:skip + limit]


@router.get("/deals/{dl_nbr}", response_model=DealRead)
def get_deal_by_dl_nbr(
    dl_nbr: int,
    service: DatawarehouseService = Depends(get_datawarehouse_service)
) -> DealRead:
    """Get a deal by DL number."""
    deal = service.get_deal_by_dl_nbr(dl_nbr)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.get("/deals/{dl_nbr}/with-tranches", response_model=DealWithTranches)
def get_deal_with_tranches(
    dl_nbr: int,
    service: DatawarehouseService = Depends(get_datawarehouse_service)
) -> DealWithTranches:
    """Get a deal with its tranches loaded."""
    deal = service.get_deal_with_tranches(dl_nbr)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.post("/deals", response_model=DealRead, status_code=201)
def create_deal(
    deal_data: DealCreate,
    deal_service: DealService = Depends(get_deal_service)
) -> DealRead:
    """Create a new deal."""
    return deal_service.create(deal_data)


@router.patch("/deals/{dl_nbr}", response_model=DealRead)
def update_deal(
    dl_nbr: int,
    deal_data: DealUpdate,
    deal_service: DealService = Depends(get_deal_service)
) -> DealRead:
    """Update an existing deal."""
    # Note: BaseService uses integer IDs, but we need to find by dl_nbr
    deal = deal_service.deal_dao.get_by_dl_nbr(dl_nbr)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    # Since Deal has composite primary key, we need to handle this specially
    updated_deal = deal_service.deal_dao.update(deal, **deal_data.model_dump(exclude_unset=True))
    return deal_service._to_response(updated_deal)


@router.delete("/deals/{dl_nbr}")
def delete_deal(
    dl_nbr: int,
    deal_service: DealService = Depends(get_deal_service)
) -> Dict[str, str]:
    """Delete a deal."""
    deal = deal_service.deal_dao.get_by_dl_nbr(dl_nbr)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    # Delete using DAO directly since BaseService delete expects integer ID
    deal_service.deal_dao.db.delete(deal)
    deal_service.deal_dao.db.commit()
    
    return {"message": f"Deal {dl_nbr} deleted successfully"}


# ===== TRANCHE ENDPOINTS =====

@router.get("/tranches", response_model=List[TrancheRead])
def get_tranches(
    dl_nbr: Optional[int] = Query(None, description="Filter by deal number"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: DatawarehouseService = Depends(get_datawarehouse_service)
) -> List[TrancheRead]:
    """Get tranches with optional filtering by deal."""
    if dl_nbr:
        return service.get_tranches_by_dl_nbr(dl_nbr)
    else:
        # Get all tranches (this could be a large dataset)
        tranche_service = TrancheService(service.dao.tranche_dao)
        tranches = tranche_service.get_all(skip=skip, limit=limit)
        return tranches


@router.get("/tranches/{dl_nbr}/{tr_id}", response_model=TrancheRead)
def get_tranche_by_keys(
    dl_nbr: int,
    tr_id: str,
    service: DatawarehouseService = Depends(get_datawarehouse_service)
) -> TrancheRead:
    """Get a tranche by composite key."""
    tranche = service.get_tranche_by_keys(dl_nbr, tr_id)
    if not tranche:
        raise HTTPException(status_code=404, detail="Tranche not found")
    return tranche


@router.get("/tranches/{dl_nbr}/{tr_id}/with-deal", response_model=TrancheWithDeal)
def get_tranche_with_deal(
    dl_nbr: int,
    tr_id: str,
    service: DatawarehouseService = Depends(get_datawarehouse_service)
) -> TrancheWithDeal:
    """Get a tranche with its parent deal loaded."""
    tranche = service.get_tranche_with_deal(dl_nbr, tr_id)
    if not tranche:
        raise HTTPException(status_code=404, detail="Tranche not found")
    return tranche


@router.get("/tranches/{dl_nbr}/{tr_id}/with-balances", response_model=TrancheWithBals)
def get_tranche_with_balances(
    dl_nbr: int,
    tr_id: str,
    service: DatawarehouseService = Depends(get_datawarehouse_service)
) -> TrancheWithBals:
    """Get a tranche with its balance history loaded."""
    tranche = service.get_tranche_with_balances(dl_nbr, tr_id)
    if not tranche:
        raise HTTPException(status_code=404, detail="Tranche not found")
    return tranche


@router.post("/tranches", response_model=TrancheRead, status_code=201)
def create_tranche(
    tranche_data: TrancheCreate,
    tranche_service: TrancheService = Depends(get_tranche_service)
) -> TrancheRead:
    """Create a new tranche."""
    return tranche_service.create(tranche_data)


@router.patch("/tranches/{dl_nbr}/{tr_id}", response_model=TrancheRead)
def update_tranche(
    dl_nbr: int,
    tr_id: str,
    tranche_data: TrancheUpdate,
    tranche_service: TrancheService = Depends(get_tranche_service)
) -> TrancheRead:
    """Update an existing tranche."""
    tranche = tranche_service.tranche_dao.get_by_composite_key(dl_nbr, tr_id)
    if not tranche:
        raise HTTPException(status_code=404, detail="Tranche not found")
    
    updated_tranche = tranche_service.tranche_dao.update(tranche, **tranche_data.model_dump(exclude_unset=True))
    return tranche_service._to_response(updated_tranche)


@router.delete("/tranches/{dl_nbr}/{tr_id}")
def delete_tranche(
    dl_nbr: int,
    tr_id: str,
    tranche_service: TrancheService = Depends(get_tranche_service)
) -> Dict[str, str]:
    """Delete a tranche."""
    tranche = tranche_service.tranche_dao.get_by_composite_key(dl_nbr, tr_id)
    if not tranche:
        raise HTTPException(status_code=404, detail="Tranche not found")
    
    tranche_service.tranche_dao.db.delete(tranche)
    tranche_service.tranche_dao.db.commit()
    
    return {"message": f"Tranche {dl_nbr}/{tr_id} deleted successfully"}


# ===== TRANCHE BALANCE ENDPOINTS =====

@router.get("/tranche-balances", response_model=List[TrancheBalRead])
def get_tranche_balances(
    dl_nbr: Optional[int] = Query(None, description="Filter by deal number"),
    tr_id: Optional[str] = Query(None, description="Filter by tranche ID"),
    cycle_cde: Optional[int] = Query(None, description="Filter by cycle code"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: DatawarehouseService = Depends(get_datawarehouse_service)
) -> List[TrancheBalRead]:
    """Get tranche balances with optional filtering."""
    if dl_nbr and tr_id:
        return service.get_tranchebals_by_tranche(dl_nbr, tr_id)
    elif cycle_cde:
        return service.tranche_bal_service.get_balances_by_cycle(cycle_cde)
    else:
        # Get all balances (this could be a very large dataset)
        tranche_bal_service = TrancheBalService(service.dao.tranche_bal_dao)
        balances = tranche_bal_service.get_all(skip=skip, limit=limit)
        return balances


@router.get("/tranche-balances/{dl_nbr}/{tr_id}/{cycle_cde}", response_model=TrancheBalRead)
def get_tranche_balance_by_keys(
    dl_nbr: int,
    tr_id: str,
    cycle_cde: int,
    service: DatawarehouseService = Depends(get_datawarehouse_service)
) -> TrancheBalRead:
    """Get a tranche balance by composite key."""
    balance = service.tranche_bal_service.get_by_composite_key(dl_nbr, tr_id, cycle_cde)
    if not balance:
        raise HTTPException(status_code=404, detail="Tranche balance not found")
    return balance


@router.get("/tranche-balances/{dl_nbr}/{tr_id}/{cycle_cde}/with-tranche", response_model=TrancheBalWithTranche)
def get_tranche_balance_with_tranche(
    dl_nbr: int,
    tr_id: str,
    cycle_cde: int,
    service: DatawarehouseService = Depends(get_datawarehouse_service)
) -> TrancheBalWithTranche:
    """Get a tranche balance with its parent tranche loaded."""
    balance = service.get_tranchebal_with_tranche(dl_nbr, tr_id, cycle_cde)
    if not balance:
        raise HTTPException(status_code=404, detail="Tranche balance not found")
    return balance


@router.get("/tranche-balances/{dl_nbr}/{tr_id}/latest", response_model=TrancheBalRead)
def get_latest_tranche_balance(
    dl_nbr: int,
    tr_id: str,
    service: DatawarehouseService = Depends(get_datawarehouse_service)
) -> TrancheBalRead:
    """Get the latest balance for a tranche."""
    balance = service.tranche_bal_service.get_latest_balance_by_tranche(dl_nbr, tr_id)
    if not balance:
        raise HTTPException(status_code=404, detail="No balance data found for this tranche")
    return balance


@router.post("/tranche-balances", response_model=TrancheBalRead, status_code=201)
def create_tranche_balance(
    balance_data: TrancheBalCreate,
    tranche_bal_service: TrancheBalService = Depends(get_tranche_bal_service)
) -> TrancheBalRead:
    """Create a new tranche balance record."""
    return tranche_bal_service.create(balance_data)


@router.patch("/tranche-balances/{dl_nbr}/{tr_id}/{cycle_cde}", response_model=TrancheBalRead)
def update_tranche_balance(
    dl_nbr: int,
    tr_id: str,
    cycle_cde: int,
    balance_data: TrancheBalUpdate,
    tranche_bal_service: TrancheBalService = Depends(get_tranche_bal_service)
) -> TrancheBalRead:
    """Update an existing tranche balance record."""
    balance = tranche_bal_service.tranche_bal_dao.get_by_composite_key(dl_nbr, tr_id, cycle_cde)
    if not balance:
        raise HTTPException(status_code=404, detail="Tranche balance not found")
    
    updated_balance = tranche_bal_service.tranche_bal_dao.update(balance, **balance_data.model_dump(exclude_unset=True))
    return tranche_bal_service._to_response(updated_balance)


@router.delete("/tranche-balances/{dl_nbr}/{tr_id}/{cycle_cde}")
def delete_tranche_balance(
    dl_nbr: int,
    tr_id: str,
    cycle_cde: int,
    tranche_bal_service: TrancheBalService = Depends(get_tranche_bal_service)
) -> Dict[str, str]:
    """Delete a tranche balance record."""
    balance = tranche_bal_service.tranche_bal_dao.get_by_composite_key(dl_nbr, tr_id, cycle_cde)
    if not balance:
        raise HTTPException(status_code=404, detail="Tranche balance not found")
    
    tranche_bal_service.tranche_bal_dao.db.delete(balance)
    tranche_bal_service.tranche_bal_dao.db.commit()
    
    return {"message": f"Tranche balance {dl_nbr}/{tr_id}/{cycle_cde} deleted successfully"}


# ===== UTILITY ENDPOINTS =====

@router.get("/cycles", response_model=List[Dict[str, Any]])
def get_available_cycles(
    service: DatawarehouseService = Depends(get_datawarehouse_service)
) -> List[Dict[str, Any]]:
    """Get available cycle codes formatted for UI."""
    return service.get_available_cycles()


@router.get("/issuers", response_model=List[str])
def get_unique_issuer_codes(
    service: DatawarehouseService = Depends(get_datawarehouse_service)
) -> List[str]:
    """Get unique issuer codes for filtering."""
    return service.get_unique_issuer_codes()


@router.get("/portfolio-summary", response_model=Dict[str, Any])
def get_portfolio_summary(
    cycle_cde: Optional[int] = Query(None, description="Specific cycle code for summary"),
    service: DatawarehouseService = Depends(get_datawarehouse_service)
) -> Dict[str, Any]:
    """Get portfolio summary statistics."""
    return service.get_portfolio_summary(cycle_cde)


# ===== HEALTH CHECK ENDPOINT =====

@router.get("/health", response_model=Dict[str, str])
def health_check(
    service: DatawarehouseService = Depends(get_datawarehouse_service)
) -> Dict[str, str]:
    """Health check endpoint for the datawarehouse service."""
    try:
        # Simple check - try to count deals
        deals = service.get_all_deals()
        return {
            "status": "healthy",
            "service": "datawarehouse",
            "deal_count": str(len(deals)),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Datawarehouse service unhealthy: {str(e)}"
        )