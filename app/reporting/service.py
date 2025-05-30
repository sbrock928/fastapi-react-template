# filepath: c:\Users\steph\fastapi-react-template\app\reporting\service.py
"""Service layer for the reporting module."""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from decimal import Decimal
from pydantic import ValidationError

from app.reporting.dao import ReportDAO
from app.reporting.models import Report, ReportDeal, ReportTranche, ReportField, FilterCondition
from app.reporting.schemas import (
    ReportRead, ReportCreate, ReportUpdate, ReportSummary, ReportScope,
    ReportDealCreate, ReportTrancheCreate, ReportFieldCreate, AvailableField, FieldType,
    FilterConditionCreate, FilterOperator
)
from app.datawarehouse.dao import DatawarehouseDAO
from app.datawarehouse.models import Deal
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
                    field_name="cycle_cde",  # Changed from cycle_date to cycle_cde
                    display_name="Cycle Code",  # Changed from "Cycle Date" to "Cycle Code"
                    field_type=FieldType.NUMBER,  # Changed from DATE to NUMBER
                    description="Cycle code for the data",  # Updated description
                    scope=scope,
                    category="Cycle Data",
                    is_default=False
                ),
                # New TrancheBal fields
                AvailableField(
                    field_name="tr_end_bal_amt",
                    display_name="Ending Balance Amount",
                    field_type=FieldType.NUMBER,
                    description="Tranche ending balance amount",
                    scope=scope,
                    category="Cycle Data",
                    is_default=True
                ),
                AvailableField(
                    field_name="tr_prin_rel_ls_amt",
                    display_name="Principal Release Loss Amount",
                    field_type=FieldType.NUMBER,
                    description="Tranche principal release loss amount",
                    scope=scope,
                    category="Cycle Data",
                    is_default=False
                ),
                AvailableField(
                    field_name="tr_pass_thru_rte",
                    display_name="Pass-Through Rate",
                    field_type=FieldType.PERCENTAGE,
                    description="Tranche pass-through rate",
                    scope=scope,
                    category="Cycle Data",
                    is_default=True
                ),
                AvailableField(
                    field_name="tr_accrl_days",
                    display_name="Accrual Days",
                    field_type=FieldType.NUMBER,
                    description="Tranche accrual days",
                    scope=scope,
                    category="Cycle Data",
                    is_default=False
                ),
                AvailableField(
                    field_name="tr_int_dstrb_amt",
                    display_name="Interest Distribution Amount",
                    field_type=FieldType.NUMBER,
                    description="Tranche interest distribution amount",
                    scope=scope,
                    category="Cycle Data",
                    is_default=True
                ),
                AvailableField(
                    field_name="tr_prin_dstrb_amt",
                    display_name="Principal Distribution Amount",
                    field_type=FieldType.NUMBER,
                    description="Tranche principal distribution amount",
                    scope=scope,
                    category="Cycle Data",
                    is_default=True
                ),
                AvailableField(
                    field_name="tr_int_accrl_amt",
                    display_name="Interest Accrual Amount",
                    field_type=FieldType.NUMBER,
                    description="Tranche interest accrual amount",
                    scope=scope,
                    category="Cycle Data",
                    is_default=False
                ),
                AvailableField(
                    field_name="tr_int_shtfl_amt",
                    display_name="Interest Shortfall Amount",
                    field_type=FieldType.NUMBER,
                    description="Tranche interest shortfall amount",
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
        report = Report(**{k: v for k, v in report_dict.items() if k not in ['selected_deals', 'selected_fields', 'filter_conditions']})
        
        # Add deals and tranches
        self._populate_deals_and_tranches(report, report_data.selected_deals)
        
        # Add fields
        self._populate_fields(report, report_data.selected_fields)
        
        # Add filter conditions
        self._populate_filter_conditions(report, report_data.filter_conditions)
        
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
        update_data = report_data.model_dump(exclude_unset=True, exclude={'selected_deals', 'selected_fields', 'filter_conditions'})
        
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

        # Handle filter conditions update if provided
        if report_data.filter_conditions is not None:
            report.filter_conditions.clear()
            self._populate_filter_conditions(report, report_data.filter_conditions)

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

    async def get_report_schema(self, report_id: int) -> Dict[str, Any]:
        """Get the schema/structure of a saved report for skeleton preview."""
        report = await self._get_validated_report(report_id)
        
        # Get selected fields to determine columns
        selected_field_names = [field.field_name for field in report.selected_fields]
        
        # Generate skeleton data based on field types
        columns = []
        skeleton_row = {}
        
        # Get available fields to determine data types
        available_fields = await self.get_available_fields(ReportScope(report.scope))
        field_type_map = {field.field_name: field for field in available_fields}
        
        for field_name in selected_field_names:
            field_info = field_type_map.get(field_name)
            if field_info:
                # Create column definition
                column = {
                    "field": field_name,
                    "header": field_info.display_name,
                    "type": field_info.field_type.value
                }
                columns.append(column)
                
                # Generate skeleton value based on field type
                skeleton_row[field_name] = self._generate_skeleton_value(field_info.field_type, field_info.display_name)
        
        return {
            "title": f"{report.name} (Preview)",
            "scope": report.scope,
            "columns": columns,
            "skeleton_data": [skeleton_row],  # Single row for preview
            "deal_count": len(report.selected_deals),
            "tranche_count": sum(len(deal.selected_tranches) for deal in report.selected_deals),
            "field_count": len(report.selected_fields)
        }

    def _generate_skeleton_value(self, field_type: FieldType, display_name: str) -> str:
        """Generate a skeleton value based on field type to show expected data format."""
        if field_type == FieldType.NUMBER:
            if "amount" in display_name.lower() or "balance" in display_name.lower():
                return "123,456.78"
            elif "count" in display_name.lower():
                return "42"
            elif "days" in display_name.lower():
                return "30"
            else:
                return "12345"
        elif field_type == FieldType.PERCENTAGE:
            return "5.25%"
        elif field_type == FieldType.DATE:
            return "2024-12-31"
        elif field_type == FieldType.TEXT:
            if "code" in display_name.lower():
                return "ABC123"
            elif "file" in display_name.lower() and "name" in display_name.lower():
                return "sample_file.csv"
            elif "id" in display_name.lower():
                return "TR001"
            else:
                return "Sample Text"
        else:
            return f"({field_type.value})"

    async def get_available_cycles(self) -> List[Dict[str, Any]]:
        """Get available cycle codes from the data warehouse."""
        try:
            return self.dw_dao.get_available_cycles()
        except Exception as e:
            # Fallback to empty data
            print(f"Warning: Could not fetch cycle data from data warehouse: {e}")
            return []

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

    async def _get_validated_report(self, report_id: int) -> Report:
        """Get and validate report configuration."""
        report = await self.report_dao.get_by_id(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        if not report.is_active:
            raise HTTPException(status_code=400, detail="Report is inactive")
        return report

    async def _run_deal_level_report(self, report: Report, cycle_code: int) -> List[Dict[str, Any]]:
        """Generate deal-level report with dynamic field selection and filtering."""
        results = []
        selected_field_names = [field.field_name for field in report.selected_fields]
        filter_conditions = report.filter_conditions
        
        for report_deal in report.selected_deals:
            deal_data = await self._get_deal_data_with_fields(report_deal.dl_nbr, selected_field_names)
            if deal_data and self._apply_filters(deal_data, filter_conditions):
                results.append(deal_data)
        return results

    async def _run_tranche_level_report(self, report: Report, cycle_code: int) -> List[Dict[str, Any]]:
        """Generate tranche-level report with dynamic field selection and filtering."""
        results = []
        selected_field_names = [field.field_name for field in report.selected_fields]
        filter_conditions = report.filter_conditions
        
        for report_deal in report.selected_deals:
            deal = self.dw_dao.get_deal_by_dl_nbr(report_deal.dl_nbr)
            if not deal:
                continue
                
            for report_tranche in report_deal.selected_tranches:
                tranche_data = await self._get_tranche_data_with_fields(
                    deal, report_tranche.dl_nbr, report_tranche.tr_id, selected_field_names, cycle_code
                )
                if tranche_data and self._apply_filters(tranche_data, filter_conditions):
                    results.append(tranche_data)
        return results

    def _apply_filters(self, data_row: Dict[str, Any], filter_conditions: List[FilterCondition]) -> bool:
        """Apply filter conditions to a data row. Returns True if the row passes all filters."""
        if not filter_conditions:
            return True
            
        for condition in filter_conditions:
            if not self._evaluate_filter_condition(data_row, condition):
                return False
        return True

    def _evaluate_filter_condition(self, data_row: Dict[str, Any], condition: FilterCondition) -> bool:
        """Evaluate a single filter condition against a data row."""
        field_value = data_row.get(condition.field_name)
        operator = FilterOperator(condition.operator)
        filter_value = condition.value
        
        # Handle null checks first
        if operator == FilterOperator.IS_NULL:
            return field_value is None
        elif operator == FilterOperator.IS_NOT_NULL:
            return field_value is not None
            
        # If field value is None and we're not checking for null, condition fails
        if field_value is None:
            return False
            
        # Convert values for comparison
        try:
            # Convert filter value to string for parsing
            if filter_value is not None:
                filter_value_str = str(filter_value)
            else:
                filter_value_str = ""
                
            # Numeric comparisons
            if operator in [FilterOperator.GREATER_THAN, FilterOperator.LESS_THAN, 
                          FilterOperator.GREATER_THAN_OR_EQUAL, FilterOperator.LESS_THAN_OR_EQUAL]:
                field_num = float(field_value) if field_value is not None else 0
                filter_num = float(filter_value_str) if filter_value_str else 0
                
                if operator == FilterOperator.GREATER_THAN:
                    return field_num > filter_num
                elif operator == FilterOperator.LESS_THAN:
                    return field_num < filter_num
                elif operator == FilterOperator.GREATER_THAN_OR_EQUAL:
                    return field_num >= filter_num
                elif operator == FilterOperator.LESS_THAN_OR_EQUAL:
                    return field_num <= filter_num
                    
            # String operations (case-insensitive)
            field_str = str(field_value).lower() if field_value is not None else ""
            filter_str = filter_value_str.lower()
            
            if operator == FilterOperator.EQUALS:
                return field_str == filter_str
            elif operator == FilterOperator.NOT_EQUALS:
                return field_str != filter_str
            elif operator == FilterOperator.CONTAINS:
                return filter_str in field_str
            elif operator == FilterOperator.NOT_CONTAINS:
                return filter_str not in field_str
            elif operator == FilterOperator.STARTS_WITH:
                return field_str.startswith(filter_str)
            elif operator == FilterOperator.ENDS_WITH:
                return field_str.endswith(filter_str)
            elif operator == FilterOperator.IN:
                # filter_value should be a list for IN operator
                if isinstance(filter_value, list):
                    return field_str in [str(v).lower() for v in filter_value]
                return False
            elif operator == FilterOperator.NOT_IN:
                # filter_value should be a list for NOT_IN operator
                if isinstance(filter_value, list):
                    return field_str not in [str(v).lower() for v in filter_value]
                return True
                
        except (ValueError, TypeError):
            # If conversion fails, return False for safety
            return False
            
        return False

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

    def _populate_filter_conditions(self, report: Report, filter_conditions_data: List) -> None:
        """Helper method to populate filter conditions for a report."""
        for condition_data in filter_conditions_data:
            filter_condition = FilterCondition(
                field_name=condition_data.field_name,
                operator=condition_data.operator,
                value=condition_data.value
            )
            report.filter_conditions.append(filter_condition)

    async def _get_deal_data_with_fields(self, dl_nbr: int, selected_field_names: List[str]) -> Optional[Dict[str, Any]]:
        """Get deal data with only the selected fields."""
        deal = self.dw_dao.get_deal_by_dl_nbr(dl_nbr)
        if not deal:
            return None
        
        deal_data = {}
        
        for field_name in selected_field_names:
            if field_name == "dl_nbr":
                deal_data["dl_nbr"] = deal.dl_nbr
            elif field_name == "issr_cde":
                deal_data["issr_cde"] = deal.issr_cde
            elif field_name == "cdi_file_nme":
                deal_data["cdi_file_nme"] = deal.cdi_file_nme
            elif field_name == "CDB_cdi_file_nme":
                deal_data["CDB_cdi_file_nme"] = deal.CDB_cdi_file_nme
            elif field_name == "tranche_count":
                # Calculate tranche count for aggregated field
                tranches = self.dw_dao.get_tranches_by_dl_nbr(dl_nbr)
                deal_data["tranche_count"] = len(tranches)
        
        return deal_data

    async def _get_tranche_data_with_fields(
        self, 
        deal: Deal, 
        dl_nbr: int, 
        tr_id: str, 
        selected_field_names: List[str], 
        cycle_code: int
    ) -> Optional[Dict[str, Any]]:
        """Get tranche data with only the selected fields."""
        tranche = self.dw_dao.get_tranche_by_keys(dl_nbr, tr_id)
        if not tranche:
            return None
        
        tranche_data = {}
        
        for field_name in selected_field_names:
            # Deal-level fields
            if field_name == "dl_nbr":
                tranche_data["dl_nbr"] = deal.dl_nbr
            elif field_name == "deal_issr_cde":
                tranche_data["deal_issr_cde"] = deal.issr_cde
            elif field_name == "deal_cdi_file_nme":
                tranche_data["deal_cdi_file_nme"] = deal.cdi_file_nme
            elif field_name == "deal_CDB_cdi_file_nme":
                tranche_data["deal_CDB_cdi_file_nme"] = deal.CDB_cdi_file_nme
            # Tranche-level fields
            elif field_name == "tr_id":
                tranche_data["tr_id"] = tranche.tr_id
            elif field_name == "cycle_cde":
                # Get cycle data if requested
                tranche_bal = self.dw_dao.get_tranchebal_by_keys(dl_nbr, tr_id)
                if tranche_bal:
                    tranche_data["cycle_cde"] = tranche_bal.cycle_cde
                else:
                    tranche_data["cycle_cde"] = None
            elif field_name == "tr_end_bal_amt":
                # Get tranche ending balance amount
                tranche_bal = self.dw_dao.get_tranchebal_by_keys(dl_nbr, tr_id)
                if tranche_bal:
                    tranche_data["tr_end_bal_amt"] = tranche_bal.tr_end_bal_amt
                else:
                    tranche_data["tr_end_bal_amt"] = None
            elif field_name == "tr_prin_rel_ls_amt":
                # Get tranche principal release loss amount
                tranche_bal = self.dw_dao.get_tranchebal_by_keys(dl_nbr, tr_id)
                if tranche_bal:
                    tranche_data["tr_prin_rel_ls_amt"] = tranche_bal.tr_prin_rel_ls_amt
                else:
                    tranche_data["tr_prin_rel_ls_amt"] = None
            elif field_name == "tr_pass_thru_rte":
                # Get tranche pass-through rate
                tranche_bal = self.dw_dao.get_tranchebal_by_keys(dl_nbr, tr_id)
                if tranche_bal:
                    tranche_data["tr_pass_thru_rte"] = tranche_bal.tr_pass_thru_rte
                else:
                    tranche_data["tr_pass_thru_rte"] = None
            elif field_name == "tr_accrl_days":
                # Get tranche accrual days
                tranche_bal = self.dw_dao.get_tranchebal_by_keys(dl_nbr, tr_id)
                if tranche_bal:
                    tranche_data["tr_accrl_days"] = tranche_bal.tr_accrl_days
                else:
                    tranche_data["tr_accrl_days"] = None
            elif field_name == "tr_int_dstrb_amt":
                # Get tranche interest distribution amount
                tranche_bal = self.dw_dao.get_tranchebal_by_keys(dl_nbr, tr_id)
                if tranche_bal:
                    tranche_data["tr_int_dstrb_amt"] = tranche_bal.tr_int_dstrb_amt
                else:
                    tranche_data["tr_int_dstrb_amt"] = None
            elif field_name == "tr_prin_dstrb_amt":
                # Get tranche principal distribution amount
                tranche_bal = self.dw_dao.get_tranchebal_by_keys(dl_nbr, tr_id)
                if tranche_bal:
                    tranche_data["tr_prin_dstrb_amt"] = tranche_bal.tr_prin_dstrb_amt
                else:
                    tranche_data["tr_prin_dstrb_amt"] = None
            elif field_name == "tr_int_accrl_amt":
                # Get tranche interest accrual amount
                tranche_bal = self.dw_dao.get_tranchebal_by_keys(dl_nbr, tr_id)
                if tranche_bal:
                    tranche_data["tr_int_accrl_amt"] = tranche_bal.tr_int_accrl_amt
                else:
                    tranche_data["tr_int_accrl_amt"] = None
            elif field_name == "tr_int_shtfl_amt":
                # Get tranche interest shortfall amount
                tranche_bal = self.dw_dao.get_tranchebal_by_keys(dl_nbr, tr_id)
                if tranche_bal:
                    tranche_data["tr_int_shtfl_amt"] = tranche_bal.tr_int_shtfl_amt
                else:
                    tranche_data["tr_int_shtfl_amt"] = None
        
        return tranche_data
