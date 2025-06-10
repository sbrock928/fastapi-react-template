"""Service layer for the reporting module - Phase 1: Fixed async/sync issues."""

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
from app.calculations.models import Calculation, GroupLevel
from app.query import QueryEngine
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

    def get_available_calculations(self, scope: ReportScope) -> List[AvailableCalculation]:
        """Get available calculations for report configuration based on scope."""
        
        if not self.query_engine:
            raise HTTPException(status_code=500, detail="Query engine not available")
            
        calc_dao = CalculationDAO(self.query_engine.config_db)
        
        # Filter calculations by group level (deal/tranche) based on scope
        if scope == ReportScope.DEAL:
            calculations = calc_dao.get_all_calculations(group_level=GroupLevel.DEAL)
        else:
            # For tranche scope, get both deal-level and tranche-level calculations
            deal_calculations = calc_dao.get_all_calculations(group_level=GroupLevel.DEAL)
            tranche_calculations = calc_dao.get_all_calculations(group_level=GroupLevel.TRANCHE)
            calculations = deal_calculations + tranche_calculations
        
        available_calculations = []
        
        # Convert to AvailableCalculation schema
        for calc in calculations:
            category = self._get_calculation_category(calc)
            is_default = self._is_default_calculation(calc)
            
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
        
        return available_calculations

    def _get_calculation_category(self, calc: Calculation) -> str:
        """Determine the category for a calculation based on its properties."""
        source_model = calc.source_model.value
        source_field = calc.source_field
        agg_function = calc.aggregation_function.value
        
        if source_model == "Deal":
            return "Deal Information"
        elif source_model == "Tranche":
            return "Tranche Structure"
        elif source_model == "TrancheBal":
            if agg_function == "RAW":
                return "Raw TrancheBal Fields"
            elif "bal" in source_field.lower() or "amt" in source_field.lower():
                return "Balance & Amount Calculations"
            elif "rte" in source_field.lower() or "rate" in source_field.lower():
                return "Rate Calculations"
            elif "dstrb" in source_field.lower():
                return "Distribution Calculations"
            elif "accrl" in source_field.lower():
                return "Accrual Calculations"
            else:
                return "Performance Calculations"
        else:
            return "Other"

    def _is_default_calculation(self, calc: Calculation) -> bool:
        """Determine if a calculation should be selected by default."""
        # Mark common calculations as default
        default_calc_names = [
            "Deal Number", "Total Ending Balance", "Average Pass Through Rate",
            "Tranche ID", "Ending Balance Amount"
        ]
        return calc.name in default_calc_names

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
        reports = await self.report_dao.get_all()  # FIXED: await the async call
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
        """Create a new report."""
        # Pydantic validation handles most validation
        # Create main report
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
        """Update a report."""
        report = await self.report_dao.get_by_id(report_id)
        if not report:
            return None

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
        
        # Get calculations for this report - simplified to only get real calculations
        calculations = []
        calc_dao = CalculationDAO(self.query_engine.config_db)
        
        for report_calc in report.selected_calculations:
            calc_id = report_calc.calculation_id
            calc = calc_dao.get_by_id(calc_id)
            if calc:
                calculations.append(calc)
        
        if not calculations:
            raise HTTPException(status_code=400, detail="No valid calculations found for report")
        
        return deal_tranche_map, calculations

    async def run_saved_report(self, report_id: int, cycle_code: int) -> List[Dict[str, Any]]:
        """Run a saved report using the simplified QueryEngine"""
        if not self.query_engine:
            raise HTTPException(status_code=500, detail="Query engine not available")
            
        start_time = time.time()
        
        try:
            report = await self._get_validated_report(report_id)
            
            # Use shared preparation logic
            deal_tranche_map, calculations = self._prepare_report_execution(report)
            
            # Execute using simplified QueryEngine
            results = self.query_engine.execute_report_query(
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
                executed_by="api_user",
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
        """Preview SQL that would be generated for a report."""
        if not self.query_engine:
            raise HTTPException(status_code=500, detail="Query engine not available")
            
        report = await self._get_validated_report(report_id)
        
        # Use the EXACT same preparation logic as execution
        deal_tranche_map, calculations = self._prepare_report_execution(report)
        
        # Generate the query using simplified method
        return self.query_engine.preview_report_sql(
            report_name=report.name,
            deal_tranche_map=deal_tranche_map,
            cycle_code=cycle_code,
            calculations=calculations,
            aggregation_level=report.scope.lower()
        )

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

    def get_available_deals(self) -> List[Dict[str, Any]]:
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

    def get_available_tranches_for_deals(self, deal_ids: List[int], cycle_code: Optional[int] = None) -> Dict[int, List[Dict[str, Any]]]:
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

    def get_available_cycles(self) -> List[Dict[str, Any]]:
        """Get available cycle codes from the data warehouse."""
        try:
            return self.dw_dao.get_available_cycles()
        except Exception as e:
            # Fallback to empty data
            print(f"Warning: Could not fetch cycle data from data warehouse: {e}")
            return []

    def _populate_deals_and_tranches(self, report: Report, selected_deals: List[ReportDealCreate]) -> None:
        """Populate deals and tranches for a report - keeping smart logic."""
        for deal_data in selected_deals:
            # Create ReportDeal
            report_deal = ReportDeal(
                dl_nbr=deal_data.dl_nbr
            )
            
            # Only add tranches to the database if they were explicitly provided
            if hasattr(deal_data, 'selected_tranches') and deal_data.selected_tranches:
                for tranche_data in deal_data.selected_tranches:
                    # Auto-populate dl_nbr if missing
                    tranche_dl_nbr = tranche_data.dl_nbr if tranche_data.dl_nbr is not None else deal_data.dl_nbr
                    
                    report_tranche = ReportTranche(
                        dl_nbr=tranche_dl_nbr,
                        tr_id=tranche_data.tr_id
                    )
                    report_deal.selected_tranches.append(report_tranche)
            
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