"""Service layer for the reporting module - Phase 3: Streamlined execution."""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException

from app.reporting.dao import ReportDAO
from app.reporting.models import Report, ReportDeal, ReportTranche, ReportCalculation
from app.reporting.schemas import (
    ReportRead, ReportCreate, ReportUpdate, ReportSummary, ReportScope,
    ReportDealCreate, ReportTrancheCreate, ReportCalculationCreate, AvailableCalculation
)
from app.datawarehouse.dao import DatawarehouseDAO
from app.calculations.dao import CalculationDAO
from app.calculations.models import Calculation, GroupLevel
from app.query import QueryEngine
import time


class ReportService:
    """Streamlined service for managing report configurations and execution."""

    def __init__(self, report_dao: ReportDAO, dw_dao: DatawarehouseDAO, query_engine: QueryEngine = None):
        self.report_dao = report_dao
        self.dw_dao = dw_dao
        self.query_engine = query_engine

    # ===== CALCULATION MANAGEMENT =====

    def get_available_calculations(self, scope: ReportScope) -> List[AvailableCalculation]:
        """Get available calculations for report configuration based on scope."""
        if not self.query_engine:
            raise HTTPException(status_code=500, detail="Query engine not available")
            
        calc_dao = CalculationDAO(self.query_engine.config_db)
        
        # Get calculations based on scope - enforce proper scoping
        if scope == ReportScope.DEAL:
            # Deal-level reports: only deal-level calculations
            calculations = calc_dao.get_all_calculations(group_level=GroupLevel.DEAL)
        else:
            # Tranche-level reports: only tranche-level calculations
            # Deal-level calculations should not be available for tranche reports
            calculations = calc_dao.get_all_calculations(group_level=GroupLevel.TRANCHE)
        
        return [self._convert_to_available_calculation(calc, scope) for calc in calculations]

    def _convert_to_available_calculation(self, calc: Calculation, scope: ReportScope) -> AvailableCalculation:
        """Convert a Calculation model to AvailableCalculation schema."""
        return AvailableCalculation(
            id=calc.id,
            name=calc.name,
            description=calc.description,
            aggregation_function=calc.aggregation_function.value if calc.aggregation_function else None,
            source_model=calc.source_model.value if calc.source_model else None,
            source_field=calc.source_field,
            group_level=calc.group_level.value,
            weight_field=calc.weight_field,
            scope=scope,
            category=self._categorize_calculation(calc),
            is_default=calc.name in ["Deal Number", "Total Ending Balance", "Tranche ID", "Ending Balance Amount"]
        )

    def _categorize_calculation(self, calc: Calculation) -> str:
        """Categorize calculation for UI grouping."""
        if not calc.source_model:
            # Handle system SQL calculations or other calculations without source_model
            if hasattr(calc, 'calculation_type') and calc.calculation_type.value == 'SYSTEM_SQL':
                return "Custom SQL Calculations"
            return "Other"
            
        source_model = calc.source_model.value
        source_field = calc.source_field or ""
        
        if source_model == "Deal":
            return "Deal Information"
        elif source_model == "Tranche":
            return "Tranche Structure"
        elif source_model == "TrancheBal":
            if "bal" in source_field.lower() or "amt" in source_field.lower():
                return "Balance & Amount Calculations"
            elif "rte" in source_field.lower():
                return "Rate Calculations"
            elif "dstrb" in source_field.lower():
                return "Distribution Calculations"
            else:
                return "Performance Calculations"
        return "Other"

    # ===== CORE CRUD OPERATIONS =====

    async def get_all(self) -> List[ReportRead]:
        """Get all reports."""
        reports = await self.report_dao.get_all()
        return [ReportRead.model_validate(report) for report in reports]

    async def get_by_id(self, report_id: int) -> Optional[ReportRead]:
        """Get a report by ID."""
        report = await self.report_dao.get_by_id(report_id)
        return ReportRead.model_validate(report) if report else None

    async def get_all_summaries(self) -> List[ReportSummary]:
        """Get all reports with summary information."""
        reports = await self.report_dao.get_all()
        return [self._build_summary(report) for report in reports]

    def _build_summary(self, report: Report) -> ReportSummary:
        """Build summary for a single report."""
        # Calculate counts
        deal_count = len(report.selected_deals)
        tranche_count = sum(
            len(deal.selected_tranches) if deal.selected_tranches 
            else len(self.dw_dao.get_tranches_by_dl_nbr(deal.dl_nbr))
            for deal in report.selected_deals
        )
        
        # Get execution stats
        from app.reporting.models import ReportExecutionLog
        execution_query = self.query_engine.config_db.query(ReportExecutionLog)\
            .filter(ReportExecutionLog.report_id == report.id)
        
        total_executions = execution_query.count()
        last_execution = execution_query.order_by(ReportExecutionLog.executed_at.desc()).first()
        
        return ReportSummary(
            id=report.id,
            name=report.name,
            scope=ReportScope(report.scope),
            created_by=report.created_by or "system",
            created_date=report.created_date,
            deal_count=deal_count,
            tranche_count=tranche_count,
            calculation_count=len(report.selected_calculations),
            is_active=report.is_active,
            total_executions=total_executions,
            last_executed=last_execution.executed_at if last_execution else None,
            last_execution_success=last_execution.success if last_execution else None
        )

    async def create(self, report_data: ReportCreate) -> ReportRead:
        """Create a new report."""
        report = self._build_report(report_data)
        created_report = await self.report_dao.create(report)
        return ReportRead.model_validate(created_report)

    async def update(self, report_id: int, report_data: ReportUpdate) -> Optional[ReportRead]:
        """Update a report."""
        report = await self.report_dao.get_by_id(report_id)
        if not report:
            return None

        self._update_report(report, report_data)
        updated_report = await self.report_dao.update(report)
        return ReportRead.model_validate(updated_report)

    async def delete(self, report_id: int) -> bool:
        """Delete a report."""
        return await self.report_dao.delete(report_id)

    def _build_report(self, report_data: ReportCreate) -> Report:
        """Build Report entity from creation data."""
        # Base report
        report_dict = report_data.model_dump(exclude={'selected_deals', 'selected_calculations'})
        report_dict['scope'] = report_data.scope.value
        report = Report(**report_dict)
        
        # Add relationships
        for deal_data in report_data.selected_deals:
            report_deal = ReportDeal(dl_nbr=deal_data.dl_nbr)
            
            # Smart tranche logic: only store if explicitly provided
            if hasattr(deal_data, 'selected_tranches') and deal_data.selected_tranches:
                for tranche_data in deal_data.selected_tranches:
                    report_tranche = ReportTranche(
                        dl_nbr=tranche_data.dl_nbr or deal_data.dl_nbr,
                        tr_id=tranche_data.tr_id
                    )
                    report_deal.selected_tranches.append(report_tranche)
            
            report.selected_deals.append(report_deal)
        
        for calc_data in report_data.selected_calculations:
            report_calc = ReportCalculation(
                calculation_id=calc_data.calculation_id,
                display_order=calc_data.display_order
            )
            report.selected_calculations.append(report_calc)
        
        return report

    def _update_report(self, report: Report, report_data: ReportUpdate) -> None:
        """Update Report entity from update data."""
        # Update basic fields
        update_data = report_data.model_dump(
            exclude_unset=True, 
            exclude={'selected_deals', 'selected_calculations'}
        )
        
        if "scope" in update_data and update_data["scope"]:
            update_data["scope"] = update_data["scope"].value

        for field, value in update_data.items():
            setattr(report, field, value)

        # Update relationships if provided
        if report_data.selected_deals is not None:
            report.selected_deals.clear()
            # Build deals directly without using ReportCreate validation
            for deal_data in report_data.selected_deals:
                report_deal = ReportDeal(dl_nbr=deal_data.dl_nbr)
                
                # Smart tranche logic: only store if explicitly provided
                if hasattr(deal_data, 'selected_tranches') and deal_data.selected_tranches:
                    for tranche_data in deal_data.selected_tranches:
                        report_tranche = ReportTranche(
                            dl_nbr=tranche_data.dl_nbr or deal_data.dl_nbr,
                            tr_id=tranche_data.tr_id
                        )
                        report_deal.selected_tranches.append(report_tranche)
                
                report.selected_deals.append(report_deal)

        if report_data.selected_calculations is not None:
            report.selected_calculations.clear()
            for calc_data in report_data.selected_calculations:
                report_calc = ReportCalculation(
                    calculation_id=calc_data.calculation_id,
                    display_order=calc_data.display_order
                )
                report.selected_calculations.append(report_calc)

    # ===== STREAMLINED EXECUTION ENGINE =====

    def _prepare_execution(self, report: Report) -> tuple[Dict[int, List[str]], List[Calculation]]:
        """Prepare execution data - single preparation method for both preview and execution."""
        # Build deal-tranche mapping with smart logic
        deal_tranche_map = {}
        for deal in report.selected_deals:
            if deal.selected_tranches:
                # Explicit tranche selection
                deal_tranche_map[deal.dl_nbr] = [rt.tr_id for rt in deal.selected_tranches]
            else:
                # Smart logic: include all tranches
                all_tranches = self.dw_dao.get_tranches_by_dl_nbr(deal.dl_nbr)
                deal_tranche_map[deal.dl_nbr] = [t.tr_id for t in all_tranches]
        
        # Get calculations
        calc_dao = CalculationDAO(self.query_engine.config_db)
        calculations = []
        for report_calc in report.selected_calculations:
            calc = calc_dao.get_by_id(report_calc.calculation_id)
            if calc:
                calculations.append(calc)
        
        if not calculations:
            raise HTTPException(status_code=400, detail="No valid calculations found for report")
        
        return deal_tranche_map, calculations

    async def run_saved_report(self, report_id: int, cycle_code: int) -> List[Dict[str, Any]]:
        """Execute a report - streamlined single-path execution."""
        if not self.query_engine:
            raise HTTPException(status_code=500, detail="Query engine not available")
        
        report = await self._get_report_or_404(report_id)
        start_time = time.time()
        
        try:
            # Prepare execution (same logic as preview)
            deal_tranche_map, calculations = self._prepare_execution(report)
            
            # Execute via QueryEngine (single method call)
            results = self.query_engine.execute_report_query(
                deal_tranche_map=deal_tranche_map,
                cycle_code=cycle_code,
                calculations=calculations,
                aggregation_level=report.scope.lower()
            )
            
            # Process results (simplified)
            processed_results = self.query_engine.process_report_results(
                results=results,
                calculations=calculations,
                aggregation_level=report.scope.lower()
            )
            
            # Log execution
            await self._log_execution(
                report_id, cycle_code, "api_user",
                (time.time() - start_time) * 1000,
                len(processed_results), True
            )
            
            return processed_results
            
        except Exception as e:
            # Log failure
            await self._log_execution(
                report_id, cycle_code, "api_user",
                (time.time() - start_time) * 1000,
                0, False, str(e)
            )
            raise

    async def preview_report_sql(self, report_id: int, cycle_code: int) -> Dict[str, Any]:
        """Preview SQL - uses same preparation as execution for consistency."""
        if not self.query_engine:
            raise HTTPException(status_code=500, detail="Query engine not available")
        
        report = await self._get_report_or_404(report_id)
        
        # Use same preparation as execution (guaranteed consistency)
        deal_tranche_map, calculations = self._prepare_execution(report)
        
        # Generate preview via QueryEngine
        return self.query_engine.preview_report_sql(
            report_name=report.name,
            deal_tranche_map=deal_tranche_map,
            cycle_code=cycle_code,
            calculations=calculations,
            aggregation_level=report.scope.lower()
        )

    async def get_execution_logs(self, report_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get execution logs - simplified."""
        await self._get_report_or_404(report_id)  # Validate report exists
        
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
        self, report_id: int, cycle_code: int, executed_by: str,
        execution_time_ms: float, row_count: int, success: bool, error_message: str = None
    ) -> None:
        """Log execution - simplified."""
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

    # ===== DATA WAREHOUSE ENDPOINTS =====

    def get_available_deals(self) -> List[Dict[str, Any]]:
        """Get available deals."""
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
            print(f"Warning: Could not fetch deals: {e}")
            return []

    def get_available_tranches_for_deals(self, deal_ids: List[int], cycle_code: Optional[int] = None) -> Dict[int, List[Dict[str, Any]]]:
        """Get available tranches for deals."""
        try:
            return {
                deal_id: [{"tr_id": t.tr_id} for t in self.dw_dao.get_tranches_by_dl_nbr(deal_id)]
                for deal_id in deal_ids
            }
        except Exception as e:
            print(f"Warning: Could not fetch tranches: {e}")
            return {}

    def get_available_cycles(self) -> List[Dict[str, Any]]:
        """Get available cycles."""
        try:
            return self.dw_dao.get_available_cycles()
        except Exception as e:
            print(f"Warning: Could not fetch cycles: {e}")
            return []

    # ===== UTILITIES =====

    async def _get_report_or_404(self, report_id: int) -> Report:
        """Get report or raise 404."""
        report = await self.report_dao.get_by_id(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return report