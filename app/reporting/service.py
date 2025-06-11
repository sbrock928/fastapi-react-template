# app/reporting/service.py
"""Refactored reporting service using BaseService to reduce boilerplate code."""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException

from app.core.base_service import BaseService
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


class ReportService(BaseService[Report, ReportCreate, ReportUpdate, ReportRead]):
    """Refactored service for managing reports using BaseService to reduce boilerplate."""

    def __init__(self, report_dao: ReportDAO, dw_dao: DatawarehouseDAO, 
                 user_calc_service: UserCalculationService = None,
                 system_calc_service: SystemCalculationService = None,
                 report_execution_service: ReportExecutionService = None):
        super().__init__(report_dao)
        self.dw_dao = dw_dao
        
        # Store calculation services
        self.user_calc_service = user_calc_service
        self.system_calc_service = system_calc_service
        self.report_execution_service = report_execution_service
        
        # Execution log service will be injected by dependency system
        self.execution_log_service = None

    # ===== BASE SERVICE OVERRIDES =====

    def _to_response(self, record: Report) -> ReportRead:
        """Convert database model to response schema."""
        return ReportRead.model_validate(record)

    def _validate_create(self, create_data: ReportCreate) -> None:
        """Validate data before creation."""
        # Validation is already handled by Pydantic schema validation
        # Add any additional business validation here
        if not create_data.selected_deals:
            raise HTTPException(status_code=400, detail="At least one deal must be selected")
        
        if not create_data.selected_calculations:
            raise HTTPException(status_code=400, detail="At least one calculation must be selected")

    def _validate_update(self, record: Report, update_data: ReportUpdate) -> None:
        """Validate data before update."""
        if update_data.selected_deals is not None and not update_data.selected_deals:
            raise HTTPException(status_code=400, detail="At least one deal must be selected")
        
        if update_data.selected_calculations is not None and not update_data.selected_calculations:
            raise HTTPException(status_code=400, detail="At least one calculation must be selected")

    def _validate_delete(self, record: Report) -> None:
        """Validate before deletion."""
        # Add any business rules for deletion here
        # For example, prevent deletion if report has recent executions
        pass

    def _post_create(self, record: Report, create_data: ReportCreate) -> None:
        """Business logic after creation."""
        # Could log creation, send notifications, etc.
        pass

    def _post_update(self, record: Report, update_data: ReportUpdate) -> None:
        """Business logic after update."""
        # Could log updates, invalidate caches, etc.
        pass

    def _post_delete(self, record: Report) -> None:
        """Business logic after deletion."""
        # Could clean up related data, log deletion, etc.
        pass

    # ===== CUSTOM CRUD METHODS USING DAO DIRECTLY =====

    def get_all_with_relationships(self) -> List[ReportRead]:
        """Get all reports with relationships loaded."""
        reports = self.dao.get_all_with_relationships()
        return [self._to_response(report) for report in reports]

    def get_by_id_with_relationships(self, report_id: int) -> Optional[ReportRead]:
        """Get a report by ID with relationships loaded."""
        report = self.dao.get_by_id_with_relationships(report_id)
        return self._to_response(report) if report else None

    def create_with_relationships(self, report_data: ReportCreate) -> ReportRead:
        """Create a new report with relationships."""
        # Validate using base service method
        self._validate_create(report_data)
        
        # Build report entity
        report = self._build_report(report_data)
        
        # Create using DAO
        created_report = self.dao.create_with_relationships(report)
        
        # Post-creation logic
        self._post_create(created_report, report_data)
        
        return self._to_response(created_report)

    def update_with_relationships(self, report_id: int, report_data: ReportUpdate) -> Optional[ReportRead]:
        """Update a report with relationships."""
        report = self.dao.get_by_id_with_relationships(report_id)
        if not report:
            return None

        # Validate using base service method
        self._validate_update(report, report_data)

        # Update entity
        self._update_report(report, report_data)
        
        # Update using DAO
        updated_report = self.dao.update_with_relationships(report)
        
        # Post-update logic
        self._post_update(updated_report, report_data)
        
        return self._to_response(updated_report)

    def delete_report(self, report_id: int) -> bool:
        """Delete a report (soft delete)."""
        report = self.dao.get_by_id(report_id)
        if not report:
            return False

        # Validate using base service method
        self._validate_delete(report)

        # Use DAO soft delete
        success = self.dao.soft_delete(report_id)
        
        if success:
            self._post_delete(report)
        
        return success

    def get_all_summaries(self) -> List[ReportSummary]:
        """Get all reports with summary information."""
        reports = self.dao.get_all_with_relationships()
        summaries = []
        
        for report in reports:
            summary = self._build_summary(report)
            
            # Add execution statistics if execution log service is available
            if self.execution_log_service:
                try:
                    exec_stats = self.execution_log_service.get_execution_stats_for_report(report.id)
                    summary.total_executions = exec_stats.get("total_executions", 0)
                    summary.last_executed = exec_stats.get("last_execution_date")
                    summary.last_execution_success = (
                        exec_stats.get("successful_executions", 0) > 0 
                        if exec_stats.get("total_executions", 0) > 0 else None
                    )
                except Exception as e:
                    # If execution stats fail, just use defaults
                    print(f"Warning: Could not fetch execution stats for report {report.id}: {e}")
            
            summaries.append(summary)
        
        return summaries

    # ===== CALCULATION MANAGEMENT (UNCHANGED) =====

    def get_available_calculations(self, scope: ReportScope) -> List[AvailableCalculation]:
        """Get available calculations for report configuration based on scope."""
        if not self.user_calc_service or not self.system_calc_service:
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

    # ===== REPORT EXECUTION (UNCHANGED) =====

    def run_saved_report(self, report_id: int, cycle_code: int, executed_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """Execute a report using the new calculation system with proper logging."""
        if not self.report_execution_service:
            raise HTTPException(status_code=500, detail="Report execution service not available")

        report = self._get_report_or_404(report_id)
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

            # Log successful execution
            execution_time_ms = (time.time() - start_time) * 1000
            self._log_execution(
                report_id=report_id,
                cycle_code=cycle_code,
                executed_by=executed_by or "api_user",
                execution_time_ms=execution_time_ms,
                row_count=len(result['data']),
                success=True
            )

            return result['data']

        except Exception as e:
            # Log failed execution
            execution_time_ms = (time.time() - start_time) * 1000
            self._log_execution(
                report_id=report_id,
                cycle_code=cycle_code,
                executed_by=executed_by or "api_user",
                execution_time_ms=execution_time_ms,
                row_count=0,
                success=False,
                error_message=str(e)
            )
            raise

    def preview_report_sql(self, report_id: int, cycle_code: int) -> Dict[str, Any]:
        """Preview SQL for a report."""
        if not self.report_execution_service:
            raise HTTPException(status_code=500, detail="Report execution service not available")

        report = self._get_report_or_404(report_id)
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

    def get_execution_logs(self, report_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get execution logs for a report."""
        self._get_report_or_404(report_id)
        
        if not self.execution_log_service:
            return []  # Return empty if service not available
        
        try:
            return self.execution_log_service.get_execution_logs_for_report(report_id, limit)
        except Exception as e:
            print(f"Warning: Could not fetch execution logs: {e}")
            return []

    # ===== DATA WAREHOUSE ENDPOINTS (UNCHANGED) =====

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

    # ===== PRIVATE HELPER METHODS (UNCHANGED) =====

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

        return ReportSummary(
            id=report.id,
            name=report.name,
            description=report.description,
            scope=ReportScope(report.scope),
            created_by=report.created_by or "system",
            created_date=report.created_date,
            deal_count=deal_count,
            tranche_count=tranche_count,
            calculation_count=len(report.selected_calculations),
            is_active=report.is_active,
            # These will be updated by get_all_summaries if execution log service is available
            total_executions=0,
            last_executed=None,
            last_execution_success=None,
        )

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

        # Add selected calculations with proper calculation_type
        for calc_data in report_data.selected_calculations:
            # Determine calculation_type if not provided
            calculation_type = calc_data.calculation_type
            if not calculation_type:
                calculation_type = self._determine_calculation_type(calc_data.calculation_id)
            
            report_calc = ReportCalculation(
                calculation_id=str(calc_data.calculation_id),
                calculation_type=calculation_type,
                display_order=calc_data.display_order
            )
            report_calc.display_name = self._get_calculation_display_name(report_calc.calculation_id, report_calc.calculation_type)
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
                # Determine calculation_type if not provided
                calculation_type = calc_data.calculation_type
                if not calculation_type:
                    calculation_type = self._determine_calculation_type(calc_data.calculation_id)
                
                report_calc = ReportCalculation(
                    calculation_id=str(calc_data.calculation_id),
                    calculation_type=calculation_type,
                    display_order=calc_data.display_order
                )
                report_calc.display_name = self._get_calculation_display_name(report_calc.calculation_id, report_calc.calculation_type)
                report.selected_calculations.append(report_calc)

    def _get_report_or_404(self, report_id: int) -> Report:
        """Get report or raise 404."""
        report = self.dao.get_by_id_with_relationships(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return report

    def _log_execution(
        self, report_id: int, cycle_code: int, executed_by: str,
        execution_time_ms: float, row_count: int, success: bool,
        error_message: str = None
    ) -> None:
        """Log report execution using the execution log service."""
        if not self.execution_log_service:
            return  # Skip logging if service not available
        
        try:
            self.execution_log_service.log_execution(
                report_id=report_id,
                cycle_code=cycle_code,
                executed_by=executed_by,
                execution_time_ms=execution_time_ms,
                row_count=row_count,
                success=success,
                error_message=error_message
            )
        except Exception as e:
            print(f"Warning: Could not log execution: {e}")
            # Don't raise the exception as it's not critical to the main operation

    # ===== CALCULATION HELPER METHODS (UNCHANGED) =====

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

    def _get_calculation_display_name(self, calculation_id: str, calculation_type: str) -> str:
        """Get the display name for a calculation based on its ID and type."""
        # Handle static fields
        if calculation_id.startswith("static_"):
            field_path = calculation_id.replace("static_", "")
            # Try to get the actual field name from static fields
            static_fields = StaticFieldService.get_all_static_fields()
            for field in static_fields:
                if field.field_path == field_path:
                    return field.name
            # Fallback to field path if not found
            return field_path
        
        # Handle numeric calculation IDs
        try:
            numeric_id = int(calculation_id)
            
            if calculation_type == "user_calculation" or calculation_type == "user":
                if self.user_calc_service:
                    user_calc = self.user_calc_service.get_user_calculation_by_id(numeric_id)
                    if user_calc:
                        return user_calc.name
            
            elif calculation_type == "system_calculation" or calculation_type == "system":
                if self.system_calc_service:
                    system_calc = self.system_calc_service.get_system_calculation_by_id(numeric_id)
                    if system_calc:
                        return system_calc.name
            
            # Auto-detect if calculation_type is missing or unknown
            if self.user_calc_service:
                user_calc = self.user_calc_service.get_user_calculation_by_id(numeric_id)
                if user_calc:
                    return user_calc.name
            
            if self.system_calc_service:
                system_calc = self.system_calc_service.get_system_calculation_by_id(numeric_id)
                if system_calc:
                    return system_calc.name
                    
        except ValueError:
            pass
        
        # Fallback to calculation_id if we can't resolve the name
        return calculation_id

    def _determine_calculation_type(self, calculation_id) -> str:
        """Determine the calculation type based on the calculation_id."""
        calc_id_str = str(calculation_id)
        
        # Handle static fields
        if calc_id_str.startswith("static_"):
            return "static_field"
        
        # Handle numeric IDs
        try:
            numeric_id = int(calc_id_str)
            
            # Check if it's a user calculation
            if self.user_calc_service:
                user_calc = self.user_calc_service.get_user_calculation_by_id(numeric_id)
                if user_calc:
                    return "user_calculation"
            
            # Check if it's a system calculation
            if self.system_calc_service:
                system_calc = self.system_calc_service.get_system_calculation_by_id(numeric_id)
                if system_calc:
                    return "system_calculation"
            
            # Default to user_calculation if we can't determine (for backwards compatibility)
            return "user_calculation"
            
        except ValueError:
            # Non-numeric, non-static ID - default to user_calculation
            return "user_calculation"

    def _prepare_execution(self, report: Report) -> tuple[Dict[int, List[str]], List[CalculationRequest]]:
        """Convert report to execution format with enhanced calculation type detection."""
        # Build deal-tranche mapping
        deal_tranche_map = {}
        for deal in report.selected_deals:
            if deal.selected_tranches:
                deal_tranche_map[deal.dl_nbr] = [rt.tr_id for rt in deal.selected_tranches]
            else:
                # Include all tranches for this deal
                all_tranches = self.dw_dao.get_tranches_by_dl_nbr(deal.dl_nbr)
                deal_tranche_map[deal.dl_nbr] = [t.tr_id for t in all_tranches]

        # Convert to calculation requests with improved logic
        calculation_requests = []
        for report_calc in report.selected_calculations:
            calc_id_str = report_calc.calculation_id
            calc_type = getattr(report_calc, 'calculation_type', None)
            
            # Handle static fields (they always start with "static_")
            if calc_id_str.startswith("static_"):
                field_path = calc_id_str.replace("static_", "")
                calc_request = CalculationRequest(
                    calc_type="static_field",
                    field_path=field_path,
                    alias=field_path.replace(".", "_")
                )
                calculation_requests.append(calc_request)
                continue
            
            # Handle numeric calculation IDs
            try:
                numeric_id = int(calc_id_str)
            except ValueError:
                # Skip non-numeric, non-static IDs
                print(f"Warning: Skipping invalid calculation_id: {calc_id_str}")
                continue
                
            calc_request = None
            
            # If calculation_type is explicitly set, use it
            if calc_type == "user_calculation":
                user_calc = self.user_calc_service.get_user_calculation_by_id(numeric_id)
                if user_calc:
                    calc_request = CalculationRequest(
                        calc_type="user_calculation",
                        calc_id=numeric_id,
                        alias=user_calc.name
                    )
            elif calc_type == "system_calculation":
                system_calc = self.system_calc_service.get_system_calculation_by_id(numeric_id)
                if system_calc:
                    calc_request = CalculationRequest(
                        calc_type="system_calculation",
                        calc_id=numeric_id,
                        alias=system_calc.name
                    )
            else:
                # calculation_type is NULL or missing - try to auto-detect
                # This handles the legacy data issue
                print(f"Warning: calculation_type is NULL for calc_id {numeric_id}, attempting auto-detection")
                
                # Check user calculations first
                user_calc = self.user_calc_service.get_user_calculation_by_id(numeric_id)
                if user_calc:
                    calc_request = CalculationRequest(
                        calc_type="user_calculation",
                        calc_id=numeric_id,
                        alias=user_calc.name
                    )
                    print(f"Auto-detected as user_calculation: {user_calc.name}")
                else:
                    # Try system calculations
                    system_calc = self.system_calc_service.get_system_calculation_by_id(numeric_id)
                    if system_calc:
                        calc_request = CalculationRequest(
                            calc_type="system_calculation",
                            calc_id=numeric_id,
                            alias=system_calc.name
                        )
                        print(f"Auto-detected as system_calculation: {system_calc.name}")
                    else:
                        print(f"Warning: No calculation found with ID {numeric_id}")
            
            if calc_request:
                calculation_requests.append(calc_request)

        if not calculation_requests:
            print("Debug: No valid calculations found. Report calculations:")
            for report_calc in report.selected_calculations:
                print(f"  - ID: {report_calc.calculation_id}, Type: {getattr(report_calc, 'calculation_type', 'NULL')}")
            raise HTTPException(status_code=400, detail="No valid calculations found for report")

        print(f"Debug: Successfully prepared {len(calculation_requests)} calculation requests")
        return deal_tranche_map, calculation_requests