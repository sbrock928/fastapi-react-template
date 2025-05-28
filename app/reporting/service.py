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
from app.datawarehouse.dao import DWDao
from app.datawarehouse.schemas import DealRead, TrancheRead, TrancheReportSummary


class ReportService:
    """Service for managing report configurations and coordinating with data warehouse."""

    def __init__(
        self,
        report_dao: ReportDAO,
        dw_dao: DWDao,
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
            deal_ids = [deal.deal_id for deal in report_data.selected_deals]
            existing_deals = await self.dw_dao.get_deals_by_ids(deal_ids)
            existing_deal_ids = {deal.id for deal in existing_deals}
            missing_deal_ids = set(deal_ids) - existing_deal_ids
            
            if missing_deal_ids:
                errors.append(f"Deal IDs not found in data warehouse: {sorted(missing_deal_ids)}")

            # Validate tranche existence for tranche-level reports
            if (hasattr(report_data, 'scope') and 
                report_data.scope == ReportScope.TRANCHE):
                
                all_tranche_ids = []
                for deal in report_data.selected_deals:
                    all_tranche_ids.extend([t.tranche_id for t in deal.selected_tranches])
                
                if all_tranche_ids:
                    existing_tranches = await self.dw_dao.get_tranches_by_ids(all_tranche_ids)
                    existing_tranche_ids = {tranche.id for tranche in existing_tranches}
                    missing_tranche_ids = set(all_tranche_ids) - existing_tranche_ids
                    
                    if missing_tranche_ids:
                        errors.append(f"Tranche IDs not found in data warehouse: {sorted(missing_tranche_ids)}")

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
            report_deal = ReportDeal(deal_id=deal_data.deal_id)
            
            for tranche_data in deal_data.selected_tranches:
                report_tranche = ReportTranche(tranche_id=tranche_data.tranche_id)
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
                report_deal = ReportDeal(deal_id=deal_data.deal_id)
                
                for tranche_data in deal_data.selected_tranches:
                    report_tranche = ReportTranche(tranche_id=tranche_data.tranche_id)
                    report_deal.selected_tranches.append(report_tranche)
                
                report.selected_deals.append(report_deal)

        updated_report = await self.report_dao.update(report)
        return ReportRead.model_validate(updated_report)

    async def delete(self, report_id: int) -> bool:
        """Delete a report."""
        return await self.report_dao.delete(report_id)

    async def run_saved_report(self, report_id: int, cycle_code: str) -> List[Dict[str, Any]]:
        """Run a saved report by fetching config and querying data warehouse."""

        # 1. Get report configuration from config DB
        report = await self.report_dao.get_by_id(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        if not report.is_active:
            raise HTTPException(status_code=400, detail="Report is inactive")

        # 2. Query data warehouse using stored IDs
        results = []

        if report.scope == "DEAL":
            # Deal-level report: one row per deal with aggregated data from historical tables
            for report_deal in report.selected_deals:
                deal_id = report_deal.deal_id
                
                # Get static deal data
                deal = await self.dw_dao.get_deal_by_id(deal_id)
                if not deal:
                    continue

                # Get tranches for this deal
                tranches = await self.dw_dao.get_tranches_by_deal_id(deal_id)
                tranche_ids = [t.id for t in tranches]

                # Get historical data for all tranches in this cycle
                historical_data = (
                    await self.dw_dao.get_historical_by_tranche_ids_and_cycle(
                        tranche_ids, cycle_code
                    )
                )

                # Calculate aggregated metrics from historical data
                if historical_data:
                    total_tranche_principal = sum(
                        float(h.principal_amount) for h in historical_data
                    )
                    avg_interest_rate = sum(
                        float(h.interest_rate) for h in historical_data
                    ) / len(historical_data)
                    tranche_count = len(historical_data)
                else:
                    total_tranche_principal = 0
                    avg_interest_rate = 0
                    tranche_count = 0

                result_row = {
                    "deal_id": deal.id,
                    "deal_name": deal.name,
                    "originator": deal.originator,
                    "deal_type": deal.deal_type,
                    "closing_date": (
                        deal.closing_date.isoformat() if deal.closing_date else None
                    ),
                    "total_principal": float(deal.total_principal),
                    "credit_rating": deal.credit_rating,
                    "yield_rate": float(deal.yield_rate) if deal.yield_rate else None,
                    "duration": float(deal.duration) if deal.duration else None,
                    "cycle_code": cycle_code,
                    # Aggregated tranche data from historical table
                    "tranche_count": tranche_count,
                    "total_tranche_principal": total_tranche_principal,
                    "avg_tranche_interest_rate": avg_interest_rate,
                }
                results.append(result_row)

        else:  # TRANCHE level
            # Tranche-level report: one row per selected tranche with cycle-specific data
            for report_deal in report.selected_deals:
                deal_id = report_deal.deal_id
                
                # Get deal info for context
                deal = await self.dw_dao.get_deal_by_id(deal_id)
                if not deal:
                    continue

                # Get selected tranche IDs for this deal
                tranche_ids = [rt.tranche_id for rt in report_deal.selected_tranches]
                
                # Get static tranche data
                tranches = await self.dw_dao.get_tranches_by_ids(tranche_ids)
                tranche_dict = {t.id: t for t in tranches}

                # Get historical data for selected tranches in this cycle
                historical_data = (
                    await self.dw_dao.get_historical_by_tranche_ids_and_cycle(
                        tranche_ids, cycle_code
                    )
                )

                # Join static tranche data with historical data
                for hist in historical_data:
                    tranche = tranche_dict.get(hist.tranche_id)
                    if not tranche:
                        continue

                    result_row = {
                        "deal_id": deal.id,
                        "deal_name": deal.name,
                        "deal_originator": deal.originator,
                        "deal_type": deal.deal_type,
                        "deal_credit_rating": deal.credit_rating,
                        "deal_yield_rate": float(deal.yield_rate) if deal.yield_rate else None,
                        "tranche_id": tranche.id,
                        "tranche_name": tranche.name,
                        "class_name": tranche.class_name,
                        "subordination_level": tranche.subordination_level,
                        "principal_amount": float(
                            hist.principal_amount
                        ),  # From historical table
                        "interest_rate": float(hist.interest_rate),  # From historical table
                        "credit_rating": tranche.credit_rating,  # Static from tranche table
                        "payment_priority": tranche.payment_priority,
                        "maturity_date": (
                            tranche.maturity_date.isoformat() if tranche.maturity_date else None
                        ),
                        "cycle_code": hist.cycle_code,
                    }
                    results.append(result_row)

        return results

    async def get_available_deals(self, cycle_code: Optional[str] = None) -> List[DealRead]:
        """Get available deals for report building."""
        deals = await self.dw_dao.get_all_deals()
        return [DealRead.model_validate(deal) for deal in deals]

    async def get_available_tranches_for_deals(
        self, deal_ids: List[int], cycle_code: Optional[str] = None
    ) -> Dict[int, List[TrancheReportSummary]]:
        """Get available tranches for specific deals with cycle-specific data if available."""
        result = {}

        for deal_id in deal_ids:
            # Get static tranche data
            tranches = await self.dw_dao.get_tranches_by_deal_id(deal_id)

            # Convert to report format with cycle data if available
            tranche_summaries = []
            for tranche in tranches:
                # Get deal name for the summary
                deal = await self.dw_dao.get_deal_by_id(deal_id)
                deal_name = deal.name if deal else "Unknown Deal"

                if cycle_code:
                    # Try to get historical data for this cycle
                    historical = await self.dw_dao.get_historical_by_tranche_and_cycle(
                        tranche.id, cycle_code
                    )
                    if historical:
                        # Use historical data for cycle-specific fields
                        summary = TrancheReportSummary(
                            id=tranche.id,
                            deal_id=tranche.deal_id,
                            deal_name=deal_name,
                            name=tranche.name,
                            class_name=tranche.class_name,
                            credit_rating=tranche.credit_rating,
                            cycle_code=historical.cycle_code,
                            principal_amount=historical.principal_amount,
                            interest_rate=historical.interest_rate,
                            payment_priority=tranche.payment_priority,
                        )
                    else:
                        # No historical data for this cycle, skip this tranche
                        continue
                else:
                    # No cycle specified, get latest historical data if available
                    latest_historical = await self.dw_dao.get_latest_historical_by_tranche_id(
                        tranche.id
                    )
                    if latest_historical:
                        summary = TrancheReportSummary(
                            id=tranche.id,
                            deal_id=tranche.deal_id,
                            deal_name=deal_name,
                            name=tranche.name,
                            class_name=tranche.class_name,
                            credit_rating=tranche.credit_rating,
                            cycle_code=latest_historical.cycle_code,
                            principal_amount=latest_historical.principal_amount,
                            interest_rate=latest_historical.interest_rate,
                            payment_priority=tranche.payment_priority,
                        )
                    else:
                        # No historical data at all, use placeholder values
                        summary = TrancheReportSummary(
                            id=tranche.id,
                            deal_id=tranche.deal_id,
                            deal_name=deal_name,
                            name=tranche.name,
                            class_name=tranche.class_name,
                            credit_rating=tranche.credit_rating,
                            cycle_code="N/A",
                            principal_amount=Decimal("0"),
                            interest_rate=Decimal("0"),
                            payment_priority=tranche.payment_priority,
                        )

                tranche_summaries.append(summary)

            result[deal_id] = tranche_summaries

        return result

    async def get_available_cycles(self) -> List[Dict[str, str]]:
        """Get available cycle codes from the cycles table or historical data."""
        try:
            # Use the cycle methods from the DWDao class
            return await self.dw_dao.get_available_cycles()

        except Exception as e:
            # Fallback to dummy data if there's an issue with cycles table
            print(f"Warning: Could not fetch cycle data from data warehouse: {e}")
            dummy_cycles = [
                {"code": "2024Q4", "label": "2024Q4 (Quarter 4 2024)"},
                {"code": "2025Q1", "label": "2025Q1 (Quarter 1 2025)"},
            ]
            return dummy_cycles
