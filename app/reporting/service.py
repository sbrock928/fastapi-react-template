"""Clean reporting service using only the new separated calculation system."""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException

from app.reporting.dao import ReportDAO
from app.reporting.models import Report, ReportDeal, ReportTranche, ReportCalculation
from app.reporting.schemas import (
    ReportRead,
    ReportCreate,
    ReportUpdate,
    ReportSummary,
    ReportScope,
    AvailableCalculation,
)
from app.datawarehouse.dao import DatawarehouseDAO
from app.calculations.service import (
    UserCalculationService,
    SystemCalculationService, 
    StaticFieldService,
    ReportExecutionService
)
from app.calculations.models import GroupLevel
from app.calculations.resolver import CalculationRequest
import time


class ReportService:
    """Clean service for managing reports with the new calculation system."""

    def __init__(self, report_dao: ReportDAO, dw_dao: DatawarehouseDAO, dw_db=None, config_db=None):
        self.report_dao = report_dao
        self.dw_dao = dw_dao
        
        # Initialize new calculation services
        if config_db and dw_db:
            self.user_calc_service = UserCalculationService(config_db)
            self.system_calc_service = SystemCalculationService(config_db)
            self.report_execution_service = ReportExecutionService(dw_db, config_db)
            self.config_db = config_db
        else:
            # Fallback for when called without DB sessions
            self.user_calc_service = None
            self.system_calc_service = None
            self.report_execution_service = None
            self.config_db = None

    # ===== CALCULATION MANAGEMENT =====

    def get_available_calculations(self, scope: ReportScope) -> List[AvailableCalculation]:
        """Get available calculations for report configuration based on scope."""
        if not self.user_calc_service:
            raise HTTPException(status_code=500, detail="Calculation services not available")

        available_calcs = []
        group_level = GroupLevel.DEAL if scope == ReportScope.DEAL else GroupLevel.TRANCHE

        # Get user-defined calculations
        user_calcs = self.user_calc_service.get_all_user_calculations(group_level.value)
        for calc in user_calcs:
            available_calcs.append(AvailableCalculation(
                id=calc.id,
                name=calc.name,
                description=calc.description,
                aggregation_function=calc.aggregation_function.value,
                source_model=calc.source_model.value,
                source_field=calc.source_field,
                group_level=calc.group_level.value,
                weight_field=calc.weight_field,
                scope=scope,
                category=self._categorize_user_calculation(calc),
                is_default=calc.name in ["Total Ending Balance", "Average Pass Through Rate"],
            ))

        # Get approved system calculations
        system_calcs = self.system_calc_service.get_all_system_calculations(group_level.value)
        for calc in system_calcs:
            if calc.is_approved():
                available_calcs.append(AvailableCalculation(
                    id=calc.id,
                    name=calc.name,
                    description=calc.description,
                    aggregation_function=None,
                    source_model=None,
                    source_field=None,
                    group_level=calc.group_level.value,
                    weight_field=None,
                    scope=scope,
                    category="Custom SQL Calculations",
                    is_default=False,
                ))

        # Get static fields
        static_fields = StaticFieldService.get_all_static_fields()
        for field in static_fields:
            field_group_level = "tranche" if field.field_path.startswith(("tranche.", "tranchebal.")) else "deal"
            if (scope == ReportScope.DEAL and field_group_level == "deal") or \
               (scope == ReportScope.TRANCHE and field_group_level in ["deal", "tranche"]):
                available_calcs.append(AvailableCalculation(
                    id=f"static_{field.field_path}",
                    name=field.name,
                    description=field.description,
                    aggregation_function=None,
                    source_model=None,
                    source_field=field.field_path,
                    group_level=field_group_level,
                    weight_field=None,
                    scope=scope,
                    category=self._categorize_static_field(field),
                    is_default=field.name in ["Deal Number", "Tranche ID"],
                ))

        return available_calcs

    def _categorize_user_calculation(self, calc) -> str:
        """Categorize user calculation for UI grouping."""
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

    def _categorize_static_field(self, field) -> str:
        """Categorize static field for UI grouping."""
        if field.field_path.startswith("deal."):
            return "Deal Information"
        elif field.field_path.startswith("tranche."):
            return "Tranche Structure"
        elif field.field_path.startswith("tranchebal."):
            return "Balance & Performance Data"
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
        deal_count = len(report.selected_deals)
        tranche_count = sum(
            (
                len(deal.selected_tranches)
                if deal.selected_tranches
                else len(self.dw_dao.get_tranches_by_dl_nbr(deal.dl_nbr))
            )
            for deal in report.selected_deals
        )

        # Get execution stats
        if self.config_db:
            from app.reporting.models import ReportExecutionLog
            execution_query = self.config_db.query(ReportExecutionLog).filter(
                ReportExecutionLog.report_id == report.id
            )
            total_executions = execution_query.count()
            last_execution = execution_query.order_by(ReportExecutionLog.executed_at.desc()).first()
        else:
            total_executions = 0
            last_execution = None

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
            last_execution_success=last_execution.success if last_execution else None,
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
        report_dict = report_data.model_dump(exclude={"selected_deals", "selected_calculations"})
        report_dict["scope"] = report_data.scope.value
        report = Report(**report_dict)

        # Add selected deals
        for deal_data in report_data.selected_deals:
            report_deal = ReportDeal(dl_nbr=deal_data.dl_nbr)

            if hasattr(deal_data, "selected_tranches") and deal_data.selected_tranches:
                for tranche_data in deal_data.selected_tranches:
                    report_tranche = ReportTranche(
                        dl_nbr=tranche_data.dl_nbr or deal_data.dl_nbr, 
                        tr_id=tranche_data.tr_id
                    )
                    report_deal.selected_tranches.append(report_tranche)

            report.selected_deals.append(report_deal)

        # Add selected calculations
        for calc_data in report_data.selected_calculations:
            report_calc = ReportCalculation(
                calculation_id=str(calc_data.calculation_id),
                display_order=calc_data.display_order
            )
            report.selected_calculations.append(report_calc)

        return report

    def _update_report(self, report: Report, report_data: ReportUpdate) -> None:
        """Update Report entity from update data."""
        update_data = report_data.model_dump(
            exclude_unset=True, exclude={"selected_deals", "selected_calculations"}
        )

        if "scope" in update_data and update_data["scope"]:
            update_data["scope"] = update_data["scope"].value

        for field, value in update_data.items():
            setattr(report, field, value)

        # Update relationships if provided
        if report_data.selected_deals is not None:
            report.selected_deals.clear()
            for deal_data in report_data.selected_deals:
                report_deal = ReportDeal(dl_nbr=deal_data.dl_nbr)

                if hasattr(deal_data, "selected_tranches") and deal_data.selected_tranches:
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
                    calculation_id=str(calc_data.calculation_id),
                    display_order=calc_data.display_order
                )
                report.selected_calculations.append(report_calc)

    # ===== REPORT EXECUTION =====

    async def run_saved_report(self, report_id: int, cycle_code: int) -> List[Dict[str, Any]]:
        """Execute a report using the new calculation system."""
        if not self.report_execution_service:
            raise HTTPException(status_code=500, detail="Report execution service not available")

        report = await self._get_report_or_404(report_id)
        start_time = time.time()

        try:
            # Convert report to calculation requests
            deal_tranche_map, calculation_requests = self._prepare_execution(report)

            # Execute via new system
            result = self.report_execution_service.execute_report(
                calculation_requests,
                deal_tranche_map,
                cycle_code
            )

            # Log execution
            await self._log_execution(
                report_id, cycle_code, "api_user",
                (time.time() - start_time) * 1000,
                len(result['data']), True
            )

            return result['data']

        except Exception as e:
            await self._log_execution(
                report_id, cycle_code, "api_user",
                (time.time() - start_time) * 1000,
                0, False, str(e)
            )
            raise

    def _prepare_execution(self, report: Report) -> tuple[Dict[int, List[str]], List[CalculationRequest]]:
        """Convert report to execution format."""
        # Build deal-tranche mapping
        deal_tranche_map = {}
        for deal in report.selected_deals:
            if deal.selected_tranches:
                deal_tranche_map[deal.dl_nbr] = [rt.tr_id for rt in deal.selected_tranches]
            else:
                # Include all tranches for this deal
                all_tranches = self.dw_dao.get_tranches_by_dl_nbr(deal.dl_nbr)
                deal_tranche_map[deal.dl_nbr] = [t.tr_id for t in all_tranches]

        # Convert to calculation requests
        calculation_requests = []
        for report_calc in report.selected_calculations:
            calc_id = report_calc.calculation_id
            
            if calc_id.startswith("static_"):
                # Static field
                field_path = calc_id.replace("static_", "")
                calc_request = CalculationRequest(
                    calc_type="static_field",
                    field_path=field_path,
                    alias=field_path.replace(".", "_")
                )
            else:
                # Try as integer ID for user/system calculations
                try:
                    numeric_id = int(calc_id)
                    
                    # Check user calculations first
                    user_calc = self.user_calc_service.get_user_calculation_by_id(numeric_id)
                    if user_calc:
                        calc_request = CalculationRequest(
                            calc_type="user_calculation",
                            calc_id=numeric_id,
                            alias=user_calc.name
                        )
                    else:
                        # Try system calculations
                        system_calc = self.system_calc_service.get_system_calculation_by_id(numeric_id)
                        if system_calc:
                            calc_request = CalculationRequest(
                                calc_type="system_calculation",
                                calc_id=numeric_id,
                                alias=system_calc.name
                            )
                        else:
                            continue  # Skip unknown calculations
                except ValueError:
                    continue  # Skip invalid IDs
            
            calculation_requests.append(calc_request)

        if not calculation_requests:
            raise HTTPException(status_code=400, detail="No valid calculations found for report")

        return deal_tranche_map, calculation_requests

    async def preview_report_sql(self, report_id: int, cycle_code: int) -> Dict[str, Any]:
        """Preview SQL for a report."""
        if not self.report_execution_service:
            raise HTTPException(status_code=500, detail="Report execution service not available")

        report = await self._get_report_or_404(report_id)
        deal_tranche_map, calculation_requests = self._prepare_execution(report)

        result = self.report_execution_service.preview_report_sql(
            calculation_requests, deal_tranche_map, cycle_code
        )

        return {
            "template_name": report.name,
            "sql_previews": result['sql_previews'],
            "parameters": result['parameters'],
            "summary": result['summary']
        }

    async def get_execution_logs(self, report_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get execution logs for a report."""
        await self._get_report_or_404(report_id)

        if not self.config_db:
            return []

        from app.reporting.models import ReportExecutionLog
        logs = (
            self.config_db.query(ReportExecutionLog)
            .filter(ReportExecutionLog.report_id == report_id)
            .order_by(ReportExecutionLog.executed_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "id": log.id,
                "cycle_code": log.cycle_code,
                "executed_by": log.executed_by,
                "execution_time_ms": log.execution_time_ms,
                "row_count": log.row_count,
                "success": log.success,
                "error_message": log.error_message,
                "executed_at": log.executed_at,
            }
            for log in logs
        ]

    async def _log_execution(
        self, report_id: int, cycle_code: int, executed_by: str,
        execution_time_ms: float, row_count: int, success: bool,
        error_message: str = None
    ) -> None:
        """Log report execution."""
        if not self.config_db:
            return

        from app.reporting.models import ReportExecutionLog
        log_entry = ReportExecutionLog(
            report_id=report_id, cycle_code=cycle_code, executed_by=executed_by,
            execution_time_ms=execution_time_ms, row_count=row_count,
            success=success, error_message=error_message
        )

        self.config_db.add(log_entry)
        self.config_db.commit()

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
                    "CDB_cdi_file_nme": deal.CDB_cdi_file_nme,
                }
                for deal in deals
            ]
        except Exception as e:
            print(f"Warning: Could not fetch deals: {e}")
            return []

    def get_available_tranches_for_deals(
        self, deal_ids: List[int], cycle_code: Optional[int] = None
    ) -> Dict[int, List[Dict[str, Any]]]:
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