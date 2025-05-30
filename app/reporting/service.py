# filepath: c:\Users\steph\fastapi-react-template\app\reporting\service.py
"""Service layer for the reporting module."""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from decimal import Decimal
from pydantic import ValidationError

from app.reporting.dao import ReportDAO
from app.reporting.models import Report, ReportDeal, ReportTranche, ReportField
from app.reporting.schemas import (
    ReportRead, ReportCreate, ReportUpdate, ReportSummary, ReportScope,
    ReportDealCreate, ReportTrancheCreate, ReportFieldCreate, AvailableField, FieldType
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

    async def get_available_fields(self, scope: ReportScope) -> List[AvailableField]:
        """Get available fields for report configuration based on scope."""
        fields = []
        
        if scope == ReportScope.DEAL:
            # Deal-level fields
            fields.extend([
                AvailableField(
                    field_name="dl_nbr",
                    display_name="Deal Number",
                    field_type=FieldType.NUMBER,
                    description="Unique deal identifier",
                    scope=scope,
                    category="Deal",
                    is_default=True
                ),
                AvailableField(
                    field_name="issr_cde",
                    display_name="Issuer Code",
                    field_type=FieldType.TEXT,
                    description="Issuer identification code",
                    scope=scope,
                    category="Deal",
                    is_default=True
                ),
                AvailableField(
                    field_name="cdi_file_nme",
                    display_name="CDI File Name",
                    field_type=FieldType.TEXT,
                    description="CDI file name for the deal",
                    scope=scope,
                    category="Deal",
                    is_default=True
                ),
                AvailableField(
                    field_name="CDB_cdi_file_nme",
                    display_name="CDB CDI File Name",
                    field_type=FieldType.TEXT,
                    description="CDB CDI file name for the deal",
                    scope=scope,
                    category="Deal",
                    is_default=False
                ),
                AvailableField(
                    field_name="tranche_count",
                    display_name="Tranche Count",
                    field_type=FieldType.NUMBER,
                    description="Number of tranches in the deal",
                    scope=scope,
                    category="Aggregated",
                    is_default=True
                )
            ])
            
        elif scope == ReportScope.TRANCHE:
            # Tranche-level fields include deal fields plus tranche-specific fields
            fields.extend([
                # Deal information
                AvailableField(
                    field_name="dl_nbr",
                    display_name="Deal Number",
                    field_type=FieldType.NUMBER,
                    description="Deal number for this tranche",
                    scope=scope,
                    category="Deal",
                    is_default=True
                ),
                AvailableField(
                    field_name="deal_issr_cde",
                    display_name="Deal Issuer Code",
                    field_type=FieldType.TEXT,
                    description="Issuer code for the deal",
                    scope=scope,
                    category="Deal",
                    is_default=True
                ),
                AvailableField(
                    field_name="deal_cdi_file_nme",
                    display_name="Deal CDI File Name",
                    field_type=FieldType.TEXT,
                    description="CDI file name for the deal",
                    scope=scope,
                    category="Deal",
                    is_default=True
                ),
                AvailableField(
                    field_name="deal_CDB_cdi_file_nme",
                    display_name="Deal CDB CDI File Name",
                    field_type=FieldType.TEXT,
                    description="CDB CDI file name for the deal",
                    scope=scope,
                    category="Deal",
                    is_default=False
                ),
                # Tranche information
                AvailableField(
                    field_name="tr_id",
                    display_name="Tranche ID",
                    field_type=FieldType.TEXT,
                    description="Tranche identifier",
                    scope=scope,
                    category="Tranche",
                    is_default=True
                ),
                # Cycle data (from TrancheBal) - these would be available when cycle is selected
                AvailableField(
                    field_name="cycle_date",
                    display_name="Cycle Date",
                    field_type=FieldType.DATE,
                    description="Cycle date for the data",
                    scope=scope,
                    category="Cycle Data",
                    is_default=False
                )
            ])
        
        return fields

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

        # Validate field selections
        if hasattr(report_data, 'selected_fields') and report_data.selected_fields:
            if hasattr(report_data, 'scope') and report_data.scope:
                available_fields = await self.get_available_fields(report_data.scope)
                available_field_names = {field.field_name for field in available_fields}
                
                selected_field_names = {field.field_name for field in report_data.selected_fields}
                invalid_fields = selected_field_names - available_field_names
                
                if invalid_fields:
                    errors.append(f"Invalid field names for {report_data.scope} scope: {sorted(invalid_fields)}")

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
            field_count = len(report.selected_fields)

            summary = ReportSummary(
                id=report.id,
                name=report.name,
                scope=ReportScope(report.scope),
                created_by=report.created_by or "system",
                created_date=report.created_date,
                deal_count=deal_count,
                tranche_count=tranche_count,
                field_count=field_count,
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
        report = Report(**{k: v for k, v in report_dict.items() if k not in ['selected_deals', 'selected_fields']})
        
        # Add deals and tranches
        self._populate_deals_and_tranches(report, report_data.selected_deals)
        
        # Add fields
        self._populate_fields(report, report_data.selected_fields)
        
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
        update_data = report_data.model_dump(exclude_unset=True, exclude={'selected_deals', 'selected_fields'})
        
        # Handle scope enum conversion
        if "scope" in update_data and update_data["scope"]:
            update_data["scope"] = update_data["scope"].value

        for field, value in update_data.items():
            setattr(report, field, value)

        # Handle deals and tranches update if provided
        if report_data.selected_deals is not None:
            report.selected_deals.clear()
            self._populate_deals_and_tranches(report, report_data.selected_deals)

        # Handle fields update if provided
        if report_data.selected_fields is not None:
            report.selected_fields.clear()
            self._populate_fields(report, report_data.selected_fields)

        updated_report = await self.report_dao.update(report)
        return ReportRead.model_validate(updated_report)

    async def delete(self, report_id: int) -> bool:
        """Delete a report."""
        return await self.report_dao.delete(report_id)

    async def run_saved_report(self, report_id: int, cycle_code: int) -> List[Dict[str, Any]]:
        """Run a saved report by fetching config and querying data warehouse."""
        report = await self._get_validated_report(report_id)
        
        if report.scope == "DEAL":
            return await self._run_deal_level_report(report, cycle_code)
        else:
            return await self._run_tranche_level_report(report, cycle_code)

    async def _get_validated_report(self, report_id: int) -> Report:
        """Get and validate report configuration."""
        report = await self.report_dao.get_by_id(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        if not report.is_active:
            raise HTTPException(status_code=400, detail="Report is inactive")
        return report

    async def _run_deal_level_report(self, report: Report, cycle_code: int) -> List[Dict[str, Any]]:
        """Generate deal-level report with dynamic field selection."""
        results = []
        selected_field_names = [field.field_name for field in report.selected_fields]
        
        for report_deal in report.selected_deals:
            deal_data = await self._get_deal_data_with_fields(report_deal.dl_nbr, selected_field_names)
            if deal_data:
                results.append(deal_data)
        return results

    async def _run_tranche_level_report(self, report: Report, cycle_code: int) -> List[Dict[str, Any]]:
        """Generate tranche-level report with dynamic field selection."""
        results = []
        selected_field_names = [field.field_name for field in report.selected_fields]
        
        for report_deal in report.selected_deals:
            deal = self.dw_dao.get_deal_by_dl_nbr(report_deal.dl_nbr)
            if not deal:
                continue
                
            for report_tranche in report_deal.selected_tranches:
                tranche_data = await self._get_tranche_data_with_fields(
                    deal, report_tranche.dl_nbr, report_tranche.tr_id, selected_field_names, cycle_code
                )
                if tranche_data:
                    results.append(tranche_data)
        return results

    async def _get_deal_data_with_fields(self, dl_nbr: int, selected_fields: List[str]) -> Optional[Dict[str, Any]]:
        """Get deal data with only selected fields."""
        deal = self.dw_dao.get_deal_by_dl_nbr(dl_nbr)
        if not deal:
            return None

        # Build the result dict with only selected fields
        result = {}
        
        # Available deal fields
        available_data = {
            "dl_nbr": deal.dl_nbr,
            "issr_cde": deal.issr_cde,
            "cdi_file_nme": deal.cdi_file_nme,
            "CDB_cdi_file_nme": deal.CDB_cdi_file_nme,
        }
        
        # Add tranche count if requested
        if "tranche_count" in selected_fields:
            tranches = self.dw_dao.get_tranches_by_dl_nbr(dl_nbr)
            available_data["tranche_count"] = len(tranches)
        
        # Only include requested fields
        for field_name in selected_fields:
            if field_name in available_data:
                result[field_name] = available_data[field_name]
                
        return result

    async def _get_tranche_data_with_fields(
        self, deal, dl_nbr: int, tr_id: str, selected_fields: List[str], cycle_code: int
    ) -> Optional[Dict[str, Any]]:
        """Get tranche data with only selected fields."""
        tranche = self.dw_dao.get_tranche_by_keys(dl_nbr, tr_id)
        if not tranche:
            return None
        
        # Build the result dict with only selected fields
        result = {}
        
        # Available tranche fields
        available_data = {
            "dl_nbr": deal.dl_nbr,
            "deal_issr_cde": deal.issr_cde,
            "deal_cdi_file_nme": deal.cdi_file_nme,
            "deal_CDB_cdi_file_nme": deal.CDB_cdi_file_nme,
            "tr_id": tranche.tr_id,
        }
        
        # Add cycle data if requested
        if "cycle_date" in selected_fields:
            # Get cycle data from TrancheBal
            tranche_bal = self.dw_dao.get_tranchebal_by_keys(dl_nbr, tr_id, cycle_code)
            if tranche_bal:
                available_data["cycle_date"] = tranche_bal.cycle_date
        
        # Only include requested fields
        for field_name in selected_fields:
            if field_name in available_data:
                result[field_name] = available_data[field_name]
                
        return result

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
            result[str(dl_nbr)] = self._get_tranche_summaries_for_deal(dl_nbr)
        return result

    def _get_tranche_summaries_for_deal(self, dl_nbr: int) -> List[Dict[str, Any]]:
        """Get tranche summaries for a specific deal."""
        tranches = self.dw_dao.get_tranches_by_dl_nbr(dl_nbr)
        deal = self.dw_dao.get_deal_by_dl_nbr(dl_nbr)
        deal_info = deal.issr_cde if deal else "Unknown Deal"

        tranche_summaries = []
        for tranche in tranches:
            summary = {
                "dl_nbr": tranche.dl_nbr,
                "tr_id": tranche.tr_id,
                "deal_issr_cde": deal_info,
            }
            tranche_summaries.append(summary)
        
        return tranche_summaries

    async def get_available_cycles(self) -> List[Dict[str, Any]]:
        """Get available cycle codes from the data warehouse."""
        try:
            return self.dw_dao.get_available_cycles()
        except Exception as e:
            # Fallback to empty data
            print(f"Warning: Could not fetch cycle data from data warehouse: {e}")
            return []

    def _populate_deals_and_tranches(self, report: Report, selected_deals_data: List) -> None:
        """Helper method to populate deals and tranches for a report."""
        for deal_data in selected_deals_data:
            report_deal = ReportDeal(dl_nbr=deal_data.dl_nbr)
            
            for tranche_data in deal_data.selected_tranches:
                report_tranche = ReportTranche(dl_nbr=tranche_data.dl_nbr, tr_id=tranche_data.tr_id)
                report_deal.selected_tranches.append(report_tranche)
            
            report.selected_deals.append(report_deal)

    def _populate_fields(self, report: Report, selected_fields_data: List) -> None:
        """Helper method to populate fields for a report."""
        for field_data in selected_fields_data:
            report_field = ReportField(
                field_name=field_data.field_name,
                display_name=field_data.display_name,
                field_type=field_data.field_type.value,
                is_required=field_data.is_required
            )
            report.selected_fields.append(report_field)
