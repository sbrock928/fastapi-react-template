"""Service layer for the reporting module - Updated for calculation-based reporting."""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from decimal import Decimal
from pydantic import ValidationError

from app.reporting.dao import ReportDAO
from app.reporting.models import Report, ReportDeal, ReportTranche, ReportCalculation
from app.reporting.schemas import (
    ReportRead, ReportCreate, ReportUpdate, ReportSummary, ReportScope,
    ReportDealCreate, ReportTrancheCreate, ReportCalculationCreate, AvailableCalculation
)
from app.datawarehouse.dao import DatawarehouseDAO
from app.datawarehouse.schemas import DealRead, TrancheRead
from app.calculations.dao import CalculationDAO
from app.calculations.models import Calculation
from app.shared.query_engine import QueryEngine
import time


class ReportService:
    """Service for managing report configurations and coordinating with data warehouse."""

    def __init__(
        self,
        report_dao: ReportDAO,
        dw_dao: DatawarehouseDAO,
        query_engine: QueryEngine = None,
    ):
        self.report_dao = report_dao
        self.dw_dao = dw_dao
        self.query_engine = query_engine

    async def get_available_calculations(self, scope: ReportScope) -> List[AvailableCalculation]:
        """Get available calculations for report configuration based on scope, including auto-generated raw fields."""
        
        # Get manually defined calculations from the config database using query engine
        if not self.query_engine:
            raise HTTPException(status_code=500, detail="Query engine not available")
            
        calc_repo = CalculationDAO(self.query_engine.config_db)
        
        # Filter calculations by group level (deal/tranche) based on scope
        if scope == ReportScope.DEAL:
            manual_calculations = calc_repo.get_all_calculations(group_level="deal")
        else:
            manual_calculations = calc_repo.get_all_calculations(group_level="tranche")
        
        available_calculations = []
        
        # Add manually defined calculations (excluding RAW ones since we'll auto-generate them)
        for calc in manual_calculations:
            if calc.aggregation_function.value != "RAW":  # Skip manual RAW calculations
                category = self._get_calculation_category(calc)
                is_default = calc.name in ["Total Ending Balance", "Average Pass Through Rate"]
                
                available_calc = AvailableCalculation(
                    id=calc.id,
                    name=calc.name,
                    description=calc.description,
                    aggregation_function=calc.aggregation_function.value,
                    source_model=calc.source_model.value,
                    source_field=calc.source_field,
                    group_level=calc.group_level.value,
                    weight_field=calc.weight_field,
                    scope=scope,
                    category=category,
                    is_default=is_default
                )
                available_calculations.append(available_calc)
        
        # Auto-generate RAW field calculations based on model introspection
        auto_generated_fields = self._generate_auto_raw_fields(scope)
        available_calculations.extend(auto_generated_fields)
        
        return available_calculations

    def _get_calculation_category(self, calc: Calculation) -> str:
        """Determine the category for a calculation based on its properties."""
        source_model = calc.source_model.value
        source_field = calc.source_field
        
        if source_model == "Deal":
            return "Deal Information"
        elif source_model == "Tranche":
            return "Tranche Structure"
        elif source_model == "TrancheBal":
            if "bal" in source_field.lower():
                return "Balance Data"
            elif "rte" in source_field.lower() or "rate" in source_field.lower():
                return "Rate Data"
            elif "dstrb" in source_field.lower() or "distribution" in source_field.lower():
                return "Distribution Data"
            elif "accrl" in source_field.lower() or "accrual" in source_field.lower():
                return "Accrual Data"
            else:
                return "Performance Data"
        else:
            return "Other"

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
                    for tranche in deal.selected_tranches:
                        # Use tranche.dl_nbr if available, otherwise use deal.dl_nbr
                        tranche_dl_nbr = tranche.dl_nbr if tranche.dl_nbr is not None else deal.dl_nbr
                        all_tranche_keys.append((tranche_dl_nbr, tranche.tr_id))
                
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

        # Validate calculation selections
        if hasattr(report_data, 'selected_calculations') and report_data.selected_calculations:
            if self.query_engine:
                calc_repo = CalculationDAO(self.query_engine.config_db)
                calc_ids = [calc.calculation_id for calc in report_data.selected_calculations]
                
                # Separate real calculations from virtual auto-generated ones
                real_calc_ids = [calc_id for calc_id in calc_ids if calc_id < 10000]
                virtual_calc_ids = [calc_id for calc_id in calc_ids if calc_id >= 10000]
                
                # Validate real calculations exist in database
                existing_calculations = []
                for calc_id in real_calc_ids:
                    calc = calc_repo.get_by_id(calc_id)
                    if calc:
                        existing_calculations.append(calc)
                
                existing_calc_ids = {calc.id for calc in existing_calculations}
                missing_calc_ids = set(real_calc_ids) - existing_calc_ids
                
                if missing_calc_ids:
                    errors.append(f"Calculation IDs not found: {sorted(missing_calc_ids)}")
                
                # Validate virtual calculations by checking if they can be generated
                if virtual_calc_ids:
                    # Determine scope for virtual calculation validation
                    scope = getattr(report_data, 'scope', None)
                    if scope:
                        scope_enum = ReportScope.DEAL if scope == ReportScope.DEAL else ReportScope.TRANCHE
                        auto_fields = self._generate_auto_raw_fields(scope_enum)
                        valid_virtual_ids = {field.id for field in auto_fields}
                        
                        invalid_virtual_ids = set(virtual_calc_ids) - valid_virtual_ids
                        if invalid_virtual_ids:
                            errors.append(f"Invalid virtual calculation IDs: {sorted(invalid_virtual_ids)}")

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
        """Get all reports with summary information including execution statistics."""
        reports = await self.report_dao.get_all()
        summaries = []

        for report in reports:
            deal_count = len(report.selected_deals)
            
            # Calculate actual tranche count using smart tranche logic
            tranche_count = 0
            for deal in report.selected_deals:
                if deal.selected_tranches:
                    # Deal has explicit tranche selections
                    tranche_count += len(deal.selected_tranches)
                else:
                    # Deal uses "smart" all-tranches selection - get actual count from data warehouse
                    deal_tranches = self.dw_dao.get_tranches_by_dl_nbr(deal.dl_nbr)
                    tranche_count += len(deal_tranches)
            
            calculation_count = len(report.selected_calculations)
            
            # Get execution statistics
            from app.reporting.models import ReportExecutionLog
            
            execution_stats = self.query_engine.config_db.query(ReportExecutionLog)\
                .filter(ReportExecutionLog.report_id == report.id)
            
            total_executions = execution_stats.count()
            last_execution = execution_stats.order_by(ReportExecutionLog.executed_at.desc()).first()

            summary = ReportSummary(
                id=report.id,
                name=report.name,
                scope=ReportScope(report.scope),
                created_by=report.created_by or "system",
                created_date=report.created_date,
                deal_count=deal_count,
                tranche_count=tranche_count,
                calculation_count=calculation_count,
                is_active=report.is_active,
                total_executions=total_executions,
                last_executed=last_execution.executed_at if last_execution else None,
                last_execution_success=last_execution.success if last_execution else None
            )
            summaries.append(summary)

        return summaries

    async def create(self, report_data: ReportCreate) -> ReportRead:
        """Create a new report with calculation-based validation."""
        # Pydantic already handled structural validation
        # Only validate database constraints
        await self._validate_database_constraints(report_data)

        # Direct model creation using Pydantic's model_dump
        report_dict = report_data.model_dump()
        report_dict['scope'] = report_data.scope.value  # Convert enum to string
        
        # Create main report
        report = Report(**{k: v for k, v in report_dict.items() if k not in ['selected_deals', 'selected_calculations']})
        
        # Add deals and tranches
        self._populate_deals_and_tranches(report, report_data.selected_deals)
        
        # Add calculations
        self._populate_calculations(report, report_data.selected_calculations)
        
        created_report = await self.report_dao.create(report)
        return ReportRead.model_validate(created_report)

    async def update(self, report_id: int, report_data: ReportUpdate) -> Optional[ReportRead]:
        """Update a report with calculation-based validation."""
        report = await self.report_dao.get_by_id(report_id)
        if not report:
            return None

        # Pydantic already handled structural validation
        # Only validate database constraints
        await self._validate_database_constraints(report_data, existing_report_id=report_id)

        # Update basic fields using Pydantic's model_dump
        update_data = report_data.model_dump(exclude_unset=True, exclude={'selected_deals', 'selected_calculations'})
        
        # Handle scope enum conversion
        if "scope" in update_data and update_data["scope"]:
            update_data["scope"] = update_data["scope"].value

        for field, value in update_data.items():
            setattr(report, field, value)

        # Handle deals and tranches update if provided
        if report_data.selected_deals is not None:
            report.selected_deals.clear()
            self._populate_deals_and_tranches(report, report_data.selected_deals)

        # Handle calculations update if provided
        if report_data.selected_calculations is not None:
            report.selected_calculations.clear()
            self._populate_calculations(report, report_data.selected_calculations)

        updated_report = await self.report_dao.update(report)
        return ReportRead.model_validate(updated_report)

    async def delete(self, report_id: int) -> bool:
        """Delete a report."""
        return await self.report_dao.delete(report_id)

    def _build_deal_tranche_mapping(self, report: Report) -> Dict[int, List[str]]:
        """Extract deal-tranche mapping from report configuration."""
        deal_tranche_map = {}
        
        for deal in report.selected_deals:
            selected_tranches = [rt.tr_id for rt in deal.selected_tranches]
            deal_tranche_map[deal.dl_nbr] = selected_tranches
        
        # Handle each deal individually: if no specific tranches stored, get all tranches for that deal
        for dl_nbr, tranches_list in deal_tranche_map.items():
            if not tranches_list:  # If empty, it means "include all tranches"
                deal_tranches = self.dw_dao.get_tranches_by_dl_nbr(dl_nbr)
                deal_tranche_map[dl_nbr] = [t.tr_id for t in deal_tranches]
        
        return deal_tranche_map

    def _prepare_report_execution(self, report: Report) -> tuple:
        """Prepare all data needed for report execution (used by both run and preview)."""
        # Build deal-tranche mapping
        deal_tranche_map = self._build_deal_tranche_mapping(report)
        
        # Get calculations for this report
        calculations = []
        calc_repo = CalculationDAO(self.query_engine.config_db)
        
        for report_calc in report.selected_calculations:
            calc_id = report_calc.calculation_id
            
            # Check if this is a virtual auto-generated RAW field (ID >= 10000)
            if calc_id >= 10000:
                # This is a virtual auto-generated field - create a temporary calculation object
                virtual_calc = self._create_virtual_calculation_from_id(calc_id, report.scope)
                if virtual_calc:
                    calculations.append(virtual_calc)
            else:
                # This is a real calculation from the database
                calc = calc_repo.get_by_id(calc_id)
                if calc:
                    calculations.append(calc)
        
        if not calculations:
            raise HTTPException(status_code=400, detail="No valid calculations found for report")
        
        return deal_tranche_map, calculations

    def _create_virtual_calculation_from_id(self, virtual_id: int, report_scope: str) -> Optional[Calculation]:
        """Create a virtual calculation object for auto-generated RAW fields."""
        from app.calculations.models import Calculation, AggregationFunction, SourceModel, GroupLevel
        
        # Recreate the same auto-generated fields logic to find the matching field
        scope_enum = ReportScope.DEAL if report_scope.upper() == "DEAL" else ReportScope.TRANCHE
        auto_fields = self._generate_auto_raw_fields(scope_enum)
        
        # Find the matching auto-generated field
        for auto_field in auto_fields:
            if auto_field.id == virtual_id:
                # Create a temporary Calculation object that mimics the virtual field
                virtual_calc = Calculation()
                virtual_calc.id = virtual_id
                virtual_calc.name = auto_field.name
                virtual_calc.description = auto_field.description
                virtual_calc.aggregation_function = AggregationFunction.RAW
                virtual_calc.source_model = SourceModel(auto_field.source_model)
                virtual_calc.source_field = auto_field.source_field
                virtual_calc.group_level = GroupLevel(auto_field.group_level)
                virtual_calc.weight_field = None
                virtual_calc.is_active = True
                
                return virtual_calc
        
        return None

    async def run_saved_report(self, report_id: int, cycle_code: int) -> List[Dict[str, Any]]:
        """Run a saved report using the QueryEngine with calculations and execution logging."""
        if not self.query_engine:
            raise HTTPException(status_code=500, detail="Query engine not available")
            
        start_time = time.time()
        
        try:
            report = await self._get_validated_report(report_id)
            
            # Use shared preparation logic
            deal_tranche_map, calculations = self._prepare_report_execution(report)
            
            # Execute using QueryEngine with proper deal-tranche mapping
            results = self.query_engine.execute_report_query_with_mapping(
                deal_tranche_map=deal_tranche_map,
                cycle_code=cycle_code,
                calculations=calculations,
                aggregation_level=report.scope.lower()
            )
            
            # Process results
            processed_results = self.query_engine.process_report_results(
                results=results,
                calculations=calculations,
                aggregation_level=report.scope.lower()
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            # Log successful execution
            await self._log_execution(
                report_id=report_id,
                cycle_code=cycle_code,
                executed_by="api_user",  # Could be made dynamic
                execution_time_ms=execution_time,
                row_count=len(processed_results),
                success=True
            )
            
            return processed_results
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            # Log failed execution
            await self._log_execution(
                report_id=report_id,
                cycle_code=cycle_code,
                executed_by="api_user",
                execution_time_ms=execution_time,
                row_count=0,
                success=False,
                error_message=str(e)
            )
            
            # Re-raise the exception
            raise

    async def preview_report_sql(self, report_id: int, cycle_code: int) -> Dict[str, Any]:
        """Preview SQL that would be generated for a report - uses exact same logic as execution."""
        if not self.query_engine:
            raise HTTPException(status_code=500, detail="Query engine not available")
            
        report = await self._get_validated_report(report_id)
        
        # Use the EXACT same preparation logic as execution
        deal_tranche_map, calculations = self._prepare_report_execution(report)
        
        # Generate the query using the same method as execution, but extract SQL instead of executing
        query = self.query_engine.build_consolidated_query_with_mapping(
            deal_tranche_map=deal_tranche_map,
            cycle_code=cycle_code,
            calculations=calculations,
            aggregation_level=report.scope.lower()
        )
        
        # Analyze the calculations
        raw_count = sum(1 for calc in calculations if calc.is_raw_field())
        aggregated_count = len(calculations) - raw_count
        
        # Extract deal numbers and tranche IDs for the response
        deal_numbers = list(deal_tranche_map.keys())
        all_tranche_ids = []
        for tranches in deal_tranche_map.values():
            all_tranche_ids.extend(tranches)
        
        return {
            "template_name": report.name,
            "aggregation_level": report.scope.lower(),
            "calculation_summary": {
                "total_calculations": len(calculations),
                "raw_fields": raw_count,
                "aggregated_calculations": aggregated_count
            },
            "deal_tranche_mapping": deal_tranche_map,  # Include the mapping in response
            "sql_query": self.query_engine._compile_query_to_sql(query),
            "parameters": {
                "cycle_code": cycle_code,
                "deal_numbers": deal_numbers,
                "tranche_ids": all_tranche_ids
            }
        }

    async def get_execution_logs(self, report_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get execution logs for a report."""
        report = await self._get_validated_report(report_id)
        
        # Import here to avoid circular imports
        from app.reporting.models import ReportExecutionLog
        
        logs = self.query_engine.config_db.query(ReportExecutionLog)\
            .filter(ReportExecutionLog.report_id == report_id)\
            .order_by(ReportExecutionLog.executed_at.desc())\
            .limit(limit).all()
        
        return [
            {
                "id": log.id,
                "cycle_code": log.cycle_code,
                "executed_by": log.executed_by,
                "execution_time_ms": log.execution_time_ms,
                "row_count": log.row_count,
                "success": log.success,
                "error_message": log.error_message,
                "executed_at": log.executed_at
            }
            for log in logs
        ]

    async def _log_execution(
        self,
        report_id: int,
        cycle_code: int,
        executed_by: str,
        execution_time_ms: float,
        row_count: int,
        success: bool,
        error_message: str = None
    ) -> None:
        """Log report execution."""
        # Import here to avoid circular imports
        from app.reporting.models import ReportExecutionLog
        
        log_entry = ReportExecutionLog(
            report_id=report_id,
            cycle_code=cycle_code,
            executed_by=executed_by,
            execution_time_ms=execution_time_ms,
            row_count=row_count,
            success=success,
            error_message=error_message
        )
        
        self.query_engine.config_db.add(log_entry)
        self.query_engine.config_db.commit()

    async def get_available_deals(self) -> List[Dict[str, Any]]:
        """Get available deals from the data warehouse."""
        try:
            deals = self.dw_dao.get_all_deals()
            return [
                {
                    "dl_nbr": deal.dl_nbr,
                    "issr_cde": deal.issr_cde,
                    "cdi_file_nme": deal.cdi_file_nme,
                    "CDB_cdi_file_nme": deal.CDB_cdi_file_nme
                }
                for deal in deals
            ]
        except Exception as e:
            # Fallback to empty data
            print(f"Warning: Could not fetch deals from data warehouse: {e}")
            return []

    async def get_available_tranches_for_deals(self, deal_ids: List[int], cycle_code: Optional[int] = None) -> Dict[int, List[Dict[str, Any]]]:
        """Get available tranches for specific deals."""
        try:
            tranches_by_deal = {}
            
            for deal_id in deal_ids:
                tranches = self.dw_dao.get_tranches_by_dl_nbr(deal_id)
                tranches_by_deal[deal_id] = [
                    {
                        "tr_id": tranche.tr_id
                    }
                    for tranche in tranches
                ]
            
            return tranches_by_deal
        except Exception as e:
            # Fallback to empty data
            print(f"Warning: Could not fetch tranches from data warehouse: {e}")
            return {}

    async def get_available_cycles(self) -> List[Dict[str, Any]]:
        """Get available cycle codes from the data warehouse."""
        try:
            return self.dw_dao.get_available_cycles()
        except Exception as e:
            # Fallback to empty data
            print(f"Warning: Could not fetch cycle data from data warehouse: {e}")
            return []

    def _populate_deals_and_tranches(self, report: Report, selected_deals: List[ReportDealCreate]) -> None:
        """Populate deals and tranches for a report.
        
        Smart logic:
        - For DEAL scope: Only store tranches if they represent explicit exclusions
        - For TRANCHE scope: Always store selected tranches
        - If no tranches are provided for a deal, it means all tranches are included (no storage needed)
        """
        for deal_data in selected_deals:
            # Create ReportDeal
            report_deal = ReportDeal(
                dl_nbr=deal_data.dl_nbr
            )
            
            # Only add tranches to the database if they were explicitly provided
            # Frontend now only sends tranches when they represent explicit user selections
            if hasattr(deal_data, 'selected_tranches') and deal_data.selected_tranches:
                for tranche_data in deal_data.selected_tranches:
                    # Auto-populate dl_nbr if missing
                    tranche_dl_nbr = tranche_data.dl_nbr if tranche_data.dl_nbr is not None else deal_data.dl_nbr
                    
                    report_tranche = ReportTranche(
                        dl_nbr=tranche_dl_nbr,
                        tr_id=tranche_data.tr_id
                    )
                    report_deal.selected_tranches.append(report_tranche)
            
            # If no tranches are provided (empty list or missing), it means:
            # - For DEAL scope: All tranches are included (default behavior)
            # - For TRANCHE scope: No tranches selected (explicit empty selection)
            # In both cases, we don't store anything in report_tranches table
            
            report.selected_deals.append(report_deal)

    def _populate_calculations(self, report: Report, selected_calculations: List[ReportCalculationCreate]) -> None:
        """Populate calculations for a report."""
        for calc_data in selected_calculations:
            report_calc = ReportCalculation(
                calculation_id=calc_data.calculation_id,
                display_order=calc_data.display_order
            )
            report.selected_calculations.append(report_calc)

    async def _get_validated_report(self, report_id: int) -> Report:
        """Get and validate that a report exists."""
        report = await self.report_dao.get_by_id(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return report

    def _get_tranche_summaries_for_deal(self, dl_nbr: int) -> List[Dict[str, Any]]:
        """Get tranche summaries for a specific deal."""
        deal = self.dw_dao.get_deal_by_dl_nbr(dl_nbr)
        if not deal:
            return []
        
        tranche_summaries = []
        for tranche in deal.tranches:
            tranche_summary = {
                "tranche_id": tranche.tr_id,
                "tranche_name": tranche.name,
                "balance": tranche.balance,
                "rate": tranche.rate,
                "status": tranche.status
            }
            tranche_summaries.append(tranche_summary)
        
        return tranche_summaries

    def _generate_auto_raw_fields(self, scope: ReportScope) -> List[AvailableCalculation]:
        """Auto-generate RAW field calculations based on available model fields."""
        auto_fields = []
        
        # Define available fields for each model with metadata
        field_definitions = {
            "Deal": [
                {"field": "dl_nbr", "name": "Deal Number", "description": "Unique deal identifier", "type": "number"},
                {"field": "issr_cde", "name": "Issuer Code", "description": "Deal issuer code", "type": "string"},
                {"field": "cdi_file_nme", "name": "CDI File Name", "description": "CDI file name", "type": "string"},
                {"field": "CDB_cdi_file_nme", "name": "CDB CDI File Name", "description": "CDB CDI file name", "type": "string"},
            ],
            "Tranche": [
                {"field": "tr_id", "name": "Tranche ID", "description": "Tranche identifier within the deal", "type": "string"},
                {"field": "dl_nbr", "name": "Deal Number", "description": "Parent deal number", "type": "number"},
                {"field": "tr_cusip_id", "name": "Tranche CUSIP ID", "description": "CUSIP identifier for the tranche", "type": "string"},
            ],
            "TrancheBal": [
                {"field": "tr_end_bal_amt", "name": "Ending Balance Amount", "description": "Outstanding principal balance at period end", "type": "currency"},
                {"field": "tr_prin_rel_ls_amt", "name": "Principal Release/Loss Amount", "description": "Principal released or lost during the period", "type": "currency"},
                {"field": "tr_pass_thru_rte", "name": "Pass Through Rate", "description": "Interest rate passed through to investors", "type": "percentage"},
                {"field": "tr_accrl_days", "name": "Accrual Days", "description": "Number of days in the accrual period", "type": "number"},
                {"field": "tr_int_dstrb_amt", "name": "Interest Distribution Amount", "description": "Interest distributed to investors", "type": "currency"},
                {"field": "tr_prin_dstrb_amt", "name": "Principal Distribution Amount", "description": "Principal distributed to investors", "type": "currency"},
                {"field": "tr_int_accrl_amt", "name": "Interest Accrual Amount", "description": "Interest accrued during the period", "type": "currency"},
                {"field": "tr_int_shtfl_amt", "name": "Interest Shortfall Amount", "description": "Interest shortfall amount", "type": "currency"},
                {"field": "cycle_cde", "name": "Cycle Code", "description": "Reporting cycle identifier (YYYYMM format)", "type": "number"},
            ]
        }
        
        # Determine which models to include based on scope - CORRECTED LOGIC
        models_to_include = []
        group_level = scope.value.lower()  # 'deal' or 'tranche'
        
        if scope == ReportScope.DEAL:
            # For deal-level reports, ONLY include Deal fields as raw fields
            # TrancheBal fields should only be available as aggregated calculations
            models_to_include = ["Deal"]
        else:
            # For tranche-level reports, include Deal and Tranche fields as raw fields
            # TrancheBal fields should only be available as aggregated calculations
            models_to_include = ["Deal", "Tranche"]
        
        # Generate unique ID starting from a high number to avoid conflicts with manual calculations
        auto_id_counter = 10000
        
        for source_model in models_to_include:
            fields = field_definitions.get(source_model, [])
            
            for field_def in fields:
                # Skip duplicate dl_nbr from Tranche model when Deal is already included
                if field_def["field"] == "dl_nbr" and source_model == "Tranche":
                    continue
                    
                # Create category based on source model and field type
                category = self._get_auto_field_category(source_model, field_def)
                
                # Generate a virtual calculation for this raw field
                auto_field = AvailableCalculation(
                    id=auto_id_counter,  # Virtual ID that won't conflict with real calculations
                    name=field_def["name"],
                    description=field_def["description"],
                    aggregation_function="RAW",
                    source_model=source_model,
                    source_field=field_def["field"],
                    group_level=group_level,
                    weight_field=None,
                    scope=scope,
                    category=category,
                    is_default=self._is_default_raw_field(source_model, field_def["field"])
                )
                auto_fields.append(auto_field)
                auto_id_counter += 1
        
        return auto_fields

    def _get_auto_field_category(self, source_model: str, field_def: dict) -> str:
        """Determine category for auto-generated raw fields."""
        if source_model == "Deal":
            return "Deal Information"
        elif source_model == "Tranche":
            return "Tranche Structure"
        elif source_model == "TrancheBal":
            field_name = field_def["field"].lower()
            field_type = field_def["type"]
            
            if "bal" in field_name or "amt" in field_name:
                if field_type == "currency":
                    return "Balance & Amount Fields"
                else:
                    return "Balance Data"
            elif "rte" in field_name or "rate" in field_name:
                return "Rate Fields"
            elif "dstrb" in field_name:
                return "Distribution Fields"
            elif "accrl" in field_name:
                return "Accrual Fields"
            elif field_name == "cycle_cde":
                return "Cycle Information"
            else:
                return "Other TrancheBal Fields"
        else:
            return "Other Fields"

    def _is_default_raw_field(self, source_model: str, field_name: str) -> bool:
        """Determine if a raw field should be selected by default."""
        # Define commonly used fields that should be selected by default
        default_fields = {
            "Deal": ["dl_nbr"],
            "Tranche": ["tr_id"],
            "TrancheBal": ["tr_end_bal_amt", "cycle_cde"]
        }
        
        return field_name in default_fields.get(source_model, [])