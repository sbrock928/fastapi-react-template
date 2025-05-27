"""Service layer for the reporting module."""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from decimal import Decimal

from app.reporting.dao import ReportDAO
from app.reporting.models import Report
from app.reporting.schemas import ReportRead, ReportCreate, ReportUpdate, ReportSummary, ReportScope
from app.datawarehouse.dao import DealDAO, TrancheDAO
from app.datawarehouse.schemas import DealRead, TrancheRead


def collect_validation_errors() -> Dict:
    """Helper function to collect multiple validation errors."""
    errors = []

    def add_error(field: str, msg: str, error_type: str = "value_error") -> None:
        errors.append({"loc": ["body", field], "msg": msg, "type": error_type})

    def has_errors() -> bool:
        return len(errors) > 0

    def raise_if_errors() -> Any:
        if errors:
            raise HTTPException(status_code=422, detail=errors)

    return {
        "add": add_error,
        "has_errors": has_errors,
        "raise_if_errors": raise_if_errors,
    }


class ReportService:
    """Service for managing report configurations and coordinating with data warehouse."""

    def __init__(self, report_dao: ReportDAO, deal_dao: DealDAO, tranche_dao: TrancheDAO):
        self.report_dao = report_dao
        self.deal_dao = deal_dao
        self.tranche_dao = tranche_dao

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
            deal_count = len(report.selected_deals) if report.selected_deals else 0
            tranche_count = 0
            if report.selected_tranches:
                tranche_count = sum(len(tranches) for tranches in report.selected_tranches.values())

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

    async def before_create(self, report_data: ReportCreate) -> ReportCreate:
        """Custom validation before report creation."""
        errors = collect_validation_errors()

        # Check if report name already exists (across all users)
        existing_reports = await self.report_dao.get_all()
        if any(r.name == report_data.name for r in existing_reports):
            errors["add"]("name", "Report name already exists", "value_error.already_exists")

        # Validate that selected deals exist in data warehouse using DWDao methods
        if report_data.selected_deals:
            # Use the parent class get_by_ids method to validate deal existence
            existing_deals = await self.deal_dao.get_by_ids(report_data.selected_deals)
            existing_deal_ids = {deal.id for deal in existing_deals}
            missing_deal_ids = set(report_data.selected_deals) - existing_deal_ids
            
            if missing_deal_ids:
                errors["add"](
                    "selected_deals", 
                    f"Deal IDs not found: {sorted(missing_deal_ids)}"
                )

        # For tranche-level reports, validate tranche selections
        if report_data.scope == ReportScope.TRANCHE:
            if not report_data.selected_tranches or not any(report_data.selected_tranches.values()):
                errors["add"](
                    "selected_tranches", "Tranche-level reports must have tranche selections"
                )

            # Validate that tranche deal IDs match selected deals
            if report_data.selected_tranches:
                tranche_deal_ids = set(
                    int(deal_id) for deal_id in report_data.selected_tranches.keys()
                )
                if not tranche_deal_ids.issubset(set(report_data.selected_deals)):
                    errors["add"](
                        "selected_tranches",
                        "Tranche selections contain deals not in selected deals",
                    )

                # Validate that selected tranches exist using DWDao methods
                for deal_id_str, tranche_ids in report_data.selected_tranches.items():
                    existing_tranches = await self.tranche_dao.get_by_ids(tranche_ids)
                    existing_tranche_ids = {tranche.id for tranche in existing_tranches}
                    missing_tranche_ids = set(tranche_ids) - existing_tranche_ids
                    
                    if missing_tranche_ids:
                        errors["add"](
                            "selected_tranches",
                            f"Tranche IDs not found for deal {deal_id_str}: {sorted(missing_tranche_ids)}"
                        )

        errors["raise_if_errors"]()
        return report_data

    async def before_update(self, report_id: int, report_data: ReportUpdate) -> ReportUpdate:
        """Custom validation before report update."""
        errors = collect_validation_errors()

        # Get current report
        current_report = await self.report_dao.get_by_id(report_id)
        if not current_report:
            raise HTTPException(status_code=404, detail="Report not found")

        # Check if name already exists (if changed)
        if report_data.name and current_report.name != report_data.name:
            existing_report = await self.report_dao.get_by_name_and_creator(
                report_data.name, current_report.created_by
            )
            if existing_report:
                errors["add"]("name", "Report name already exists", "value_error.already_exists")

        errors["raise_if_errors"]()
        return report_data

    async def create(self, report_data: ReportCreate) -> ReportRead:
        """Create a new report."""
        # Validate report data before creation
        await self.before_create(report_data)

        report = Report(
            name=report_data.name,
            scope=report_data.scope.value,
            created_by=report_data.created_by,
            selected_deals=report_data.selected_deals,
            selected_tranches=report_data.selected_tranches,
            is_active=report_data.is_active,
        )
        created_report = await self.report_dao.create(report)
        return ReportRead.model_validate(created_report)

    async def update(self, report_id: int, report_data: ReportUpdate) -> Optional[ReportRead]:
        """Update a report."""
        # Validate report data before update
        await self.before_update(report_id, report_data)

        report = await self.report_dao.get_by_id(report_id)
        if not report:
            return None

        update_data = report_data.model_dump(exclude_unset=True)

        # Handle scope enum conversion
        if "scope" in update_data and update_data["scope"]:
            update_data["scope"] = update_data["scope"].value

        for field, value in update_data.items():
            setattr(report, field, value)

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

        # 2. Query data warehouse using stored IDs and DWDao parent class methods
        results = []

        if report.scope == "DEAL":
            # Deal-level report: one row per deal with aggregated data
            if report.selected_deals:
                # Use DWDao parent class method with cycle filtering
                deals = await self.deal_dao.get_by_ids(report.selected_deals, cycle_code)

                for deal in deals:
                    # Get tranches for aggregation using DWDao method
                    tranches = await self.tranche_dao.get_by_deal_id(deal.id, cycle_code)

                    # Calculate aggregated metrics
                    total_tranche_principal = sum(float(t.principal_amount) for t in tranches)
                    avg_interest_rate = (
                        sum(float(t.interest_rate) for t in tranches) / len(tranches)
                        if tranches
                        else 0
                    )
                    tranche_count = len(tranches)

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
                        "cycle_code": deal.cycle_code,
                        # Aggregated tranche data
                        "tranche_count": tranche_count,
                        "total_tranche_principal": total_tranche_principal,
                        "avg_tranche_interest_rate": avg_interest_rate,
                    }
                    results.append(result_row)

        else:  # TRANCHE level
            # Tranche-level report: one row per selected tranche
            if report.selected_tranches:
                for deal_id_str, tranche_ids in report.selected_tranches.items():
                    deal_id = int(deal_id_str)

                    # Get deal info for context using DWDao method
                    deal = await self.deal_dao.get_by_id_and_cycle(deal_id, cycle_code)
                    if not deal:
                        continue

                    # Get selected tranches using DWDao method with cycle filtering
                    tranches = await self.tranche_dao.get_by_ids(tranche_ids, cycle_code)

                    for tranche in tranches:
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
                            "principal_amount": float(tranche.principal_amount),
                            "interest_rate": float(tranche.interest_rate),
                            "credit_rating": tranche.credit_rating,
                            "payment_priority": tranche.payment_priority,
                            "maturity_date": (
                                tranche.maturity_date.isoformat() if tranche.maturity_date else None
                            ),
                            "cycle_code": tranche.cycle_code,
                        }
                        results.append(result_row)

        return results

    async def get_available_deals(self, cycle_code: Optional[str] = None) -> List[DealRead]:
        """Get available deals for report building using DWDao method."""
        # Use the parent class get_all method with optional cycle filtering
        deals = await self.deal_dao.get_all(cycle_code)
        return [DealRead.model_validate(deal) for deal in deals]

    async def get_available_tranches_for_deals(
        self, deal_ids: List[int], cycle_code: Optional[str] = None
    ) -> Dict[int, List[TrancheRead]]:
        """Get available tranches for specific deals using DWDao methods."""
        result = {}

        for deal_id in deal_ids:
            # Use the TrancheDAO specific method (which is built on DWDao base)
            tranches = await self.tranche_dao.get_by_deal_id(deal_id, cycle_code)
            result[deal_id] = [TrancheRead.model_validate(tranche) for tranche in tranches]

        return result

    async def get_available_cycles(self) -> List[Dict[str, str]]:
        """Get available cycle codes from the cycles table in the data warehouse.

        Now uses the cycle methods available in the base DWDao class.
        Can use either deal_dao or tranche_dao since both inherit the cycle methods.
        """
        try:
            # Use the cycle methods from the base DWDao class (available on any DAO instance)
            return await self.deal_dao.get_available_cycles()
            
        except Exception as e:
            # Fallback to dummy data if there's an issue with cycles table
            print(f"Warning: Could not fetch cycle data from data warehouse: {e}")
            return await self.report_dao.get_available_cycles()
