# filepath: c:\Users\steph\fastapi-react-template\app\reporting\service.py
"""Service layer for the reporting module."""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from decimal import Decimal
from pydantic import ValidationError

from app.reporting.dao import ReportDAO
from app.reporting.models import Report, ReportDeal, ReportTranche
from app.reporting.schemas import (
    ReportRead, ReportCreate, ReportUpdate, ReportSummary, ReportScope,
    ReportDealCreate, ReportTrancheCreate
)
from app.datawarehouse.dao import DatawarehouseDAO
from app.datawarehouse.schemas import DealRead, TrancheRead


class ReportService:
    """Service for managing report configurations and coordinating with data warehouse."""

    def __init__(
        self,
        report_dao: ReportDAO,
        dw_dao: DatawarehouseDAO,
    ):
        self.report_dao = report_dao
        self.dw_dao = dw_dao

    async def _validate_database_constraints(
        self, 
        report_data: ReportCreate | ReportUpdate, 
        existing_report_id: Optional[int] = None
    ) -> None:
        """Centralized database-dependent validation."""
        errors = []

        # Name uniqueness validation
        if hasattr(report_data, 'name') and report_data.name:
            existing_reports = await self.report_dao.get_all()
            name_conflicts = [
                r for r in existing_reports 
                if r.name == report_data.name and r.id != existing_report_id
            ]
            if name_conflicts:
                errors.append("Report name already exists")

        # Validate deal existence in data warehouse
        if hasattr(report_data, 'selected_deals') and report_data.selected_deals:
            dl_nbrs = [deal.dl_nbr for deal in report_data.selected_deals]
            existing_deals = []
            for dl_nbr in dl_nbrs:
                deal = self.dw_dao.get_deal_by_dl_nbr(dl_nbr)
                if deal:
                    existing_deals.append(deal)
            
            existing_dl_nbrs = {deal.dl_nbr for deal in existing_deals}
            missing_dl_nbrs = set(dl_nbrs) - existing_dl_nbrs
            
            if missing_dl_nbrs:
                errors.append(f"Deal numbers not found in data warehouse: {sorted(missing_dl_nbrs)}")

            # Validate tranche existence for tranche-level reports
            if (hasattr(report_data, 'scope') and 
                report_data.scope == ReportScope.TRANCHE):
                
                all_tranche_keys = []
                for deal in report_data.selected_deals:
                    all_tranche_keys.extend([(t.dl_nbr, t.tr_id) for t in deal.selected_tranches])
                
                if all_tranche_keys:
                    existing_tranches = []
                    for dl_nbr, tr_id in all_tranche_keys:
                        tranche = self.dw_dao.get_tranche_by_keys(dl_nbr, tr_id)
                        if tranche:
                            existing_tranches.append(tranche)
                    
                    existing_tranche_keys = {(tranche.dl_nbr, tranche.tr_id) for tranche in existing_tranches}
                    missing_tranche_keys = set(all_tranche_keys) - existing_tranche_keys
                    
                    if missing_tranche_keys:
                        missing_keys_str = [f"({dl_nbr}, {tr_id})" for dl_nbr, tr_id in sorted(missing_tranche_keys)]
                        errors.append(f"Tranche keys not found in data warehouse: {missing_keys_str}")

        if errors:
            raise HTTPException(status_code=422, detail={"errors": errors})

    async def get_all(self) -> List[ReportRead]:
        """Get all reports."""
        reports = await self.report_dao.get_all()
        return [ReportRead.model_validate(report) for report in reports]

    async def get_by_id(self, report_id: int) -> Optional[ReportRead]:
        """Get a report by ID."""
        report = await self.report_dao.get_by_id(report_id)
        if not report:
            return None
        return ReportRead.model_validate(report)

    async def get_all_summaries(self) -> List[ReportSummary]:
        """Get all reports with summary information."""
        reports = await self.report_dao.get_all()
        summaries = []

        for report in reports:
            deal_count = len(report.selected_deals)
            tranche_count = sum(len(deal.selected_tranches) for deal in report.selected_deals)

            summary = ReportSummary(
                id=report.id,
                name=report.name,
                scope=ReportScope(report.scope),
                created_by=report.created_by or "system",
                created_date=report.created_date,
                deal_count=deal_count,
                tranche_count=tranche_count,
                is_active=report.is_active,
            )
            summaries.append(summary)

        return summaries

    async def create(self, report_data: ReportCreate) -> ReportRead:
        """Create a new report with simplified validation."""
        # Pydantic already handled structural validation
        # Only validate database constraints
        await self._validate_database_constraints(report_data)

        # Direct model creation using Pydantic's model_dump
        report_dict = report_data.model_dump()
        report_dict['scope'] = report_data.scope.value  # Convert enum to string
        
        # Create main report
        report = Report(**{k: v for k, v in report_dict.items() if k != 'selected_deals'})
        
        # Add deals and tranches
        for deal_data in report_data.selected_deals:
            report_deal = ReportDeal(dl_nbr=deal_data.dl_nbr)
            
            for tranche_data in deal_data.selected_tranches:
                report_tranche = ReportTranche(dl_nbr=tranche_data.dl_nbr, tr_id=tranche_data.tr_id)
                report_deal.selected_tranches.append(report_tranche)
            
            report.selected_deals.append(report_deal)
        
        created_report = await self.report_dao.create(report)
        return ReportRead.model_validate(created_report)

    async def update(self, report_id: int, report_data: ReportUpdate) -> Optional[ReportRead]:
        """Update a report with simplified validation."""
        report = await self.report_dao.get_by_id(report_id)
        if not report:
            return None

        # Pydantic already handled structural validation
        # Only validate database constraints
        await self._validate_database_constraints(report_data, existing_report_id=report_id)

        # Update basic fields using Pydantic's model_dump
        update_data = report_data.model_dump(exclude_unset=True, exclude={'selected_deals'})
        
        # Handle scope enum conversion
        if "scope" in update_data and update_data["scope"]:
            update_data["scope"] = update_data["scope"].value

        for field, value in update_data.items():
            setattr(report, field, value)

        # Handle deals and tranches update if provided
        if report_data.selected_deals is not None:
            report.selected_deals.clear()
            
            for deal_data in report_data.selected_deals:
                report_deal = ReportDeal(dl_nbr=deal_data.dl_nbr)
                
                for tranche_data in deal_data.selected_tranches:
                    report_tranche = ReportTranche(dl_nbr=tranche_data.dl_nbr, tr_id=tranche_data.tr_id)
                    report_deal.selected_tranches.append(report_tranche)
                
                report.selected_deals.append(report_deal)

        updated_report = await self.report_dao.update(report)
        return ReportRead.model_validate(updated_report)

    async def delete(self, report_id: int) -> bool:
        """Delete a report."""
        return await self.report_dao.delete(report_id)

    async def run_saved_report(self, report_id: int, cycle_code: int) -> List[Dict[str, Any]]:
        """Run a saved report by fetching config and querying data warehouse."""

        # 1. Get report configuration from config DB
        report = await self.report_dao.get_by_id(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        if not report.is_active:
            raise HTTPException(status_code=400, detail="Report is inactive")

        # 2. Query data warehouse using stored keys
        results = []

        if report.scope == "DEAL":
            # Deal-level report: one row per deal with aggregated data from tranche balance tables
            for report_deal in report.selected_deals:
                dl_nbr = report_deal.dl_nbr
                
                # Get static deal data
                deal = self.dw_dao.get_deal_by_dl_nbr(dl_nbr)
                if not deal:
                    continue

                # Get tranches for this deal
                tranches = self.dw_dao.get_tranches_by_dl_nbr(dl_nbr)
                tranche_keys = [(t.dl_nbr, t.tr_id) for t in tranches]

                # Get balance data for all tranches in this deal
                balance_data = []
                for dl_nbr_key, tr_id in tranche_keys:
                    balance = self.dw_dao.get_tranchebal_by_keys(dl_nbr_key, tr_id)
                    if balance:
                        balance_data.append(balance)

                # Calculate aggregated metrics from balance data
                if balance_data:
                    total_tranche_balance = sum(
                        float(b.balance) for b in balance_data if b.balance
                    )
                    tranche_count = len(balance_data)
                else:
                    total_tranche_balance = 0
                    tranche_count = 0

                result_row = {
                    "dl_nbr": deal.dl_nbr,
                    "issr_cde": deal.issr_cde,
                    "cdi_file_nme": deal.cdi_file_nme,
                    "CDB_cdi_file_nme": deal.CDB_cdi_file_nme,
                    # Aggregated tranche data
                    "tranche_count": tranche_count,
                    "total_tranche_balance": total_tranche_balance,
                }
                results.append(result_row)

        else:  # TRANCHE level
            # Tranche-level report: one row per selected tranche with balance data
            for report_deal in report.selected_deals:
                dl_nbr = report_deal.dl_nbr
                
                # Get deal info for context
                deal = self.dw_dao.get_deal_by_dl_nbr(dl_nbr)
                if not deal:
                    continue

                # Get selected tranche keys for this deal
                tranche_keys = [(rt.dl_nbr, rt.tr_id) for rt in report_deal.selected_tranches]

                # Get data for each selected tranche
                for dl_nbr_key, tr_id in tranche_keys:
                    tranche = self.dw_dao.get_tranche_by_keys(dl_nbr_key, tr_id)
                    if not tranche:
                        continue
                    
                    # Get balance data for this tranche
                    balance = self.dw_dao.get_tranchebal_by_keys(dl_nbr_key, tr_id)

                    result_row = {
                        "dl_nbr": deal.dl_nbr,
                        "deal_issr_cde": deal.issr_cde,
                        "deal_cdi_file_nme": deal.cdi_file_nme,
                        "deal_CDB_cdi_file_nme": deal.CDB_cdi_file_nme,
                        "tr_id": tranche.tr_id,
                        "balance": float(balance.balance) if balance and balance.balance else 0.0,                    }
                    results.append(result_row)

        return results

    async def get_available_deals(self, cycle_code: Optional[int] = None) -> List[DealRead]:
        """Get available deals for report building."""
        deals = self.dw_dao.get_all_deals()
        return [DealRead.model_validate(deal) for deal in deals]

    async def get_available_tranches_for_deals(
        self, dl_nbrs: List[int], cycle_code: Optional[int] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get available tranches for specific deals."""
        result = {}
        for dl_nbr in dl_nbrs:
            # Get static tranche data
            tranches = self.dw_dao.get_tranches_by_dl_nbr(dl_nbr)

            # Convert to report format
            tranche_summaries = []
            for tranche in tranches:
                # Get deal info for context
                deal = self.dw_dao.get_deal_by_dl_nbr(dl_nbr)
                deal_info = deal.issr_cde if deal else "Unknown Deal"

                # Get balance data
                balance = self.dw_dao.get_tranchebal_by_keys(tranche.dl_nbr, tranche.tr_id)

                summary = {
                    "dl_nbr": tranche.dl_nbr,
                    "tr_id": tranche.tr_id,
                    "deal_issr_cde": deal_info,
                    "balance": float(balance.balance) if balance and balance.balance else 0.0,
                }
                tranche_summaries.append(summary)

            # Convert dl_nbr (int) to string for response model compatibility
            result[str(dl_nbr)] = tranche_summaries

        return result

    async def get_available_cycles(self) -> List[Dict[str, Any]]:
        """Get available cycle codes from the data warehouse."""
        try:
            return self.dw_dao.get_available_cycles()
        except Exception as e:
            # Fallback to empty data
            print(f"Warning: Could not fetch cycle data from data warehouse: {e}")
            return []
