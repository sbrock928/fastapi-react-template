# app/calculations/service.py
"""Simplified calculation service using the unified resolver architecture"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from app.core.exceptions import (
    CalculationNotFoundError,
    CalculationAlreadyExistsError,
    InvalidCalculationError,
)

from .models import (
    UserCalculation, 
    SystemCalculation, 
    AggregationFunction, 
    SourceModel, 
    GroupLevel,
    get_all_static_fields,
    get_static_field_info
)
from .dao import UserCalculationDAO, SystemCalculationDAO
from .resolver import UnifiedCalculationResolver, CalculationRequest, QueryFilters
from .schemas import (
    UserCalculationCreate,
    UserCalculationUpdate,
    SystemCalculationCreate,
    SystemCalculationUpdate,
    StaticFieldInfo
)
# Add this conditional import to avoid circular imports
from typing import TYPE_CHECKING

# Add this conditional import to avoid circular imports
if TYPE_CHECKING:
    from .cdi_service import CDIVariableCalculationService

class ReportExecutionService:
    """Service for executing reports with mixed calculation types using unified resolver"""

    def __init__(self, dw_db: Session, config_db: Session, cdi_service: Optional['CDIVariableCalculationService'] = None):
        self.dw_db = dw_db
        self.config_db = config_db
        # Use only the unified resolver for cleaner, more readable SQL
        self.resolver = UnifiedCalculationResolver(dw_db, config_db)
        self.cdi_service = cdi_service

    def set_cdi_service(self, cdi_service: 'CDIVariableCalculationService'):
        """Set the CDI service for integration (dependency injection)"""
        self.cdi_service = cdi_service

    def execute_report(self, calculation_requests: List[CalculationRequest], 
                      deal_tranche_map: Dict[int, List[str]], cycle_code: int, 
                      report_scope: str = None) -> Dict[str, Any]:
        """Execute a report with mixed calculation types including CDI variables"""
        
        # Separate calculation requests by type
        regular_requests = []
        cdi_requests = []
        
        for request in calculation_requests:
            if request.calc_type == "system_calculation" and request.calc_id:
                # Check if this system calculation is a CDI variable
                system_calc = self.config_db.query(SystemCalculation).filter_by(
                    id=request.calc_id, is_active=True
                ).first()
                
                if (system_calc and 
                    system_calc.metadata_config and 
                    system_calc.metadata_config.get("calculation_type") == "cdi_variable"):
                    cdi_requests.append(request)
                else:
                    regular_requests.append(request)
            else:
                regular_requests.append(request)
        
        results = {}
        
        # Execute regular calculations using unified approach
        if regular_requests:
            filters = QueryFilters(deal_tranche_map, cycle_code, report_scope)
            regular_result = self.resolver.resolve_report(regular_requests, filters)
            
            results = {
                'data': regular_result['merged_data'],
                'metadata': {
                    'total_rows': len(regular_result['merged_data']),
                    'calculations_executed': len(regular_requests),
                    'debug_info': regular_result['debug_info'],
                    'unified_sql': regular_result.get('unified_sql'),
                    'query_approach': 'unified'
                }
            }
        
        # Execute CDI variable calculations
        if cdi_requests and self.cdi_service:
            cdi_results = self._execute_cdi_calculations(cdi_requests, deal_tranche_map, cycle_code)
            
            # Merge CDI results with regular results
            if 'data' in results and 'data' in cdi_results:
                results['data'] = self._merge_calculation_results(results['data'], cdi_results['data'])
            elif 'data' in cdi_results:
                results['data'] = cdi_results['data']
            
            # Update metadata
            if 'metadata' not in results:
                results['metadata'] = {}
            
            results['metadata']['cdi_calculations'] = len(cdi_requests)
            results['metadata']['total_calculations'] = len(calculation_requests)
            results['metadata']['cdi_records'] = cdi_results.get('total_cdi_records', 0)
        
        return results

    def _execute_cdi_calculations(self, cdi_requests: List[CalculationRequest], 
                                deal_tranche_map: Dict[int, List[str]], 
                                cycle_code: int) -> Dict[str, Any]:
        """Execute CDI variable calculations"""
        
        # Extract deal numbers from deal_tranche_map
        deal_numbers = list(deal_tranche_map.keys())
        
        # Group CDI results by (dl_nbr, tr_id, cycle_cde) and then by alias
        cdi_data_by_key = {}
        
        for request in cdi_requests:
            try:
                # Extract calc_id from the request
                if hasattr(request, 'calc_id') and request.calc_id:
                    calc_id = request.calc_id
                elif hasattr(request, 'calculation_id'):
                    # Handle string format like "system.123"
                    calc_id_str = str(request.calculation_id)
                    if calc_id_str.startswith('system.'):
                        calc_id = int(calc_id_str.split('.')[-1])
                    else:
                        calc_id = int(calc_id_str)
                else:
                    continue
                
                result_df = self.cdi_service.execute_cdi_variable_calculation(
                    calc_id, cycle_code, deal_numbers
                )
                
                # Convert DataFrame to list of dicts and organize by key
                result_data = result_df.to_dict('records')
                
                # Use the request alias as the field name in the merged data
                field_alias = getattr(request, 'alias', f'cdi_calc_{calc_id}')
                
                for record in result_data:
                    key = (record.get('dl_nbr'), record.get('tr_id'), record.get('cycle_cde'))
                    if key not in cdi_data_by_key:
                        cdi_data_by_key[key] = {}
                    
                    # Map the CDI value to the alias name used in the report
                    # The CDI service returns the value under different field names depending on calculation type
                    cdi_value = None
                    for field_name, field_value in record.items():
                        if field_name not in ['dl_nbr', 'tr_id', 'cycle_cde', 'variable_name', 'tranche_type']:
                            cdi_value = field_value
                            break
                    
                    if cdi_value is not None:
                        cdi_data_by_key[key][field_alias] = cdi_value
                
            except Exception as e:
                # Log error but continue with other calculations
                continue
        
        # Convert to the expected format for merging
        cdi_results = []
        for key, fields in cdi_data_by_key.items():
            dl_nbr, tr_id, cycle_cde = key
            record = {
                'dl_nbr': dl_nbr,
                'tr_id': tr_id,
                'cycle_cde': cycle_cde,
                **fields  # Add all CDI field values
            }
            cdi_results.append(record)
        
        return {
            'data': cdi_results,
            'cdi_calculation_count': len(cdi_requests),
            'total_cdi_records': len(cdi_results)
        }
    
    def _merge_calculation_results(self, regular_data: List[Dict], cdi_data: List[Dict]) -> List[Dict]:
        """Merge regular calculation results with CDI variable results"""
        
        # Get all unique CDI field names from the CDI data
        cdi_field_names = set()
        for record in cdi_data:
            for field_name in record.keys():
                if field_name not in ['dl_nbr', 'tr_id', 'cycle_cde', 'variable_name', 'tranche_type']:
                    cdi_field_names.add(field_name)
        
        # Create a lookup for CDI data by (dl_nbr, tr_id, cycle_cde)
        cdi_lookup = {}
        for record in cdi_data:
            key = (record.get('dl_nbr'), record.get('tr_id'), record.get('cycle_cde'))
            if key not in cdi_lookup:
                cdi_lookup[key] = {}
            
            # Store all CDI field values
            for field_name, field_value in record.items():
                if field_name not in ['dl_nbr', 'tr_id', 'cycle_cde', 'variable_name', 'tranche_type']:
                    cdi_lookup[key][field_name] = field_value
        
        # Merge CDI data into regular data with defaults
        for record in regular_data:
            key = (record.get('dl_nbr'), record.get('tr_id'), record.get('cycle_cde'))
            
            # For each CDI field, either use the actual value or default to 0.0
            for field_name in cdi_field_names:
                if key in cdi_lookup and field_name in cdi_lookup[key]:
                    # Use actual CDI value
                    record[field_name] = cdi_lookup[key][field_name]
                else:
                    # Use default value of 0.0 for missing CDI mappings
                    record[field_name] = 0.0
        
        return regular_data

    def preview_report_sql(self, calculation_requests: List[CalculationRequest],
                          deal_tranche_map: Dict[int, List[str]], cycle_code: int, 
                          report_scope: str = None) -> Dict[str, Any]:
        """Preview SQL queries without executing them using unified approach"""

        # Separate regular and CDI calculations using same logic as execute_report
        regular_requests = []
        cdi_requests = []
        
        for request in calculation_requests:
            if request.calc_type == "system_calculation" and request.calc_id:
                # Check if this system calculation is a CDI variable
                system_calc = self.config_db.query(SystemCalculation).filter_by(
                    id=request.calc_id, is_active=True
                ).first()
                
                if (system_calc and 
                    system_calc.metadata_config and 
                    system_calc.metadata_config.get("calculation_type") == "cdi_variable"):
                    cdi_requests.append(request)
                else:
                    regular_requests.append(request)
            else:
                regular_requests.append(request)

        filters = QueryFilters(deal_tranche_map, cycle_code, report_scope)
        
        # Generate the unified SQL for regular calculations only
        unified_sql = None
        if regular_requests:
            try:
                unified_sql = self.resolver._build_unified_query(regular_requests, filters)
            except Exception as e:
                unified_sql = f"-- ERROR generating unified SQL: {str(e)}"
        
        result = {
            'unified_sql': unified_sql,
            'parameters': {
                'deal_tranche_map': deal_tranche_map,
                'cycle_code': cycle_code,
                'report_scope': report_scope
            },
            'summary': {
                'total_calculations': len(calculation_requests),
                'static_fields': len([r for r in regular_requests if r.calc_type == 'static_field']),
                'user_calculations': len([r for r in regular_requests if r.calc_type == 'user_calculation']),
                'system_calculations': len([r for r in calculation_requests if r.calc_type == 'system_calculation']),  # FIXED: Count ALL system calculations
                'cdi_calculations': len(cdi_requests),
                'query_approach': 'unified'
            }
        }
        
        # Add CDI calculation SQL previews if present
        if cdi_requests and self.cdi_service:
            cdi_sql_previews = []
            deal_numbers = list(deal_tranche_map.keys())
            
            for req in cdi_requests:
                try:
                    # Extract calc_id from the request
                    if hasattr(req, 'calc_id') and req.calc_id:
                        calc_id = req.calc_id
                    elif hasattr(req, 'calculation_id'):
                        # Handle string format like "system.123"
                        calc_id_str = str(req.calculation_id)
                        if calc_id_str.startswith('system.'):
                            calc_id = int(calc_id_str.split('.')[-1])
                        else:
                            calc_id = int(calc_id_str)
                    else:
                        continue
                    
                    # Generate SQL preview for this CDI calculation
                    cdi_preview = self.cdi_service.generate_cdi_sql_preview(
                        calc_id, cycle_code, deal_numbers
                    )
                    
                    # Add the alias from the request for context
                    cdi_preview['alias'] = getattr(req, 'alias', f'cdi_calc_{calc_id}')
                    cdi_preview['calc_id'] = calc_id
                    
                    cdi_sql_previews.append(cdi_preview)
                    
                except Exception as e:
                    # If preview generation fails, add error info
                    cdi_sql_previews.append({
                        'alias': getattr(req, 'alias', 'unknown'),
                        'calc_id': getattr(req, 'calc_id', 'unknown'),
                        'error': f'Failed to generate SQL preview: {str(e)}',
                        'sql': '-- SQL generation failed',
                        'calculation_type': 'cdi_error'
                    })
            
            result['cdi_sql_previews'] = cdi_sql_previews
        
        return result
    
class UserCalculationService:
    """Service for managing user-defined calculations"""

    def __init__(self, user_calc_dao: UserCalculationDAO):
        self.user_calc_dao = user_calc_dao

    def get_all_user_calculations(self, group_level: Optional[str] = None) -> List[UserCalculation]:
        """Get all active user calculations with usage information"""
        group_level_enum = GroupLevel(group_level) if group_level else None
        calculations = self.user_calc_dao.get_all(group_level_enum)
        
        # Add usage information to each calculation
        for calc in calculations:
            try:
                usage_info = self.get_user_calculation_usage(calc.id)
                # Add usage info as attributes to the calculation object
                calc.usage_info = usage_info
            except Exception as e:
                # If usage fetch fails, provide default values
                calc.usage_info = {
                    "calculation_id": calc.id,
                    "calculation_name": calc.name,
                    "is_in_use": False,
                    "report_count": 0,
                    "reports": [],
                }
        
        return calculations

    def get_user_calculation_by_id(self, calc_id: int) -> Optional[UserCalculation]:
        """Get user calculation by ID"""
        return self.user_calc_dao.get_by_id(calc_id)

    def get_user_calculation_by_source_field(self, source_field: str) -> Optional[UserCalculation]:
        """Get user calculation by source_field"""
        return self.user_calc_dao.get_by_source_field(source_field)

    def get_user_calculation_by_source_field_and_scope(
        self, 
        source_field: str, 
        report_scope: str
    ) -> Optional[UserCalculation]:
        """
        Get user calculation by source_field with scope preference.
        
        For TRANCHE reports: Prefer tranche-level calculations, fall back to deal-level
        For DEAL reports: Only return deal-level calculations
        """
        # Get all active calculations for this source field
        calculations = self.user_calc_dao.get_all_by_source_field(source_field)
        
        if not calculations:
            return None
        
        # Filter by scope preference
        if report_scope == "TRANCHE":
            # For tranche reports, prefer tranche-level calculations
            tranche_calcs = [c for c in calculations if c.group_level.value == "tranche"]
            if tranche_calcs:
                return tranche_calcs[0]  # Return first tranche-level match
            
            # Fall back to deal-level if no tranche-level exists
            deal_calcs = [c for c in calculations if c.group_level.value == "deal"]
            return deal_calcs[0] if deal_calcs else None
        
        elif report_scope == "DEAL":
            # For deal reports, only return deal-level calculations
            deal_calcs = [c for c in calculations if c.group_level.value == "deal"]
            return deal_calcs[0] if deal_calcs else None
        
        # Fallback to original behavior
        return calculations[0] if calculations else None

    def create_user_calculation(self, request: UserCalculationCreate, created_by: str = "api_user") -> UserCalculation:
        """Create a new user calculation with automatic approval for development"""
        
        # Check if calculation name already exists at this group level
        existing = self.user_calc_dao.get_by_name_and_group_level(request.name, request.group_level)
        
        if existing:
            raise CalculationAlreadyExistsError(
                f"User calculation with name '{request.name}' already exists at {request.group_level} level"
            )

        # Check if source_field is already in use
        existing_calc = self.user_calc_dao.get_by_source_field_and_group_level(request.source_field, request.group_level)
        if existing_calc:
            raise ValueError(f"Source field '{request.source_field}' is already in use by calculation '{existing_calc.name}' at the {request.group_level.value} level")

        # Validate weighted average has weight field
        if request.aggregation_function == AggregationFunction.WEIGHTED_AVG and not request.weight_field:
            raise InvalidCalculationError("Weighted average calculations require a weight_field")

        # Create new calculation
        calculation = UserCalculation(
            name=request.name,
            description=request.description,
            aggregation_function=request.aggregation_function,
            source_model=request.source_model,
            source_field=request.source_field,
            weight_field=request.weight_field,
            group_level=request.group_level,
            advanced_config=request.advanced_config,
            created_by=created_by,
        )

        # Create the calculation first
        created_calc = self.user_calc_dao.create(calculation)
        
        # Auto-approve for development (TODO: implement proper approval workflow)
        approved_calc = self.approve_user_calculation(created_calc.id, "system_auto_approval")
        
        return approved_calc

    def approve_user_calculation(self, calc_id: int, approved_by: str) -> UserCalculation:
        """Approve a user calculation"""
        calculation = self.get_user_calculation_by_id(calc_id)
        if not calculation:
            raise CalculationNotFoundError(f"User calculation with ID {calc_id} not found")

        from datetime import datetime
        calculation.approved_by = approved_by
        calculation.approval_date = datetime.now()
        
        return self.user_calc_dao.update(calculation)

    def update_user_calculation(self, calc_id: int, request: UserCalculationUpdate) -> UserCalculation:
        """Update an existing user calculation"""
        calculation = self.get_user_calculation_by_id(calc_id)
        if not calculation:
            raise CalculationNotFoundError(f"User calculation with ID {calc_id} not found")

        # Check if another calculation with the same name exists at this group level (excluding current one)
        if request.name:
            group_level = request.group_level or calculation.group_level
            existing = self.user_calc_dao.get_by_name_and_group_level(request.name, group_level)
            
            if existing and existing.id != calc_id:
                raise CalculationAlreadyExistsError(
                    f"Another user calculation with name '{request.name}' already exists at that group level"
                )

        # If source_field is being updated, check for conflicts at the same group level
        if hasattr(request, 'source_field') and request.source_field and request.source_field != calculation.source_field:
            group_level = request.group_level or calculation.group_level
            conflicting_calc = self.user_calc_dao.get_by_source_field_and_group_level(request.source_field, group_level)
            if conflicting_calc and conflicting_calc.id != calc_id:
                raise ValueError(f"Source field '{request.source_field}' is already in use by calculation '{conflicting_calc.name}' at the {group_level.value} level")

        # Update fields that are provided
        if request.name is not None:
            calculation.name = request.name
        if request.description is not None:
            calculation.description = request.description
        if request.aggregation_function is not None:
            calculation.aggregation_function = request.aggregation_function
        if request.source_model is not None:
            calculation.source_model = request.source_model
        if request.source_field is not None:
            calculation.source_field = request.source_field
        if request.weight_field is not None:
            calculation.weight_field = request.weight_field
        if request.group_level is not None:
            calculation.group_level = request.group_level
        if request.advanced_config is not None:
            calculation.advanced_config = request.advanced_config

        # Validate weighted average has weight field
        if (calculation.aggregation_function == AggregationFunction.WEIGHTED_AVG 
            and not calculation.weight_field):
            raise InvalidCalculationError("Weighted average calculations require a weight_field")

        return self.user_calc_dao.update(calculation)

    def delete_user_calculation(self, calc_id: int) -> Dict[str, str]:
        """Soft delete a user calculation"""
        calculation = self.get_user_calculation_by_id(calc_id)
        if not calculation:
            raise CalculationNotFoundError(f"User calculation with ID {calc_id} not found")

        self.user_calc_dao.soft_delete(calculation)
        return {"message": f"User calculation '{calculation.name}' deleted successfully"}

    def get_user_calculation_usage(self, calc_id: int, report_scope: Optional[str] = None) -> Dict[str, Any]:
        """Get usage information for a user calculation with scope awareness."""
        calculation = self.get_user_calculation_by_id(calc_id)
        if not calculation:
            raise CalculationNotFoundError(f"User calculation with ID {calc_id} not found")
        
        from app.reporting.models import ReportCalculation, Report
        from sqlalchemy.orm import joinedload
        
        # Find all reports that use this calculation using NEW FORMAT
        new_calc_id = f"user.{calculation.source_field}"
        
        # Base query - filter by calculation ID and active reports
        query = (
            self.user_calc_dao.db
            .query(ReportCalculation)
            .join(Report)
            .filter(
                ReportCalculation.calculation_id == new_calc_id,
                Report.is_active == True
            )
            .options(joinedload(ReportCalculation.report))
        )
        
        # Apply scope filter if provided
        if report_scope:
            query = query.filter(Report.scope == report_scope.upper())
        
        report_usages = query.all()
        
        reports = []
        for usage in report_usages:
            reports.append({
                "report_id": usage.report.id,
                "report_name": usage.report.name,
                "report_scope": usage.report.scope,
                "display_order": usage.display_order,
                "display_name": usage.display_name
            })
        
        # Return the NEW FORMAT calculation_id instead of the database ID
        result = {
            "calculation_id": new_calc_id,  # FIXED: Use new format instead of calc_id
            "calculation_name": calculation.name,
            "is_in_use": len(reports) > 0,
            "report_count": len(reports),
            "reports": reports,
        }
        
        if report_scope:
            result["scope_filter"] = report_scope.upper()
            result["scope_specific_usage"] = True
        
        return result


class SystemCalculationService:
    """Service for managing system-defined calculations"""

    def __init__(self, system_calc_dao: SystemCalculationDAO):
        self.system_calc_dao = system_calc_dao
        self._cdi_service: Optional['CDIVariableCalculationService'] = None
        
    def get_all_system_calculations(self, group_level: Optional[str] = None) -> List[SystemCalculation]:
        """Get all active system calculations with usage information"""
        group_level_enum = GroupLevel(group_level) if group_level else None
        calculations = self.system_calc_dao.get_all(group_level_enum)
        
        # Add usage information to each calculation
        for calc in calculations:
            try:
                usage_info = self.get_system_calculation_usage(calc.id)
                # Add usage info as attributes to the calculation object
                calc.usage_info = usage_info
            except Exception as e:
                # If usage fetch fails, provide default values
                calc.usage_info = {
                    "calculation_id": calc.id,
                    "calculation_name": calc.name,
                    "is_in_use": False,
                    "report_count": 0,
                    "reports": [],
                }
        
        return calculations

    def get_system_calculation_by_id(self, calc_id: int) -> Optional[SystemCalculation]:
        """Get system calculation by ID"""
        return self.system_calc_dao.get_by_id(calc_id)

    def get_system_calculation_by_result_column(self, result_column_name: str) -> Optional[SystemCalculation]:
        """Get system calculation by result_column_name"""
        return self.system_calc_dao.get_by_result_column_name(result_column_name)

    def create_system_calculation(self, request: SystemCalculationCreate, 
                                created_by: str = "admin") -> SystemCalculation:
        """Create a new system calculation"""
        
        # Check if calculation name already exists at this group level
        existing = self.system_calc_dao.get_by_name_and_group_level(request.name, request.group_level)
        
        if existing:
            raise CalculationAlreadyExistsError(
                f"System calculation with name '{request.name}' already exists at {request.group_level} level"
            )

        # Check if result_column_name is already in use
        existing_calc = self.get_system_calculation_by_result_column(request.result_column_name)
        if existing_calc:
            raise ValueError(f"Result column '{request.result_column_name}' is already in use by calculation '{existing_calc.name}'")

        # Basic SQL validation
        self._validate_system_sql(request.raw_sql, request.group_level, request.result_column_name)

        # Create new calculation
        calculation = SystemCalculation(
            name=request.name,
            description=request.description,
            raw_sql=request.raw_sql,
            result_column_name=request.result_column_name,
            group_level=request.group_level,
            metadata_config=request.metadata_config,
            created_by=created_by,
        )

        return self.system_calc_dao.create(calculation)

    def update_system_calculation(self, calc_id: int, request: SystemCalculationUpdate) -> SystemCalculation:
        """Update an existing system calculation"""
        calculation = self.get_system_calculation_by_id(calc_id)
        if not calculation:
            raise CalculationNotFoundError(f"System calculation with ID {calc_id} not found")

        # Check if another calculation with the same name exists at this group level (excluding current one)
        if request.name:
            group_level = request.group_level or calculation.group_level
            existing = self.system_calc_dao.get_by_name_and_group_level(request.name, group_level)
            
            if existing and existing.id != calc_id:
                raise CalculationAlreadyExistsError(
                    f"Another system calculation with name '{request.name}' already exists at that group level"
                )

        # If result_column_name is being updated, check for conflicts
        if request.result_column_name and request.result_column_name != calculation.result_column_name:
            existing_calc = self.get_system_calculation_by_result_column(request.result_column_name)
            if existing_calc and existing_calc.id != calc_id:
                raise ValueError(f"Result column '{request.result_column_name}' is already in use by calculation '{existing_calc.name}'")

        # Validate SQL if being updated
        if request.raw_sql:
            group_level = request.group_level or calculation.group_level
            result_column = request.result_column_name or calculation.result_column_name
            self._validate_system_sql(request.raw_sql, group_level, result_column)

        # Update fields that are provided
        if request.name is not None:
            calculation.name = request.name
        if request.description is not None:
            calculation.description = request.description
        if request.raw_sql is not None:
            calculation.raw_sql = request.raw_sql
        if request.result_column_name is not None:
            calculation.result_column_name = request.result_column_name
        if request.group_level is not None:
            calculation.group_level = request.group_level
        if request.metadata_config is not None:
            calculation.metadata_config = request.metadata_config

        return self.system_calc_dao.update(calculation)

    def approve_system_calculation(self, calc_id: int, approved_by: str) -> SystemCalculation:
        """Approve a system calculation"""
        calculation = self.get_system_calculation_by_id(calc_id)
        if not calculation:
            raise CalculationNotFoundError(f"System calculation with ID {calc_id} not found")

        from datetime import datetime
        calculation.approved_by = approved_by
        calculation.approval_date = datetime.now()
        
        return self.system_calc_dao.update(calculation)

    def delete_system_calculation(self, calc_id: int) -> Dict[str, str]:
        """Soft delete a system calculation"""
        calculation = self.get_system_calculation_by_id(calc_id)
        if not calculation:
            raise CalculationNotFoundError(f"System calculation with ID {calc_id} not found")

        self.system_calc_dao.soft_delete(calculation)
        return {"message": f"System calculation '{calculation.name}' deleted successfully"}

    def get_system_calculation_usage(self, calc_id: int, report_scope: Optional[str] = None) -> Dict[str, Any]:
        """Get usage information for a system calculation with scope awareness."""
        calculation = self.get_system_calculation_by_id(calc_id)
        if not calculation:
            raise CalculationNotFoundError(f"System calculation with ID {calc_id} not found")
        
        from app.reporting.models import ReportCalculation, Report
        from sqlalchemy.orm import joinedload
        
        # Find all reports that use this calculation using NEW FORMAT
        new_calc_id = f"system.{calculation.result_column_name}"
        
        # Base query - filter by calculation ID and active reports
        query = (
            self.system_calc_dao.db
            .query(ReportCalculation)
            .join(Report)
            .filter(
                ReportCalculation.calculation_id == new_calc_id,
                Report.is_active == True
            )
            .options(joinedload(ReportCalculation.report))
        )
        
        # Apply scope filter if provided
        if report_scope:
            query = query.filter(Report.scope == report_scope.upper())
        
        report_usages = query.all()
        
        reports = []
        for usage in report_usages:
            reports.append({
                "report_id": usage.report.id,
                "report_name": usage.report.name,
                "report_scope": usage.report.scope,
                "display_order": usage.display_order,
                "display_name": usage.display_name
            })
        
        # Return the NEW FORMAT calculation_id instead of the database ID
        result = {
            "calculation_id": new_calc_id,  # FIXED: Use new format instead of calc_id
            "calculation_name": calculation.name,
            "is_in_use": len(reports) > 0,
            "report_count": len(reports),
            "reports": reports,
        }
        
        if report_scope:
            result["scope_filter"] = report_scope.upper()
            result["scope_specific_usage"] = True
        
        return result

    def set_cdi_service(self, cdi_service: 'CDIVariableCalculationService'):
        """Set the CDI service for integration (dependency injection)"""
        self._cdi_service = cdi_service
    
    def is_cdi_variable_calculation(self, calc_id: int) -> bool:
        """Check if a calculation is a CDI variable calculation"""
        if not self._cdi_service:
            return False
        
        calculation = self.get_system_calculation_by_id(calc_id)
        if not calculation:
            return False
            
        return (
            calculation.metadata_config and 
            calculation.metadata_config.get("calculation_type") == "cdi_variable"
        )
    
    def get_calculation_type(self, calc_id: int) -> str:
        """Get the type of calculation (regular, cdi_variable, etc.)"""
        calculation = self.get_system_calculation_by_id(calc_id)
        if not calculation:
            return "unknown"
        
        if calculation.metadata_config:
            return calculation.metadata_config.get("calculation_type", "regular")
        
        return "regular"
    
    def execute_calculation_by_type(self, calc_id: int, **execution_params) -> Any:
        """Execute a calculation based on its type"""
        calc_type = self.get_calculation_type(calc_id)
        
        if calc_type == "cdi_variable" and self._cdi_service:
            # Extract parameters for CDI execution
            cycle_code = execution_params.get("cycle_code")
            deal_numbers = execution_params.get("deal_numbers", [])
            
            if not cycle_code or not deal_numbers:
                raise InvalidCalculationError(
                    "CDI variable calculations require 'cycle_code' and 'deal_numbers' parameters"
                )
            
            return self._cdi_service.execute_cdi_variable_calculation(
                calc_id, cycle_code, deal_numbers
            )
        
        elif calc_type == "regular":
            # Execute regular system calculation (your existing logic)
            return self._execute_regular_calculation(calc_id, **execution_params)
        
        else:
            raise InvalidCalculationError(f"Unknown calculation type: {calc_type}")
    
    def _execute_regular_calculation(self, calc_id: int, **execution_params) -> Any:
        """Execute a regular system calculation (implement your existing logic here)"""
        # This is where you'd put your existing system calculation execution logic
        # For now, just return a placeholder
        calculation = self.get_system_calculation_by_id(calc_id)
        if not calculation:
            raise CalculationNotFoundError(f"Calculation {calc_id} not found")
        
        # TODO: Implement your regular calculation execution logic
        raise NotImplementedError("Regular calculation execution not implemented yet")
    
    def get_calculations_by_type(self, calc_type: str, group_level: Optional[str] = None) -> List[SystemCalculation]:
        """Get calculations filtered by type"""
        all_calcs = self.get_all_system_calculations(group_level)
        
        if calc_type == "cdi_variable":
            return [
                calc for calc in all_calcs 
                if calc.metadata_config and calc.metadata_config.get("calculation_type") == "cdi_variable"
            ]
        elif calc_type == "regular":
            return [
                calc for calc in all_calcs 
                if not calc.metadata_config or calc.metadata_config.get("calculation_type") != "cdi_variable"
            ]
        else:
            return all_calcs

    def _validate_system_sql(self, sql: str, group_level: GroupLevel, result_column_name: str):
        """Enhanced validation for system SQL with CTE support"""
        if not sql or not sql.strip():
            raise InvalidCalculationError("raw_sql cannot be empty")
        
        sql_trimmed = sql.strip()
        sql_lower = sql_trimmed.lower()
        
        # Check for CTEs first
        has_ctes = sql_trimmed.upper().strip().startswith('WITH')
        
        if has_ctes:
            # For CTEs, validate the structure but extract the final SELECT for field validation
            if not self._validate_cte_structure(sql_trimmed):
                raise InvalidCalculationError("Invalid CTE structure")
            
            # Extract final SELECT for field validation
            final_select = self._extract_final_select_from_cte(sql_trimmed)
            if not final_select:
                raise InvalidCalculationError("Could not identify the final SELECT statement in CTE")
            
            # Validate the final SELECT
            final_select_lower = final_select.lower()
            if not final_select_lower.strip().startswith('select'):
                raise InvalidCalculationError("Final query in CTE must be a SELECT statement")
            
            if 'from' not in final_select_lower:
                raise InvalidCalculationError("Final SELECT in CTE must include a FROM clause")
            
            # Use final SELECT for field validation
            validation_sql = final_select_lower
        else:
            # For simple queries, validate normally
            if not sql_lower.startswith('select'):
                raise InvalidCalculationError("System SQL must be a SELECT statement")
            
            if 'from' not in sql_lower:
                raise InvalidCalculationError("System SQL must include a FROM clause")
            
            validation_sql = sql_lower
        
        # Check for dangerous operations on the entire SQL
        dangerous_keywords = ['drop', 'delete', 'insert', 'update', 'alter', 'truncate']
        for keyword in dangerous_keywords:
            if keyword in sql_lower:
                raise InvalidCalculationError(f"Dangerous operation '{keyword}' not allowed in system SQL")

        # Check for required fields based on group level (use validation_sql which is the final SELECT)
        if group_level == GroupLevel.DEAL:
            if 'deal.dl_nbr' not in validation_sql and 'dl_nbr' not in validation_sql:
                raise InvalidCalculationError("Deal-level SQL must include deal.dl_nbr for proper grouping")
        
        if group_level == GroupLevel.TRANCHE:
            if 'deal.dl_nbr' not in validation_sql and 'dl_nbr' not in validation_sql:
                raise InvalidCalculationError("Tranche-level SQL must include deal.dl_nbr for proper grouping")
            if 'tranche.tr_id' not in validation_sql and 'tr_id' not in validation_sql:
                raise InvalidCalculationError("Tranche-level SQL must include tranche.tr_id for proper grouping")
    
    def _validate_cte_structure(self, sql: str) -> bool:
        """Validate CTE structure and syntax"""
        import re
        
        # Check for basic CTE syntax
        if not re.search(r'WITH\s+\w+\s+AS\s*\(', sql, re.IGNORECASE):
            return False
        
        # Check for balanced parentheses
        paren_count = 0
        in_quotes = False
        quote_char = ''
        
        for i, char in enumerate(sql):
            prev_char = sql[i-1] if i > 0 else ''
            
            if (char == '"' or char == "'") and prev_char != '\\':
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = ''
            
            if not in_quotes:
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
        
        return paren_count == 0
    
    def _extract_final_select_from_cte(self, sql: str) -> str:
        """Extract the final SELECT statement from a CTE query"""
        paren_count = 0
        in_quotes = False
        quote_char = ''
        after_with = False
        final_select_start = -1
        
        for i, char in enumerate(sql):
            prev_char = sql[i-1] if i > 0 else ''
            next_few_chars = sql[i:i+6].upper()
            
            # Handle quotes
            if (char == '"' or char == "'") and prev_char != '\\':
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = ''
            
            if not in_quotes:
                # Track parentheses
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                
                # Check for WITH keyword
                if not after_with and next_few_chars.startswith('WITH '):
                    after_with = True
                
                # Look for SELECT after we've closed all CTE parentheses
                if (after_with and paren_count == 0 and 
                    next_few_chars.startswith('SELECT') and final_select_start == -1):
                    final_select_start = i
                    break
        
        # If we found the final SELECT, extract it
        if final_select_start != -1:
            return sql[final_select_start:].strip()
        
        # Fallback: look for the last SELECT statement
        import re
        select_matches = list(re.finditer(r'\bSELECT\b', sql, re.IGNORECASE))
        if select_matches:
            last_select_pos = select_matches[-1].start()
            return sql[last_select_pos:].strip()
        
        return None
        

class StaticFieldService:
    """Service for static field information"""

    @staticmethod
    def get_all_static_fields() -> List[StaticFieldInfo]:
        """Get all available static fields"""
        fields = get_all_static_fields()
        return [
            StaticFieldInfo(
                field_path=field_path,
                name=info['name'],
                description=info['description'],
                type=info['type'],
                required_models=info['required_models'],
                nullable=info['nullable']
            )
            for field_path, info in fields.items()
        ]

    @staticmethod
    def get_static_field_by_path(field_path: str) -> Optional[StaticFieldInfo]:
        """Get static field information by path"""
        info = get_static_field_info(field_path)
        if not info or info.get('type') == 'unknown':
            return None
        
        return StaticFieldInfo(
            field_path=field_path,
            name=info['name'],
            description=info['description'],
            type=info['type'],
            required_models=info['required_models'],
            nullable=info['nullable']
        )

    @staticmethod
    def get_static_fields_by_model(model_name: str) -> List[StaticFieldInfo]:
        """Get static fields for a specific model"""
        all_fields = StaticFieldService.get_all_static_fields()
        return [
            field for field in all_fields 
            if field.field_path.startswith(f"{model_name.lower()}.")
        ]


class CalculationConfigService:
    """Service for calculation configuration and metadata"""

    @staticmethod
    def get_aggregation_functions() -> List[Dict[str, str]]:
        """Get available aggregation functions"""
        return [
            {"value": "SUM", "label": "SUM - Total amount", "description": "Add all values together"},
            {"value": "AVG", "label": "AVG - Average", "description": "Calculate average value"},
            {"value": "COUNT", "label": "COUNT - Count records", "description": "Count number of records"},
            {"value": "MIN", "label": "MIN - Minimum value", "description": "Find minimum value"},
            {"value": "MAX", "label": "MAX - Maximum value", "description": "Find maximum value"},
            {"value": "WEIGHTED_AVG", "label": "WEIGHTED_AVG - Weighted average", 
             "description": "Calculate weighted average using specified weight field"},
        ]

    @staticmethod
    def get_source_models() -> List[Dict[str, str]]:
        """Get available source models"""
        return [
            {"value": "Deal", "label": "Deal", "description": "Base deal information"},
            {"value": "Tranche", "label": "Tranche", "description": "Tranche structure data"},
            {"value": "TrancheBal", "label": "TrancheBal", "description": "Tranche balance and performance data"},
        ]

    @staticmethod
    def get_group_levels() -> List[Dict[str, str]]:
        """Get available group levels"""
        return [
            {"value": "deal", "label": "Deal Level", "description": "Aggregate to deal level"},
            {"value": "tranche", "label": "Tranche Level", "description": "Aggregate to tranche level"},
        ]