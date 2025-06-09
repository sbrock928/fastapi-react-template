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
        """Get available calculations for report configuration based on scope."""
        
        # Get calculations from the config database using query engine
        if not self.query_engine:
            raise HTTPException(status_code=500, detail="Query engine not available")
            
        calc_repo = CalculationDAO(self.query_engine.config_db)
        
        # Filter calculations by group level (deal/tranche) based on scope
        if scope == ReportScope.DEAL:
            calculations = calc_repo.get_all_calculations(group_level="deal")
        else:
            calculations = calc_repo.get_all_calculations(group_level="tranche")
        
        # Convert to AvailableCalculation format
        available_calculations = []
        for calc in calculations:
            # Determine category based on source model and field
            category = self._get_calculation_category(calc)
            
            # Determine if this should be a default calculation
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

        # Validate calculation selections
        if hasattr(report_data, 'selected_calculations') and report_data.selected_calculations:
            if self.query_engine:
                calc_repo = CalculationDAO(self.query_engine.config_db)
                calc_ids = [calc.calculation_id for calc in report_data.selected_calculations]
                
                existing_calculations = []
                for calc_id in calc_ids:
                    calc = calc_repo.get_by_id(calc_id)
                    if calc:
                        existing_calculations.append(calc)
                
                existing_calc_ids = {calc.id for calc in existing_calculations}
                missing_calc_ids = set(calc_ids) - existing_calc_ids
                
                if missing_calc_ids:
                    errors.append(f"Calculation IDs not found: {sorted(missing_calc_ids)}")

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
            tranche_count = sum(len(deal.selected_tranches) for deal in report.selected_deals)
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

    async def run_saved_report(self, report_id: int, cycle_code: int) -> List[Dict[str, Any]]:
        """Run a saved report using the QueryEngine with calculations and execution logging."""
        if not self.query_engine:
            raise HTTPException(status_code=500, detail="Query engine not available")
            
        start_time = time.time()
        
        try:
            report = await self._get_validated_report(report_id)
            
            # Get report configuration
            deal_numbers = [rd.dl_nbr for rd in report.selected_deals]
            tranche_ids = []
            
            # Collect all tranche IDs from selected deals
            for deal in report.selected_deals:
                tranche_ids.extend([rt.tr_id for rt in deal.selected_tranches])
            
            # If no specific tranches selected, get all tranches for selected deals
            if not tranche_ids:
                for dl_nbr in deal_numbers:
                    deal_tranches = self.dw_dao.get_tranches_by_dl_nbr(dl_nbr)
                    tranche_ids.extend([t.tr_id for t in deal_tranches])
            
            print(f"DEBUG: Report execution - Deal numbers: {deal_numbers}")
            print(f"DEBUG: Report execution - Tranche IDs: {tranche_ids}")
            print(f"DEBUG: Report execution - Cycle code: {cycle_code}")
            
            # Get calculations for this report
            calculations = []
            calc_repo = CalculationDAO(self.query_engine.config_db)
            
            for report_calc in report.selected_calculations:
                calc = calc_repo.get_by_id(report_calc.calculation_id)
                if calc:
                    calculations.append(calc)
                    print(f"DEBUG: Added calculation: {calc.name} (ID: {calc.id})")
            
            if not calculations:
                raise HTTPException(status_code=400, detail="No valid calculations found for report")
            
            print(f"DEBUG: Total calculations: {len(calculations)}")
            
            # Execute using QueryEngine
            results = self.query_engine.execute_report_query(
                deal_numbers=deal_numbers,
                tranche_ids=tranche_ids,
                cycle_code=cycle_code,
                calculations=calculations,
                aggregation_level=report.scope.lower()
            )
            
            print(f"DEBUG: Raw query returned {len(results)} results")
            if results:
                print(f"DEBUG: First result attributes: {dir(results[0])}")
                print(f"DEBUG: First result: {results[0]}")
            
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
            
            raise e

    async def _get_validated_report(self, report_id: int) -> Report:
        """Get and validate report configuration."""
        report = await self.report_dao.get_by_id(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        if not report.is_active:
            raise HTTPException(status_code=400, detail="Report is inactive")
        return report

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

    def _populate_calculations(self, report: Report, selected_calculations_data: List) -> None:
        """Helper method to populate calculations for a report."""
        for i, calc_data in enumerate(selected_calculations_data):
            report_calculation = ReportCalculation(
                calculation_id=calc_data.calculation_id,
                display_order=calc_data.display_order if hasattr(calc_data, 'display_order') else i,
                display_name=calc_data.display_name if hasattr(calc_data, 'display_name') else None
            )
            report.selected_calculations.append(report_calculation)

    async def preview_report_sql(self, report_id: int, cycle_code: int) -> Dict[str, Any]:
        """Preview SQL that would be generated for a report."""
        if not self.query_engine:
            raise HTTPException(status_code=500, detail="Query engine not available")
            
        report = await self._get_validated_report(report_id)
        
        # Get report configuration
        deal_numbers = [rd.dl_nbr for rd in report.selected_deals]
        tranche_ids = []
        
        # Collect all tranche IDs from selected deals
        for deal in report.selected_deals:
            tranche_ids.extend([rt.tr_id for rt in deal.selected_tranches])
        
        # If no specific tranches selected, get sample tranches for preview
        if not tranche_ids:
            for dl_nbr in deal_numbers[:3]:  # Limit to first 3 deals for preview
                deal_tranches = self.dw_dao.get_tranches_by_dl_nbr(dl_nbr)
                tranche_ids.extend([t.tr_id for t in deal_tranches[:2]])  # First 2 tranches per deal
        
        # Get calculations for this report
        calculations = []
        calc_repo = CalculationDAO(self.query_engine.config_db)
        
        for report_calc in report.selected_calculations:
            calc = calc_repo.get_by_id(report_calc.calculation_id)
            if calc:
                calculations.append(calc)
        
        if not calculations:
            raise HTTPException(status_code=400, detail="No valid calculations found for report")
        
        # Use QueryEngine to preview SQL
        return self.query_engine.preview_report_sql(
            report_name=report.name,
            aggregation_level=report.scope.lower(),
            deal_numbers=deal_numbers[:3],  # Limit for preview
            tranche_ids=tranche_ids[:6],    # Limit for preview
            cycle_code=cycle_code,
            calculations=calculations
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