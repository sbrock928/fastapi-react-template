# app/calculations/service.py
"""Simplified calculation service using the new separated model architecture"""

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
from .resolver import SimpleCalculationResolver, CalculationRequest, QueryFilters
from .schemas import (
    UserCalculationCreate,
    UserCalculationUpdate,
    SystemCalculationCreate,
    SystemCalculationUpdate,
    StaticFieldInfo
)


class ReportExecutionService:
    """Service for executing reports with mixed calculation types"""

    def __init__(self, dw_db: Session, config_db: Session):
        self.dw_db = dw_db
        self.config_db = config_db
        self.resolver = SimpleCalculationResolver(dw_db, config_db)

    def execute_report(self, calculation_requests: List[CalculationRequest], 
                      deal_tranche_map: Dict[int, List[str]], cycle_code: int, 
                      report_scope: str = None) -> Dict[str, Any]:
        """Execute a report with mixed calculation types"""

        filters = QueryFilters(deal_tranche_map, cycle_code, report_scope)
        result = self.resolver.resolve_report(calculation_requests, filters)

        return {
            'data': result['merged_data'],
            'metadata': {
                'total_rows': len(result['merged_data']),
                'calculations_executed': len(calculation_requests),
                'debug_info': result['debug_info'],
                'individual_sql_queries': {
                    alias: query_result.sql 
                    for alias, query_result in result['individual_queries'].items()
                }
            }
        }

    def preview_report_sql(self, calculation_requests: List[CalculationRequest],
                          deal_tranche_map: Dict[int, List[str]], cycle_code: int, 
                          report_scope: str = None) -> Dict[str, Any]:
        """Preview SQL queries without executing them"""

        filters = QueryFilters(deal_tranche_map, cycle_code, report_scope)
        
        # Generate SQL for each calculation
        sql_previews = {}
        for request in calculation_requests:
            try:
                query_result = self.resolver.resolve_single_calculation(request, filters)
                sql_previews[request.alias] = {
                    'sql': query_result.sql,
                    'columns': query_result.columns,
                    'calculation_type': query_result.calc_type,
                    'group_level': query_result.group_level
                }
            except Exception as e:
                sql_previews[request.alias] = {
                    'sql': f"-- ERROR: {str(e)}",
                    'columns': [],
                    'calculation_type': 'error',
                    'error': str(e)
                }

        return {
            'sql_previews': sql_previews,
            'parameters': {
                'deal_tranche_map': deal_tranche_map,
                'cycle_code': cycle_code,
                'report_scope': report_scope
            },
            'summary': {
                'total_calculations': len(calculation_requests),
                'static_fields': len([r for r in calculation_requests if r.calc_type == 'static_field']),
                'user_calculations': len([r for r in calculation_requests if r.calc_type == 'user_calculation']),
                'system_calculations': len([r for r in calculation_requests if r.calc_type == 'system_calculation'])
            }
        }


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

    def _validate_system_sql(self, sql: str, group_level: GroupLevel, result_column_name: str):
        """Basic validation for system SQL"""
        sql_lower = sql.lower().strip()
        
        if not sql_lower.startswith('select'):
            raise InvalidCalculationError("System SQL must be a SELECT statement")
        
        if 'from' not in sql_lower:
            raise InvalidCalculationError("System SQL must include a FROM clause")
        
        # Check for dangerous operations
        dangerous_keywords = ['drop', 'delete', 'insert', 'update', 'alter', 'truncate']
        for keyword in dangerous_keywords:
            if keyword in sql_lower:
                raise InvalidCalculationError(f"Dangerous operation '{keyword}' not allowed in system SQL")

        # Check for required fields based on group level
        if group_level == GroupLevel.DEAL:
            if 'deal.dl_nbr' not in sql_lower and 'dl_nbr' not in sql_lower:
                raise InvalidCalculationError("Deal-level SQL must include deal.dl_nbr for proper grouping")
        
        if group_level == GroupLevel.TRANCHE:
            if 'deal.dl_nbr' not in sql_lower and 'dl_nbr' not in sql_lower:
                raise InvalidCalculationError("Tranche-level SQL must include deal.dl_nbr for proper grouping")
            if 'tranche.tr_id' not in sql_lower and 'tr_id' not in sql_lower:
                raise InvalidCalculationError("Tranche-level SQL must include tranche.tr_id for proper grouping")


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