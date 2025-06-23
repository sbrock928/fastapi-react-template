# app/reporting/service.py - Complete service with all original functionality + column management

import time
import logging
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
from app.calculations import (
    UnifiedCalculationService as UserCalculationService,
    UnifiedCalculationService as SystemCalculationService, 
    UnifiedCalculationService as ReportExecutionService
)
from app.calculations.models import GroupLevel, CalculationType


logger = logging.getLogger(__name__)

# Helper class to provide static field functionality using Field Introspection Service
class StaticFieldHelper:
    """Helper class to work with static field information using dynamic field introspection."""
    
    @staticmethod
    def get_all_static_fields():
        """Get all static fields from the Field Introspection Service."""
        from app.calculations.field_introspection import FieldIntrospectionService
        
        fields = FieldIntrospectionService.get_available_fields()
        # Convert to the expected format
        field_objects = []
        for field in fields:
            field_obj = type('StaticField', (), {
                'field_path': field['field_path'],
                'name': field['name'],
                'description': field['description'],
                'type': field['type'],
                'required_models': field.get('required_models', ["Deal"]),
                'nullable': field.get('nullable', True)
            })()
            field_objects.append(field_obj)
        return field_objects
    
    @staticmethod
    def get_static_field_by_path(field_path: str):
        """Get a single static field by its path using Field Introspection Service."""
        from app.calculations.field_introspection import FieldIntrospectionService
        
        fields = FieldIntrospectionService.get_available_fields()
        for field in fields:
            if field['field_path'] == field_path:
                return type('StaticField', (), {
                    'field_path': field['field_path'],
                    'name': field['name'],
                    'description': field['description'],
                    'type': field['type'],
                    'required_models': field.get('required_models', ["Deal"]),
                    'nullable': field.get('nullable', True)
                })()
        
        # Fallback for unknown fields
        return type('StaticField', (), {
            'field_path': field_path,
            'name': field_path,
            'description': f"Field {field_path}",
            'type': "unknown",
            'required_models': ["Deal"],
            'nullable': True
        })()

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
        
        # If calculations are being updated but column preferences aren't provided,
        # we need to synchronize the column preferences with the new calculations
        if (hasattr(report_data, 'selected_calculations') and 
            report_data.selected_calculations is not None and 
            column_prefs_json is None):
            
            # Get the existing report to check its current column preferences
            existing_report = await self.report_dao.get_by_id(report_id)
            if existing_report and existing_report.column_preferences:
                try:
                    existing_prefs = ReportColumnPreferences(**existing_report.column_preferences)
                    # Synchronize column preferences with new calculations
                    column_prefs_json = self._synchronize_column_preferences_with_calculations(
                        existing_prefs, report_data.selected_calculations, report_data.scope or existing_report.scope
                    ).model_dump()
                except Exception as e:
                    print(f"Warning: Could not synchronize column preferences: {e}")

        report = await self.report_dao.update(report_id, report_data, column_prefs_json)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return ReportRead.model_validate(report)

    def _synchronize_column_preferences_with_calculations(self, 
                                                         existing_prefs: ReportColumnPreferences,
                                                         new_calculations: List,
                                                         report_scope: str) -> ReportColumnPreferences:
        """Synchronize column preferences to match new selected calculations."""
        # Get current calculation IDs from new calculations
        new_calc_ids = set(calc.calculation_id for calc in new_calculations)
        
        # Define default columns based on scope
        default_column_ids = {'deal_number', 'cycle_code'}
        if report_scope == 'TRANCHE':
            default_column_ids.add('tranche_id')
        
        # Filter existing column preferences to only keep:
        # 1. Default columns (always kept)
        # 2. Columns for calculations that are still selected
        updated_columns = []
        for col_pref in existing_prefs.columns:
            if (col_pref.column_id in default_column_ids or 
                col_pref.column_id in new_calc_ids):
                updated_columns.append(col_pref)
        
        # Add column preferences for any new calculations that don't have preferences yet
        existing_column_ids = set(col.column_id for col in updated_columns)
        next_display_order = max([col.display_order for col in updated_columns], default=0) + 1
        
        for calc in new_calculations:
            if calc.calculation_id not in existing_column_ids:
                # Create new column preference for this calculation
                display_name = calc.display_name or self._get_calculation_display_name(
                    calc.calculation_id, calc.calculation_type, report_scope
                )
                updated_columns.append(ColumnPreference(
                    column_id=calc.calculation_id,
                    display_name=display_name,
                    is_visible=True,
                    display_order=next_display_order,
                    format_type=ColumnFormat.TEXT  # Default format
                ))
                next_display_order += 1
        
        return ReportColumnPreferences(
            include_default_columns=existing_prefs.include_default_columns,
            columns=updated_columns
        )

    async def delete(self, report_id: int) -> bool:
        """Delete a report."""
        return await self.report_dao.delete(report_id)

    # ===== CALCULATION MANAGEMENT =====

    # Remove CDI Variable support from the available calculations
    def get_available_calculations_for_scope(self, scope: ReportScope) -> List[AvailableCalculation]:
        """Get all available calculations for a given report scope."""
        available_calcs = []

        # Add user calculations with new format
        if self.user_calc_service:
            # Use the correct method from UnifiedCalculationService
            user_calcs_result = self.user_calc_service.list_calculations(
                calculation_type=CalculationType.USER_AGGREGATION,
                limit=1000  # Get all user calculations
            )
            user_calcs = user_calcs_result.get('calculations', [])
            
            for calc in user_calcs:
                if self._is_calculation_compatible_with_scope(calc.group_level.value, scope):
                    available_calcs.append(AvailableCalculation(
                        id=f"user.{calc.source_field}",  # NEW FORMAT
                        name=calc.name,
                        description=calc.description,
                        aggregation_function=calc.aggregation_function.value if calc.aggregation_function else None,
                        source_model=calc.source_model.value if calc.source_model else None,
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
            # Use the correct method from UnifiedCalculationService
            system_calcs_result = self.system_calc_service.list_calculations(
                calculation_type=CalculationType.SYSTEM_SQL,
                limit=1000  # Get all system calculations
            )
            system_calcs = system_calcs_result.get('calculations', [])
            
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

        # Add static fields (keep existing format) - FIXED: Use StaticFieldHelper
        static_fields = StaticFieldHelper.get_all_static_fields()
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

    def _get_calculation_display_name(self, calculation_id: str, calculation_type: str, report_scope: str = None) -> str:
        """Get the display name for a calculation with new format."""
        
        # Handle new user calculation format
        if calculation_id.startswith("user."):
            source_field = calculation_id[5:]
            if self.user_calc_service:
                # Use scope-aware lookup if report_scope is available
                if report_scope:
                    user_calc = self.user_calc_service.get_user_calculation_by_source_field_and_scope(
                        source_field, report_scope
                    )
                else:
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
        
        # Handle static fields - FIXED: Use StaticFieldHelper
        elif calculation_id.startswith("static_"):
            field_path = calculation_id.replace("static_", "")
            static_fields = StaticFieldHelper.get_all_static_fields()
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

    async def run_report(self, report_id: int, cycle_code: int) -> Dict[str, Any]:
        """Execute report with column preferences applied using enhanced separate execution."""
        if not self.report_execution_service:
            raise HTTPException(status_code=500, detail="Report execution service not available")

        report = await self._get_report_or_404(report_id)
        start_time = time.time()

        try:
            # Convert report to calculation requests
            deal_tranche_map, calculation_requests = self._prepare_execution(report)

            # DEBUG: Log the calculation requests being sent
            print("=== DEBUG: Calculation Requests ===")
            for req in calculation_requests:
                print(f"  - ID: {req.calc_id}, Alias: {req.alias}")

            # Execute via enhanced separate execution method
            from app.calculations.resolver import QueryFilters, EnhancedCalculationResolver
            filters = QueryFilters(deal_tranche_map, cycle_code, report.scope)
            
            # FIXED: Use separate execution instead of unified
            resolver = EnhancedCalculationResolver(
                self.report_execution_service.dw_db,
                self.report_execution_service.config_db
            )
            result = resolver.resolve_report_separately(calculation_requests, filters)

            # Check if there was an execution error in the result
            if 'error' in result:
                error_message = result['error']
                debug_info = result.get('debug_info', {})
                
                # Log the failed execution
                await self._log_execution(
                    report_id, cycle_code, "api_user",
                    (time.time() - start_time) * 1000,
                    0, False, error_message
                )
                
                # Create a detailed error response for the frontend
                raise HTTPException(
                    status_code=400, 
                    detail={
                        "error": "SQL Execution Failed",
                        "message": error_message,
                        "debug_info": debug_info,
                        "suggestions": [
                            "Check if all selected calculations are compatible with the report scope",
                            "Verify that the selected deals and tranches exist in the current cycle",
                            "Try removing recently added calculations to isolate the issue"
                        ]
                    }
                )

            # Extract execution results and data
            execution_results = result.get('execution_results', {})
            raw_data = result.get('merged_data', [])

            # DEBUG: Log execution summary
            print("=== DEBUG: Execution Results ===")
            print(f"Base query success: {execution_results.get('base_query_success', False)}")
            print(f"Successful calculations: {len(execution_results.get('successful_calculations', []))}")
            print(f"Failed calculations: {len(execution_results.get('failed_calculations', []))}")
            
            if execution_results.get('failed_calculations'):
                print("Failed calculations:")
                for failed_calc in execution_results['failed_calculations']:
                    print(f"  - {failed_calc.get('alias', 'Unknown')}: {failed_calc.get('error', 'Unknown error')}")

            # DEBUG: Log the raw data keys
            print("=== DEBUG: Raw Data Keys ===")
            if raw_data:
                print(f"Raw data keys: {list(raw_data[0].keys())}")
                print(f"First row sample: {raw_data[0]}")
            else:
                print("No raw data returned!")

            # Apply column preferences to the result
            formatted_data = self._apply_column_preferences(raw_data, report)

            # DEBUG: Log formatted data keys
            print("=== DEBUG: Formatted Data Keys ===")
            if formatted_data:
                print(f"Formatted data keys: {list(formatted_data[0].keys())}")
            else:
                print("No formatted data!")

            # Calculate success metrics
            total_calculations = execution_results.get('total_calculations', 0)
            successful_calculations = len(execution_results.get('successful_calculations', []))
            success_rate = (successful_calculations / total_calculations * 100) if total_calculations > 0 else 100

            # Log successful execution with enhanced metrics
            await self._log_execution(
                report_id, cycle_code, "api_user",
                (time.time() - start_time) * 1000,
                len(formatted_data), True,
                f"Success rate: {success_rate:.1f}% ({successful_calculations}/{total_calculations} calculations)"
            )

            # ENHANCED: Return both data and execution metadata
            return {
                "data": formatted_data,
                "execution_results": execution_results,
                "success_rate": f"{success_rate:.1f}%",
                "total_calculations": total_calculations,
                "successful_calculations": successful_calculations,
                "failed_calculations": len(execution_results.get('failed_calculations', [])),
                "execution_time_ms": (time.time() - start_time) * 1000
            }

        except HTTPException:
            # Re-raise HTTP exceptions as they already have proper error details
            raise
        except Exception as e:
            # Log the failed execution
            await self._log_execution(
                report_id, cycle_code, "api_user",
                (time.time() - start_time) * 1000,
                0, False, str(e)
            )
            
            # Create a detailed error response for unexpected errors
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Report Execution Failed",
                    "message": str(e),
                    "debug_info": {
                        "report_id": report_id,
                        "cycle_code": cycle_code,
                        "error_type": type(e).__name__
                    },
                    "suggestions": [
                        "Check the server logs for more detailed error information",
                        "Verify that the report configuration is valid",
                        "Try running the report with a smaller set of calculations"
                    ]
                }
            )

    async def preview_report_sql(self, report_id: int, cycle_code: int) -> Dict[str, Any]:
        """Preview SQL for a report with base query and individual calculation queries."""
        if not self.report_execution_service:
            raise HTTPException(status_code=500, detail="Report execution service not available")

        report = await self._get_report_or_404(report_id)
        deal_tranche_map, calculation_requests = self._prepare_execution(report)

        try:
            # Use the resolver to generate the SQL components
            from app.calculations.resolver import QueryFilters, DynamicParameterInjector
            filters = QueryFilters(deal_tranche_map, cycle_code, report.scope)
            resolver = self.report_execution_service.resolver
            
            # FIXED: Initialize the parameter injector in the resolver
            resolver.parameter_injector = DynamicParameterInjector(filters)

            # Separate calculation requests by type
            static_field_requests = []
            regular_calc_requests = []
            
            for request in calculation_requests:
                if isinstance(request.calc_id, str) and request.calc_id.startswith("static_field:"):
                    static_field_requests.append(request)
                else:
                    regular_calc_requests.append(request)

            # Load calculation metadata for regular requests - FIXED: Get actual calculation models
            calculations = {}
            system_field_calcs = []
            
            for request in regular_calc_requests:
                calc = None
                
                # Handle string-based calculation IDs (new format)
                if isinstance(request.calc_id, str):
                    if request.calc_id.startswith("user."):
                        source_field = request.calc_id[5:]
                        if self.user_calc_service:
                            # FIXED: Get the actual calculation model from the database instead of response object
                            calc_response = self.user_calc_service.get_user_calculation_by_source_field(source_field)
                            if calc_response:
                                # Get the actual calculation model from the database
                                from app.calculations.models import Calculation
                                calc = resolver.config_db.query(Calculation).filter_by(
                                    id=calc_response.id, is_active=True
                                ).first()
                    elif request.calc_id.startswith("system."):
                        result_column = request.calc_id[7:]
                        if self.system_calc_service:
                            # FIXED: Get the actual calculation model from the database instead of response object
                            calc_response = self.system_calc_service.get_system_calculation_by_result_column(result_column)
                            if calc_response:
                                # Get the actual calculation model from the database
                                from app.calculations.models import Calculation
                                calc = resolver.config_db.query(Calculation).filter_by(
                                    id=calc_response.id, is_active=True
                                ).first()
                
                # Handle numeric calculation IDs (legacy format)
                elif isinstance(request.calc_id, int):
                    from app.calculations.models import Calculation
                    calc = resolver.config_db.query(Calculation).filter_by(
                        id=request.calc_id, is_active=True
                    ).first()
                
                if calc:
                    calculations[request.calc_id] = calc
                    # Check if it's a system field calculation
                    if hasattr(calc, 'calculation_type') and calc.calculation_type.name == 'SYSTEM_FIELD':
                        system_field_calcs.append((request, calc))

            # Generate base query (includes static fields and system fields)
            base_query = resolver._build_base_query(system_field_calcs, static_field_requests, filters, calculation_requests)

            # Generate individual calculation queries
            calculation_queries = []
            
            for request in regular_calc_requests:
                calc = calculations.get(request.calc_id)
                if calc and hasattr(calc, 'calculation_type'):
                    try:
                        if calc.calculation_type.name == 'USER_AGGREGATION':
                            query = resolver._build_user_aggregation_query(request, calc, filters)
                            calculation_queries.append({
                                "alias": request.alias,
                                "type": "User Aggregation",
                                "sql": query,
                                "description": calc.description or f"User calculation: {calc.name}"
                            })
                        elif calc.calculation_type.name == 'SYSTEM_SQL':
                            query = resolver._build_system_sql_query(request, calc, filters)
                            calculation_queries.append({
                                "alias": request.alias,
                                "type": "System SQL",
                                "sql": query,
                                "description": calc.description or f"System calculation: {calc.name}"
                            })
                        # Skip SYSTEM_FIELD calculations as they're included in the base query
                    except Exception as e:
                        # Add failed calculation to the list with error info
                        calculation_queries.append({
                            "alias": request.alias,
                            "type": "Error",
                            "sql": f"-- Error generating query: {str(e)}",
                            "description": f"Failed to generate query for {calc.name}: {str(e)}"
                        })

            return {
                "base_query": base_query,
                "calculation_queries": calculation_queries,
                "parameters": {
                    "deal_tranche_map": deal_tranche_map,
                    "cycle_code": cycle_code,
                    "report_scope": report.scope
                },
                "summary": {
                    "total_deals": len(deal_tranche_map),
                    "total_tranches": sum(len(tranches) for tranches in deal_tranche_map.values()),
                    "total_calculations": len(calculation_queries),
                    "static_fields": len(static_field_requests),
                    "execution_approach": "separate_queries_with_left_joins"
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate SQL preview for report {report_id}: {str(e)}")
            
            # Return a fallback response with error information
            return {
                "base_query": f"-- Error generating base query: {str(e)}",
                "calculation_queries": [],
                "error": str(e),
                "parameters": {
                    "deal_tranche_map": deal_tranche_map,
                    "cycle_code": cycle_code,
                    "report_scope": report.scope
                },
                "summary": {
                    "total_deals": len(deal_tranche_map),
                    "total_tranches": sum(len(tranches) for tranches in deal_tranche_map.values()),
                    "total_calculations": 0,
                    "static_fields": 0,
                    "execution_approach": "error_fallback",
                    "error_message": str(e)
                }
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
        calc_id_to_alias = {}  # NEW: Track the actual alias used in SQL
        for report_calc in report.selected_calculations:
            calc_id = report_calc.calculation_id
            calc_type = getattr(report_calc, 'calculation_type', None)
            display_name = self._get_calculation_display_name(calc_id, calc_type)
            calc_id_to_display_name[calc_id] = display_name
            
            # NEW: Track the actual alias that will be used in the SQL (the display_name from report_calc)
            actual_alias = report_calc.display_name or display_name
            calc_id_to_alias[calc_id] = actual_alias
        
        for col_pref in column_prefs.columns:
            if col_pref.is_visible:
                column_id = col_pref.column_id
                
                # FIXED: Handle different types of columns with proper static field mapping
                if column_id.startswith("static_"):
                    # For static fields, the raw data key is now the display name (alias)
                    # Find the corresponding calculation to get its display name
                    static_calc = None
                    for report_calc in report.selected_calculations:
                        if report_calc.calculation_id == column_id:
                            static_calc = report_calc
                            break
                    
                    if static_calc and static_calc.display_name:
                        # Use the display name from the report calculation
                        raw_data_key = static_calc.display_name
                    else:
                        # Fallback: try to get the display name from static field registry - FIXED: Use StaticFieldHelper
                        field_path = column_id.replace("static_", "")
                        field = StaticFieldHelper.get_static_field_by_path(field_path)
                        raw_data_key = field.name
                elif column_id.replace(".", "_") in ["deal_number", "tranche_id", "cycle_code"]:
                    # Default columns - convert dots to underscores for raw data lookup
                    raw_data_key = column_id.replace(".", "_")
                elif column_id in calc_id_to_alias:
                    # User/system calculations - use the actual alias from the SQL
                    raw_data_key = calc_id_to_alias[column_id]
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
        
        # Default columns are always included (we removed the include_default_columns toggle)
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

        # Apply sorting if specified in column preferences
        if column_prefs.sort_config:
            formatted_data = self._apply_sorting(formatted_data, column_prefs.sort_config, column_mapping, calc_id_to_alias)
    
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

        # DEBUG: Log the deal-tranche mapping
        print("=== DEBUG: Deal-Tranche Mapping ===")
        for deal_id, tranche_ids in deal_tranche_map.items():
            print(f"  Deal {deal_id}: {tranche_ids}")

        # Convert to calculation requests with improved logic
        calculation_requests = []
        
        # Add default columns if requested (always include since we removed the toggle)
        include_defaults = True
        column_prefs = getattr(report, '_parsed_column_preferences', None)
        # Default columns are now always included since we removed include_default_columns
        
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
                    # FIXED: Only use calc_id and alias for CalculationRequest
                    # For static fields, use a special calc_id format that the resolver can understand
                    calc_request = CalculationRequest(
                        calc_id=f"static_field:{field_path}",  # Use a special format for static fields
                        alias=alias
                    )
                    calculation_requests.append(calc_request)

        # Add user-selected calculations with enhanced parsing for new formats
        for report_calc in report.selected_calculations:
            calc_id_str = report_calc.calculation_id
            calc_type = getattr(report_calc, 'calculation_type', None)
            
            print(f"Debug: Processing calculation - ID: {calc_id_str}, Type: {calc_type}")
            
            calc_request = None
            
            # Handle NEW CALCULATION ID FORMATS FIRST
            if calc_id_str.startswith("user."):
                # User calculation: "user.{source_field}"
                source_field = calc_id_str[5:]  # Remove "user." prefix
                if self.user_calc_service:
                    # FIXED: Allow deal-level calculations in tranche reports
                    # First try to find a calculation that matches the report scope
                    user_calc = self.user_calc_service.get_user_calculation_by_source_field_and_scope(
                        source_field, 
                        report.scope  # Pass the report scope (DEAL or TRANCHE)
                    )
                    
                    # If no scope-specific calculation found, try to find any calculation with this source field
                    # This allows deal-level calculations to appear in tranche reports
                    if not user_calc:
                        user_calc = self.user_calc_service.get_user_calculation_by_source_field(source_field)
                        if user_calc:
                            print(f"Debug: Using deal-level calculation '{user_calc.name}' in tranche report")
                    
                    if user_calc:
                        # FIXED: Keep the original string calc_id for the resolver to handle
                        display_name = report_calc.display_name or user_calc.name
                        calc_request = CalculationRequest(
                            calc_id=calc_id_str,  # Keep the original "user.tr_pass_thru_rte" format
                            alias=display_name  # Use the display name from the report
                        )
                        print(f"Debug: Found user calculation - {user_calc.name} (level: {user_calc.group_level.value}) using alias: '{display_name}'")
                    else:
                        print(f"Warning: No user calculation found with source_field: {source_field}")
            
            elif calc_id_str.startswith("system."):
                # System calculation: "system.{result_column_name}"
                result_column = calc_id_str[7:]  # Remove "system." prefix
                if self.system_calc_service:
                    system_calc = self.system_calc_service.get_system_calculation_by_result_column(result_column)
                    if system_calc:
                        # FIXED: Keep the original string calc_id for the resolver to handle
                        display_name = report_calc.display_name or system_calc.name
                        calc_request = CalculationRequest(
                            calc_id=calc_id_str,  # Keep the original "system.result_column" format
                            alias=display_name  # Use the display name from the report
                        )
                        print(f"Debug: Found system calculation - {system_calc.name} using alias: '{display_name}'")
                    else:
                        print(f"Warning: No system calculation found with result_column: {result_column}")
            
            # Handle static fields - check calculation_type first, then fallback to "static_" prefix
            elif calc_type == "static" or calc_id_str.startswith("static_"):
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
                
                # FIXED: Use StaticFieldHelper for static fields
                field = StaticFieldHelper.get_static_field_by_path(field_path)
                display_name = report_calc.display_name or field.name
                calc_request = CalculationRequest(
                    calc_id=f"static_field:{field_path}",  # Use special format for static fields
                    alias=display_name  # Use the display name from the report
                )
                print(f"Debug: Found static field - {field.name} using alias: '{display_name}'")
            
            # Handle legacy numeric calculation IDs
            else:
                try:
                    numeric_id = int(calc_id_str)
                    
                    if calc_type == "user_calculation" or calc_type == "user":
                        if self.user_calc_service:
                            user_calc = self.user_calc_service.get_user_calculation_by_id(numeric_id)
                            if user_calc:
                                calc_request = CalculationRequest(
                                    calc_id=numeric_id,
                                    alias=user_calc.name
                                )
                    elif calc_type == "system_calculation" or calc_type == "system":
                        if self.system_calc_service:
                            system_calc = self.system_calc_service.get_system_calculation_by_id(numeric_id)
                            if system_calc:
                                calc_request = CalculationRequest(
                                    calc_id=numeric_id,
                                    alias=system_calc.name
                                )
                    else:
                        # calculation_type is NULL or missing - try to auto-detect
                        print(f"Warning: calculation_type is NULL for calc_id {numeric_id}, attempting auto-detection")
                        
                        # Check user calculations first
                        if self.user_calc_service:
                            user_calc = self.user_calc_service.get_user_calculation_by_id(numeric_id)
                            if user_calc:
                                calc_request = CalculationRequest(
                                    calc_id=numeric_id,
                                    alias=user_calc.name
                                )
                                print(f"Auto-detected as user_calculation: {user_calc.name}")
                        
                        if not calc_request and self.system_calc_service:
                            # Try system calculations
                            system_calc = self.system_calc_service.get_system_calculation_by_id(numeric_id)
                            if system_calc:
                                calc_request = CalculationRequest(
                                    calc_id=numeric_id,
                                    alias=system_calc.name
                                )
                                print(f"Auto-detected as system_calculation: {system_calc.name}")
                        
                        if not calc_request:
                            print(f"Warning: No calculation found with ID {numeric_id}")
                except ValueError:
                    # Non-numeric, non-prefixed ID - unknown format
                    print(f"Warning: Unknown calculation_id format: {calc_id_str}")
            
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
        # Default columns are now always included since we removed include_default_columns
        
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
                        calc_id=f"static_field:{field_path}",  # Use a special format for static fields
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
                    # FIXED: Allow deal-level calculations in tranche reports
                    # First try to find a calculation that matches the report scope
                    user_calc = self.user_calc_service.get_user_calculation_by_source_field_and_scope(
                        source_field, 
                        report.scope  # Pass the report scope (DEAL or TRANCHE)
                    )
                    
                    # If no scope-specific calculation found, try to find any calculation with this source field
                    # This allows deal-level calculations to appear in tranche reports
                    if not user_calc:
                        user_calc = self.user_calc_service.get_user_calculation_by_source_field(source_field)
                        if user_calc:
                            print(f"Debug: Using deal-level calculation '{user_calc.name}' in tranche report")
                    
                    if user_calc:
                        # FIXED: Keep the original string calc_id for the resolver to handle
                        display_name = report_calc.display_name or user_calc.name
                        calc_request = CalculationRequest(
                            calc_id=calc_id_str,  # Keep the original "user.tr_pass_thru_rte" format
                            alias=display_name  # Use the display name from the report
                        )
                        print(f"Debug: Found user calculation - {user_calc.name} (level: {user_calc.group_level.value}) using alias: '{display_name}'")
                    else:
                        print(f"Warning: No user calculation found with source_field: {source_field}")
            
            elif calc_id_str.startswith("system."):
                # System calculation: "system.{result_column_name}"
                result_column = calc_id_str[7:]  # Remove "system." prefix
                if self.system_calc_service:
                    system_calc = self.system_calc_service.get_system_calculation_by_result_column(result_column)
                    if system_calc:
                        # FIXED: Keep the original string calc_id for the resolver to handle
                        display_name = report_calc.display_name or system_calc.name
                        calc_request = CalculationRequest(
                            calc_id=calc_id_str,  # Keep the original "system.result_column" format
                            alias=display_name  # Use the display name from the report
                        )
                        print(f"Debug: Found system calculation - {system_calc.name} using alias: '{display_name}'")
                    else:
                        print(f"Warning: No system calculation found with result_column: {result_column}")
            
            elif calc_id_str.startswith("static_"):
                # Static field: "static_{table}.{field_name}"
                field_path = calc_id_str.replace("static_", "")
                
                # FIXED: Use display_name from report_calc like other calculation types
                field = StaticFieldHelper.get_static_field_by_path(field_path)
                display_name = report_calc.display_name or field.name
                calc_request = CalculationRequest(
                    calc_id=f"static_field:{field_path}",  # Use special format for static fields
                    alias=display_name  # Use the display name from the report
                )
                print(f"Debug: Found static field - {field.name} using alias: '{display_name}'")
            
            else:
                # Legacy numeric ID handling
                try:
                    numeric_id = int(calc_id_str)
                    
                    if calc_type == "user_calculation" or calc_type == "user":
                        if self.user_calc_service:
                            user_calc = self.user_calc_service.get_user_calculation_by_id(numeric_id)
                            if user_calc:
                                calc_request = CalculationRequest(
                                    calc_id=numeric_id,
                                    alias=user_calc.name
                                )
                    elif calc_type == "system_calculation" or calc_type == "system":
                        if self.system_calc_service:
                            system_calc = self.system_calc_service.get_system_calculation_by_id(numeric_id)
                            if system_calc:
                                calc_request = CalculationRequest(
                                    calc_id=numeric_id,
                                    alias=system_calc.name
                                )
                    else:
                        # Auto-detect for legacy data
                        if self.user_calc_service:
                            user_calc = self.user_calc_service.get_user_calculation_by_id(numeric_id)
                            if user_calc:
                                calc_request = CalculationRequest(
                                    calc_id=numeric_id,
                                    alias=user_calc.name
                                )
                        
                        if not calc_request and self.system_calc_service:
                            # Try system calculations
                            system_calc = self.system_calc_service.get_system_calculation_by_id(numeric_id)
                            if system_calc:
                                calc_request = CalculationRequest(
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

    def get_deals_by_numbers(self, deal_numbers: List[int]) -> List[Dict[str, Any]]:
        """Get specific deals by their deal numbers - much more efficient than searching through issuer codes."""
        deals = self.dw_dao.get_deals_by_numbers(deal_numbers)
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
        """Get report or raise 404 with relationships properly loaded."""
        raw_report = await self.report_dao.get_by_id(report_id)
        if not raw_report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Debug: Check if relationships are loaded
        print(f"Debug: Report {report_id} found: {raw_report.name}")
        print(f"Debug: selected_deals type: {type(raw_report.selected_deals)}")
        print(f"Debug: selected_deals value: {raw_report.selected_deals}")
        print(f"Debug: selected_calculations type: {type(raw_report.selected_calculations)}")
        print(f"Debug: selected_calculations value: {raw_report.selected_calculations}")
        
        # Ensure relationships are accessible - force loading if needed
        if raw_report.selected_deals is None:
            print("Warning: selected_deals is None, attempting to force reload relationships")
            # Try to get the report again with explicit relationship loading
            from sqlalchemy.orm import selectinload
            from sqlalchemy import select
            from app.reporting.models import ReportDeal, ReportTranche
            
            stmt = (
                select(Report)
                .options(
                    selectinload(Report.selected_deals).selectinload(ReportDeal.selected_tranches),
                    selectinload(Report.selected_calculations),
                )
                .where(Report.id == report_id)
            )
            result = self.report_dao.db.execute(stmt)
            raw_report = result.scalars().first()
            
            if not raw_report:
                raise HTTPException(status_code=404, detail="Report not found after reload")
            
            print(f"Debug: After reload - selected_deals: {raw_report.selected_deals}")
            print(f"Debug: After reload - selected_calculations: {raw_report.selected_calculations}")
        
        # Parse column preferences for internal use
        if raw_report.column_preferences and isinstance(raw_report.column_preferences, dict):
            try:
                parsed_column_prefs = ReportColumnPreferences(**raw_report.column_preferences)
                raw_report._parsed_column_preferences = parsed_column_prefs
            except Exception as e:
                print(f"Warning: Could not parse column preferences for report {report_id}: {e}")
                raw_report._parsed_column_preferences = None
        
        return raw_report

    # ===== EXECUTION LOGS =====
    
    async def get_execution_logs(self, report_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get execution logs for a report."""
        logs = await self.report_dao.get_execution_logs(report_id, limit)
        return [
            {
                "id": log.id,
                "report_id": log.report_id,
                "cycle_code": log.cycle_code,
                "executed_by": log.executed_by,
                "execution_time_ms": log.execution_time_ms,
                "row_count": log.row_count,
                "success": log.success,
                "error_message": log.error_message,
                "executed_at": log.executed_at.isoformat() if log.executed_at else None
            }
            for log in logs
        ]
    def _apply_sorting(self, data: List[Dict[str, Any]], sort_config: List, 
                       column_mapping: Dict[str, str], calc_id_to_alias: Dict[str, str]) -> List[Dict[str, Any]]:
        """Apply sorting configuration to the data."""
        if not sort_config or not data:
            return data
        
        # Build sort keys based on the sort configuration
        sort_keys = []
        
        # Sort by sort_order to get the correct precedence
        sorted_sort_config = sorted(sort_config, key=lambda x: x.sort_order)
        
        for sort_item in sorted_sort_config:
            column_id = sort_item.column_id
            direction = sort_item.direction
            
            # Map column_id to the actual column name in the data
            actual_column_name = None
            
            # Check if it's a default column
            if column_id.replace(".", "_") in ["deal_number", "tranche_id", "cycle_code"]:
                # For default columns, check if they're in column_mapping
                raw_key = column_id.replace(".", "_")
                if raw_key in column_mapping:
                    actual_column_name = column_mapping[raw_key]
                else:
                    # Fallback to the display name format
                    actual_column_name = raw_key.replace('_', ' ').title()
            
            # Check if it's a calculation column
            elif column_id in calc_id_to_alias:
                # For calculations, use the display name from column_mapping
                raw_key = calc_id_to_alias[column_id]
                if raw_key in column_mapping:
                    actual_column_name = column_mapping[raw_key]
                else:
                    actual_column_name = raw_key
            
            # Check if it's a static field
            elif column_id.startswith("static_"):
                # Find the display name in column_mapping
                for raw_key, display_name in column_mapping.items():
                    # Check if this raw_key corresponds to our static field
                    if column_id in column_mapping.values() or display_name == column_id:
                        actual_column_name = display_name
                        break
                
                # If not found in mapping, try to find by display name directly - FIXED: Use StaticFieldHelper
                if not actual_column_name:
                    field_path = column_id.replace("static_", "")
                    field = StaticFieldHelper.get_static_field_by_path(field_path)
                    actual_column_name = field.name
            
            # Fallback - check if column_id itself is a display name in the data
            if not actual_column_name and data:
                first_row = data[0]
                if column_id in first_row:
                    actual_column_name = column_id
                else:
                    # Check if any of the column mappings match
                    for raw_key, display_name in column_mapping.items():
                        if display_name == column_id:
                            actual_column_name = column_id
                            break
            
            if actual_column_name and actual_column_name in data[0]:
                # Add to sort keys with direction
                reverse_sort = (direction.lower() == "desc")
                sort_keys.append((actual_column_name, reverse_sort))
                print(f"Debug: Adding sort key - Column: '{actual_column_name}', Direction: {direction}")
            else:
                print(f"Warning: Could not find column '{column_id}' (mapped to '{actual_column_name}') in data for sorting")
        
        if not sort_keys:
            print("Warning: No valid sort keys found, returning unsorted data")
            return data
        
        # Apply sorting with multiple keys
        try:
            # Sort the data
            sorted_data = data.copy()
            
            # Apply sorts in reverse order (last sort first) to maintain precedence
            for column_name, reverse_sort in reversed(sort_keys):
                sorted_data.sort(
                    key=lambda row: (
                        row.get(column_name) is None,  # None values go to end
                        str(row.get(column_name, '')).lower() if not isinstance(row.get(column_name), (int, float)) else row.get(column_name, 0)
                    ),
                    reverse=reverse_sort
                )
            
            print(f"Debug: Applied sorting with {len(sort_keys)} sort keys")
            return sorted_data
            
        except Exception as e:
            print(f"Warning: Error applying sorting: {e}")
            return data