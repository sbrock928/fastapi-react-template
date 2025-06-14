# app/reporting/service.py - Complete service with all original functionality + column management

import time
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from datetime import datetime

from app.reporting.dao import ReportDAO
from app.datawarehouse.dao import DatawarehouseDAO
from app.reporting.models import Report, ReportExecutionLog
from app.reporting.schemas import (
    ReportRead, ReportCreate, ReportUpdate, ReportSummary, AvailableCalculation, ReportScope,
    ReportColumnPreferences, ColumnPreference, ColumnFormat
)
from app.calculations.resolver import CalculationRequest
from app.calculations.service import (
    UserCalculationService, 
    SystemCalculationService, 
    StaticFieldService,
    ReportExecutionService
)
from app.calculations.models import GroupLevel


class ReportService:
    """Complete report service with calculation management and column preferences support."""

    def __init__(self, report_dao: ReportDAO, dw_dao: DatawarehouseDAO, 
                 user_calc_service: UserCalculationService = None,
                 system_calc_service: SystemCalculationService = None,
                 report_execution_service: Optional[ReportExecutionService] = None):
        self.report_dao = report_dao
        self.dw_dao = dw_dao
        
        # Store calculation services
        self.user_calc_service = user_calc_service
        self.system_calc_service = system_calc_service
        self.report_execution_service = report_execution_service

    # ===== CORE CRUD OPERATIONS =====

    async def get_all(self) -> List[ReportRead]:
        """Get all reports."""
        reports = await self.report_dao.get_all()
        return [ReportRead.model_validate(report) for report in reports]

    async def get_by_id(self, report_id: int) -> Optional[ReportRead]:
        """Get a report by ID with parsed column preferences."""
        report = await self.report_dao.get_by_id(report_id)
        if not report:
            return None
            
        # Create a copy for the response without modifying the original database object
        report_dict = {
            'id': report.id,
            'name': report.name,
            'description': report.description,
            'scope': report.scope,
            'created_by': report.created_by,
            'is_active': report.is_active,
            'created_date': report.created_date,
            'updated_date': report.updated_date,
            'selected_deals': report.selected_deals,
            'selected_calculations': report.selected_calculations,
            'column_preferences': None
        }
        
        # Parse column preferences from JSON for the response only
        if report.column_preferences:
            try:
                report_dict['column_preferences'] = ReportColumnPreferences(**report.column_preferences)
            except Exception as e:
                print(f"Warning: Could not parse column preferences for report {report_id}: {e}")
                report_dict['column_preferences'] = None
        
        return ReportRead.model_validate(report_dict)

    async def get_all_summaries(self) -> List[ReportSummary]:
        """Get all reports with summary information."""
        reports = await self.report_dao.get_all()
        return [self._build_summary(report) for report in reports]

    def _build_summary(self, report: Report) -> ReportSummary:
        """Build summary for a single report."""
        return ReportSummary(
            id=report.id,
            name=report.name,
            description=report.description,
            scope=ReportScope(report.scope),
            created_by=report.created_by,
            created_date=report.created_date,
            deal_count=len(report.selected_deals),
            tranche_count=sum(len(deal.selected_tranches) for deal in report.selected_deals),
            calculation_count=len(report.selected_calculations),
            is_active=report.is_active,
            # TODO: Add execution statistics from execution logs
            total_executions=0,
            last_executed=None,
            last_execution_success=None
        )

    async def create(self, report_data: ReportCreate) -> ReportRead:
        """Create a new report with column preferences."""
        # Convert column preferences to JSON format for storage
        column_prefs_json = None
        if report_data.column_preferences:
            column_prefs_json = report_data.column_preferences.model_dump()

        report = await self.report_dao.create(report_data, column_prefs_json)
        return ReportRead.model_validate(report)

    async def update(self, report_id: int, report_data: ReportUpdate) -> ReportRead:
        """Update an existing report with column preferences."""
        # Convert column preferences to JSON format for storage
        column_prefs_json = None
        if report_data.column_preferences:
            column_prefs_json = report_data.column_preferences.model_dump()

        report = await self.report_dao.update(report_id, report_data, column_prefs_json)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return ReportRead.model_validate(report)

    async def delete(self, report_id: int) -> bool:
        """Delete a report."""
        return await self.report_dao.delete(report_id)

    # ===== CALCULATION MANAGEMENT =====

    def get_available_calculations_for_scope(self, scope: ReportScope) -> List[AvailableCalculation]:
        """Get all available calculations for a given report scope."""
        available_calcs = []

        # Add user calculations with new format
        if self.user_calc_service:
            user_calcs = self.user_calc_service.get_all_user_calculations()
            for calc in user_calcs:
                if self._is_calculation_compatible_with_scope(calc.group_level.value, scope):
                    available_calcs.append(AvailableCalculation(
                        id=f"user.{calc.source_field}",  # NEW FORMAT
                        name=calc.name,
                        description=calc.description,
                        aggregation_function=calc.aggregation_function.value,
                        source_model=calc.source_model.value,
                        source_field=calc.source_field,
                        group_level=calc.group_level.value,
                        weight_field=calc.weight_field,
                        scope=scope,
                        category=self._categorize_user_calculation(calc),
                        is_default=False,
                        calculation_type="USER_DEFINED"
                    ))

        # Add system calculations with new format
        if self.system_calc_service:
            system_calcs = self.system_calc_service.get_all_system_calculations()
            for calc in system_calcs:
                if self._is_calculation_compatible_with_scope(calc.group_level.value, scope):
                    available_calcs.append(AvailableCalculation(
                        id=f"system.{calc.result_column_name}",  # NEW FORMAT
                        name=calc.name,
                        description=calc.description,
                        aggregation_function=None,
                        source_model=None,
                        source_field=calc.result_column_name,
                        group_level=calc.group_level.value,
                        weight_field=None,
                        scope=scope,
                        category="System Calculations",
                        is_default=False,
                        calculation_type="SYSTEM_SQL"
                    ))

        # Add static fields (keep existing format)
        static_fields = StaticFieldService.get_all_static_fields()
        for field in static_fields:
            field_group_level = "tranche" if any(field.field_path.startswith(prefix) 
                                               for prefix in ("tranche.", "tranchebal.")) else "deal"
            if (scope == ReportScope.DEAL and field_group_level == "deal") or \
               (scope == ReportScope.TRANCHE and field_group_level in ["deal", "tranche"]):
                available_calcs.append(AvailableCalculation(
                    id=f"static_{field.field_path}",  # KEEP EXISTING FORMAT
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
                    calculation_type="STATIC_FIELD"
                ))

        return available_calcs

    def _is_calculation_compatible_with_scope(self, calc_group_level: str, scope: ReportScope) -> bool:
        """Check if a calculation is compatible with the given report scope."""
        if scope == ReportScope.DEAL:
            return calc_group_level == "deal"
        elif scope == ReportScope.TRANCHE:
            return calc_group_level in ["deal", "tranche"]
        return False

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
        """Get the display name for a calculation with new format."""
        
        # Handle new user calculation format
        if calculation_id.startswith("user."):
            source_field = calculation_id[5:]
            if self.user_calc_service:
                user_calc = self.user_calc_service.get_user_calculation_by_source_field(source_field)
                if user_calc:
                    return user_calc.name
            return f"User Calc: {source_field}"
        
        # Handle new system calculation format
        elif calculation_id.startswith("system."):
            result_column = calculation_id[7:]
            if self.system_calc_service:
                system_calc = self.system_calc_service.get_system_calculation_by_result_column(result_column)
                if system_calc:
                    return system_calc.name
            return f"System Calc: {result_column}"
        
        # Handle static fields
        elif calculation_id.startswith("static_"):
            field_path = calculation_id.replace("static_", "")
            static_fields = StaticFieldService.get_all_static_fields()
            for field in static_fields:
                if field.field_path == field_path:
                    return field.name
            return field_path
        
        # Legacy numeric ID handling
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
        
        # Fallback
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

    # ===== REPORT EXECUTION WITH COLUMN MANAGEMENT =====

    async def run_report(self, report_id: int, cycle_code: int) -> List[Dict[str, Any]]:
        """Execute report with column preferences applied."""
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

            print(f"Debug: Raw data before column preferences: {result['data'][:1] if result['data'] else 'No data'}")

            # Apply column preferences to the result
            formatted_data = self._apply_column_preferences(result['data'], report)

            # Log execution
            await self._log_execution(
                report_id, cycle_code, "api_user",
                (time.time() - start_time) * 1000,
                len(formatted_data), True
            )

            return formatted_data

        except Exception as e:
            await self._log_execution(
                report_id, cycle_code, "api_user",
                (time.time() - start_time) * 1000,
                0, False, str(e)
            )
            raise

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

    async def _log_execution(self, report_id: int, cycle_code: int, executed_by: str,
                            execution_time_ms: float, row_count: int, success: bool,
                            error_message: str = None) -> None:
        """Log report execution."""
        execution_log = ReportExecutionLog(
            report_id=report_id,
            cycle_code=cycle_code,
            executed_by=executed_by,
            execution_time_ms=execution_time_ms,
            row_count=row_count,
            success=success,
            error_message=error_message,
            executed_at=datetime.now()
        )
        
        await self.report_dao.create_execution_log(execution_log)

    def _apply_column_preferences(self, raw_data: List[Dict[str, Any]], 
                                  report: Report) -> List[Dict[str, Any]]:
        """Apply column preferences to format and filter output data."""
        if not raw_data:
            return raw_data

        # Use the parsed column preferences attached to the report
        column_prefs = getattr(report, '_parsed_column_preferences', None)
        
        # If no column preferences, return data as-is
        if not column_prefs:
            return raw_data

        # Build column mapping and formatting rules
        column_mapping = {}
        format_rules = {}
        visible_columns = set()
        
        # Create a mapping from calculation IDs to display names for user/system calculations
        calc_id_to_display_name = {}
        for report_calc in report.selected_calculations:
            calc_id = report_calc.calculation_id
            calc_type = getattr(report_calc, 'calculation_type', None)
            display_name = self._get_calculation_display_name(calc_id, calc_type)
            calc_id_to_display_name[calc_id] = display_name
        
        for col_pref in column_prefs.columns:
            if col_pref.is_visible:
                column_id = col_pref.column_id
                
                # Handle different types of columns
                if column_id.startswith("static_") or column_id.replace(".", "_") in ["deal_number", "tranche_id", "cycle_code"]:
                    # Static fields - convert dots to underscores for raw data lookup
                    raw_data_key = column_id.replace(".", "_")
                elif column_id in calc_id_to_display_name:
                    # User/system calculations - use the display name as the key
                    raw_data_key = calc_id_to_display_name[column_id]
                else:
                    # Default case - use column_id as is
                    raw_data_key = column_id
                
                column_mapping[raw_data_key] = col_pref.display_name
                format_rules[raw_data_key] = col_pref.format_type
                visible_columns.add(raw_data_key)

        # Handle default columns based on report scope, but respect visibility settings
        if report.scope == "DEAL":
            default_columns = {'deal_number', 'cycle_code'}
        else:  # TRANCHE scope
            default_columns = {'deal_number', 'tranche_id', 'cycle_code'}
        
        # Create a set of explicitly hidden columns from column preferences
        hidden_columns = set()
        for col_pref in column_prefs.columns:
            if not col_pref.is_visible:
                # Convert column_id to raw_data_key format for comparison
                if col_pref.column_id.startswith("static_") or col_pref.column_id.replace(".", "_") in ["deal_number", "tranche_id", "cycle_code"]:
                    hidden_columns.add(col_pref.column_id.replace(".", "_"))
                else:
                    hidden_columns.add(col_pref.column_id)
            
        if column_prefs.include_default_columns:
            for col in default_columns:
                # Only add default columns if they're not explicitly hidden and not already visible
                if col not in visible_columns and col not in hidden_columns and col in raw_data[0]:
                    visible_columns.add(col)
                    if col not in column_mapping:
                        column_mapping[col] = col.replace('_', ' ').title()

        # Process each row
        formatted_data = []
        for row in raw_data:
            formatted_row = {}
            
            # Only include visible columns
            for original_col, value in row.items():
                if original_col in visible_columns:
                    display_name = column_mapping.get(original_col, original_col)
                    format_type = format_rules.get(original_col, ColumnFormat.TEXT)
                    
                    # Apply formatting
                    formatted_value = self._format_value(value, format_type)
                    formatted_row[display_name] = formatted_value
            
            formatted_data.append(formatted_row)

        # Sort columns by display_order if specified
        if column_prefs.columns:
            ordered_columns = sorted(
                [col for col in column_prefs.columns if col.is_visible],
                key=lambda x: x.display_order
            )
            
            # Reorder each row based on column preferences
            reordered_data = []
            for row in formatted_data:
                reordered_row = {}
                
                # Add columns in preference order
                for col_pref in ordered_columns:
                    display_name = col_pref.display_name
                    if display_name in row:
                        reordered_row[display_name] = row[display_name]
                
                # Add any remaining columns not in preferences
                for key, value in row.items():
                    if key not in reordered_row:
                        reordered_row[key] = value
                
                reordered_data.append(reordered_row)
            
            formatted_data = reordered_data

        return formatted_data

    def _format_value(self, value: Any, format_type: ColumnFormat) -> Any:
        """Format a single value according to the specified format type."""
        if value is None:
            return None

        try:
            if format_type == ColumnFormat.CURRENCY:
                if isinstance(value, (int, float)):
                    return f"${value:,.2f}"
                return value
            
            elif format_type == ColumnFormat.PERCENTAGE:
                if isinstance(value, (int, float)):
                    return f"{value:.1f}%"
                return value
            
            elif format_type == ColumnFormat.NUMBER:
                if isinstance(value, (int, float)):
                    return f"{value:,}"
                return value
            
            elif format_type == ColumnFormat.DATE_MDY:
                if isinstance(value, datetime):
                    return value.strftime("%m/%d/%Y")
                elif isinstance(value, str):
                    # Try to parse and reformat
                    try:
                        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        return dt.strftime("%m/%d/%Y")
                    except:
                        return value
                return value
            
            elif format_type == ColumnFormat.DATE_DMY:
                if isinstance(value, datetime):
                    return value.strftime("%d/%m/%Y")
                elif isinstance(value, str):
                    try:
                        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        return dt.strftime("%d/%m/%Y")
                    except:
                        return value
                return value
            
            else:  # TEXT or unknown
                return value
                
        except Exception as e:
            print(f"Warning: Could not format value {value} with format {format_type}: {e}")
            return value

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
        
        # Add default columns if requested (NEW LOGIC)
        include_defaults = True
        column_prefs = getattr(report, '_parsed_column_preferences', None)
        if column_prefs:
            include_defaults = column_prefs.include_default_columns
        
        if include_defaults:
            # Add the automatic backend columns
            default_fields = [
                ("deal.dl_nbr", "deal_number"),
                ("tranche.tr_id", "tranche_id") if report.scope == "TRANCHE" else None,
                ("tranchebal.cycle_cde", "cycle_code")
            ]
            
            for field_info in default_fields:
                if field_info:  # Skip None entries
                    field_path, alias = field_info
                    calc_request = CalculationRequest(
                        calc_type="static_field",
                        field_path=field_path,
                        alias=alias
                    )
                    calculation_requests.append(calc_request)

        # Add user-selected calculations with enhanced auto-detection
        for report_calc in report.selected_calculations:
            calc_id_str = report_calc.calculation_id
            calc_type = getattr(report_calc, 'calculation_type', None)
            
            print(f"Debug: Processing calculation - ID: {calc_id_str}, Type: {calc_type}")
            
            # Handle static fields - check calculation_type first, then fallback to "static_" prefix
            if calc_type == "static" or calc_id_str.startswith("static_"):
                if calc_type == "static":
                    # The calc_id_str IS the field path for static type, but may have "static_" prefix
                    if calc_id_str.startswith("static_"):
                        field_path = calc_id_str.replace("static_", "")
                    else:
                        field_path = calc_id_str
                    # Use the calculation_id as the alias, but replace dots with underscores for valid SQL
                    alias = calc_id_str.replace(".", "_")
                else:
                    # The calc_id_str has "static_" prefix, remove it
                    field_path = calc_id_str.replace("static_", "")
                    alias = calc_id_str.replace(".", "_")
                    
                calc_request = CalculationRequest(
                    calc_type="static_field",
                    field_path=field_path,
                    alias=alias
                )
                calculation_requests.append(calc_request)
                print(f"Debug: Added static field request - Field: {field_path}, Alias: {alias}")
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
            if calc_type == "user_calculation" or calc_type == "user":
                if self.user_calc_service:
                    user_calc = self.user_calc_service.get_user_calculation_by_id(numeric_id)
                    if user_calc:
                        calc_request = CalculationRequest(
                            calc_type="user_calculation",
                            calc_id=numeric_id,
                            alias=user_calc.name
                        )
            elif calc_type == "system_calculation" or calc_type == "system":
                if self.system_calc_service:
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
                if self.user_calc_service:
                    user_calc = self.user_calc_service.get_user_calculation_by_id(numeric_id)
                    if user_calc:
                        calc_request = CalculationRequest(
                            calc_type="user_calculation",
                            calc_id=numeric_id,
                            alias=user_calc.name
                        )
                        print(f"Auto-detected as user_calculation: {user_calc.name}")
                
                if not calc_request and self.system_calc_service:
                    # Try system calculations
                    system_calc = self.system_calc_service.get_system_calculation_by_id(numeric_id)
                    if system_calc:
                        calc_request = CalculationRequest(
                            calc_type="system_calculation",
                            calc_id=numeric_id,
                            alias=system_calc.name
                        )
                        print(f"Auto-detected as system_calculation: {system_calc.name}")
                
                if not calc_request:
                    print(f"Warning: No calculation found with ID {numeric_id}")
            
            if calc_request:
                calculation_requests.append(calc_request)

        if not calculation_requests:
            print("Debug: No valid calculations found for report")
            print(f"Report calculations:")
            for report_calc in report.selected_calculations:
                print(f"  - ID: {report_calc.calculation_id}, Type: {getattr(report_calc, 'calculation_type', 'NULL')}")
            raise HTTPException(status_code=400, detail="No valid calculations found for report")

        print(f"Debug: Successfully prepared {len(calculation_requests)} calculation requests")
        return deal_tranche_map, calculation_requests

    def _prepare_calculations_for_report(self, report, cycle_code: int):
        """Enhanced preparation with new calculation_id format."""
        
        # Build deal-tranche mapping
        deal_tranche_map = {}
        for deal in report.selected_deals:
            if deal.selected_tranches:
                deal_tranche_map[deal.dl_nbr] = [rt.tr_id for rt in deal.selected_tranches]
            else:
                all_tranches = self.dw_dao.get_tranches_by_dl_nbr(deal.dl_nbr)
                deal_tranche_map[deal.dl_nbr] = [t.tr_id for t in all_tranches]

        # Convert to calculation requests with new parsing logic
        calculation_requests = []
        
        # Add default columns if requested
        include_defaults = True
        column_prefs = getattr(report, '_parsed_column_preferences', None)
        if column_prefs:
            include_defaults = column_prefs.include_default_columns
        
        if include_defaults:
            default_fields = [
                ("deal.dl_nbr", "deal_number"),
                ("tranche.tr_id", "tranche_id") if report.scope == "TRANCHE" else None,
                ("tranchebal.cycle_cde", "cycle_code")
            ]
            
            for field_info in default_fields:
                if field_info:
                    field_path, alias = field_info
                    calc_request = CalculationRequest(
                        calc_type="static_field",
                        field_path=field_path,
                        alias=alias
                    )
                    calculation_requests.append(calc_request)

        # Process user-selected calculations with NEW PARSING LOGIC
        for report_calc in report.selected_calculations:
            calc_id_str = report_calc.calculation_id
            calc_type = getattr(report_calc, 'calculation_type', None)
            
            print(f"Debug: Processing calculation - ID: {calc_id_str}, Type: {calc_type}")
            
            calc_request = None
            
            # Parse new calculation_id formats
            if calc_id_str.startswith("user."):
                # User calculation: "user.{source_field}"
                source_field = calc_id_str[5:]  # Remove "user." prefix
                if self.user_calc_service:
                    user_calc = self.user_calc_service.get_user_calculation_by_source_field(source_field)
                    if user_calc:
                        calc_request = CalculationRequest(
                            calc_type="user_calculation",
                            calc_id=user_calc.id,
                            alias=user_calc.name
                        )
                        print(f"Debug: Found user calculation - {user_calc.name} for source_field: {source_field}")
                    else:
                        print(f"Warning: No user calculation found with source_field: {source_field}")
            
            elif calc_id_str.startswith("system."):
                # System calculation: "system.{result_column_name}"
                result_column = calc_id_str[7:]  # Remove "system." prefix
                if self.system_calc_service:
                    system_calc = self.system_calc_service.get_system_calculation_by_result_column(result_column)
                    if system_calc:
                        calc_request = CalculationRequest(
                            calc_type="system_calculation",
                            calc_id=system_calc.id,
                            alias=system_calc.name
                        )
                        print(f"Debug: Found system calculation - {system_calc.name} for result_column: {result_column}")
                    else:
                        print(f"Warning: No system calculation found with result_column: {result_column}")
            
            elif calc_id_str.startswith("static_"):
                # Static field: "static_{table}.{field_name}"
                field_path = calc_id_str.replace("static_", "")
                alias = calc_id_str.replace(".", "_")
                
                calc_request = CalculationRequest(
                    calc_type="static_field",
                    field_path=field_path,
                    alias=alias
                )
                print(f"Debug: Added static field request - Field: {field_path}, Alias: {alias}")
            
            else:
                # Legacy numeric ID handling
                try:
                    numeric_id = int(calc_id_str)
                    
                    if calc_type == "user_calculation" or calc_type == "user":
                        if self.user_calc_service:
                            user_calc = self.user_calc_service.get_user_calculation_by_id(numeric_id)
                            if user_calc:
                                calc_request = CalculationRequest(
                                    calc_type="user_calculation",
                                    calc_id=numeric_id,
                                    alias=user_calc.name
                                )
                    elif calc_type == "system_calculation" or calc_type == "system":
                        if self.system_calc_service:
                            system_calc = self.system_calc_service.get_system_calculation_by_id(numeric_id)
                            if system_calc:
                                calc_request = CalculationRequest(
                                    calc_type="system_calculation",
                                    calc_id=numeric_id,
                                    alias=system_calc.name
                                )
                    else:
                        # Auto-detect for legacy data
                        if self.user_calc_service:
                            user_calc = self.user_calc_service.get_user_calculation_by_id(numeric_id)
                            if user_calc:
                                calc_request = CalculationRequest(
                                    calc_type="user_calculation",
                                    calc_id=numeric_id,
                                    alias=user_calc.name
                                )
                        
                        if not calc_request and self.system_calc_service:
                            # Try system calculations
                            system_calc = self.system_calc_service.get_system_calculation_by_id(numeric_id)
                            if system_calc:
                                calc_request = CalculationRequest(
                                    calc_type="system_calculation",
                                    calc_id=numeric_id,
                                    alias=system_calc.name
                                )
                except ValueError:
                    print(f"Warning: Unknown calculation_id format: {calc_id_str}")
            
            if calc_request:
                calculation_requests.append(calc_request)

        if not calculation_requests:
            print("Debug: No valid calculations found for report")
            raise HTTPException(status_code=400, detail="No valid calculations found for report")

        print(f"Debug: Successfully prepared {len(calculation_requests)} calculation requests")
        return deal_tranche_map, calculation_requests

    # ===== DATA RETRIEVAL METHODS =====

    def get_available_deals(self) -> List[Dict[str, Any]]:
        """Get available deals from the data warehouse."""
        deals = self.dw_dao.get_all_deals()
        # Convert SQLAlchemy model objects to dictionaries
        return [
            {
                "dl_nbr": deal.dl_nbr,
                "issr_cde": deal.issr_cde,
                "cdi_file_nme": deal.cdi_file_nme,
                "CDB_cdi_file_nme": deal.CDB_cdi_file_nme
            }
            for deal in deals
        ]

    def get_available_tranches_for_deals(self, deal_ids: List[int], 
                                       cycle_code: int = None) -> Dict[int, List[Dict[str, Any]]]:
        """Get available tranches for specific deals."""
        return self.dw_dao.get_available_tranches_for_deals(deal_ids, cycle_code)

    def get_available_cycles(self) -> List[Dict[str, str]]:
        """Get available cycles from the data warehouse."""
        return self.dw_dao.get_available_cycles()

    async def _get_report_or_404(self, report_id: int) -> Report:
        """Get report or raise 404."""
        raw_report = await self.report_dao.get_by_id(report_id)
        if not raw_report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Parse column preferences for internal use
        if raw_report.column_preferences and isinstance(raw_report.column_preferences, dict):
            try:
                parsed_column_prefs = ReportColumnPreferences(**raw_report.column_preferences)
                raw_report._parsed_column_preferences = parsed_column_prefs
            except Exception as e:
                print(f"Warning: Could not parse column preferences for report {report_id}: {e}")
                raw_report._parsed_column_preferences = None
        else:
            raw_report._parsed_column_preferences = None
        
        return raw_report