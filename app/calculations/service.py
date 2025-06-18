# app/calculations/service.py
"""Enhanced unified calculation service with dynamic SQL parameter injection"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from .models import Calculation, CalculationType, AggregationFunction, SourceModel, GroupLevel, get_static_field_info
from .schemas import (
    UserAggregationCalculationCreate, SystemFieldCalculationCreate, SystemSqlCalculationCreate,
    CDIVariableCalculationCreate, CalculationUpdate, CalculationResponse,
    SqlValidationRequest, SqlValidationResult, PlaceholderInfo
)
from .resolver import EnhancedCalculationResolver, CalculationRequest, QueryFilters
from app.core.exceptions import CalculationNotFoundError, InvalidCalculationError
import re


class UnifiedCalculationService:
    """Unified service for all calculation types with dynamic SQL parameter injection"""

    def __init__(self, config_db: Session, dw_db: Session):
        self.config_db = config_db
        self.dw_db = dw_db
        self.resolver = EnhancedCalculationResolver(dw_db, config_db)

    # === CREATION METHODS ===

    def create_user_aggregation_calculation(
        self, 
        request: UserAggregationCalculationCreate, 
        created_by: str
    ) -> CalculationResponse:
        """Create a new user aggregation calculation"""
        
        # Create the calculation
        calculation = Calculation(
            name=request.name,
            description=request.description,
            calculation_type=CalculationType.USER_AGGREGATION,
            group_level=request.group_level,
            aggregation_function=request.aggregation_function,
            source_model=request.source_model,
            source_field=request.source_field,
            weight_field=request.weight_field,
            created_by=created_by
        )
        
        self.config_db.add(calculation)
        self.config_db.commit()
        self.config_db.refresh(calculation)
        
        return self._to_response(calculation)

    def create_system_field_calculation(
        self, 
        request: SystemFieldCalculationCreate, 
        created_by: str
    ) -> CalculationResponse:
        """Create a new system field calculation"""
        
        # Parse field path and get field info
        field_info = get_static_field_info(request.field_path)
        
        calculation = Calculation(
            name=request.name,
            description=request.description,
            calculation_type=CalculationType.SYSTEM_FIELD,
            group_level=request.group_level,
            source_field=request.field_path.split('.')[-1],  # Extract field name
            metadata_config={
                "field_path": request.field_path,
                "field_info": field_info
            },
            created_by=created_by
        )
        
        self.config_db.add(calculation)
        self.config_db.commit()
        self.config_db.refresh(calculation)
        
        return self._to_response(calculation)

    def create_system_sql_calculation(
        self, 
        request: SystemSqlCalculationCreate, 
        created_by: str
    ) -> CalculationResponse:
        """Create a new system SQL calculation with placeholder support"""
        
        # Extract placeholders and validate SQL
        validation_result = self.validate_sql(SqlValidationRequest(
            sql_text=request.raw_sql,
            group_level=request.group_level,
            result_column_name=request.result_column_name
        ))
        
        if not validation_result.is_valid:
            raise InvalidCalculationError(f"SQL validation failed: {'; '.join(validation_result.errors)}")
        
        # Prepare SQL parameters
        sql_parameters = request.sql_parameters or {}
        sql_parameters.update({
            "placeholders_used": validation_result.placeholders_used,
            "validation_info": {
                "has_ctes": validation_result.has_ctes,
                "has_subqueries": validation_result.has_subqueries,
                "used_tables": validation_result.used_tables
            }
        })
        
        calculation = Calculation(
            name=request.name,
            description=request.description,
            calculation_type=CalculationType.SYSTEM_SQL,
            group_level=request.group_level,
            raw_sql=request.raw_sql,
            result_column_name=request.result_column_name,
            sql_parameters=sql_parameters,
            created_by=created_by
        )
        
        self.config_db.add(calculation)
        self.config_db.commit()
        self.config_db.refresh(calculation)
        
        return self._to_response(calculation)

    def create_cdi_variable_calculation(
        self, 
        request: CDIVariableCalculationCreate, 
        created_by: str
    ) -> CalculationResponse:
        """Create a new CDI variable calculation"""
        
        # Generate SQL for CDI variable calculation
        cdi_sql = self._generate_cdi_sql(request)
        
        calculation = Calculation(
            name=request.name,
            description=request.description,
            calculation_type=CalculationType.CDI_VARIABLE,
            group_level=request.group_level,
            raw_sql=cdi_sql,
            result_column_name=request.result_column_name,
            metadata_config={
                "variable_pattern": request.variable_pattern,
                "tranche_mappings": request.tranche_mappings,
                "calculation_type": "cdi_variable"
            },
            created_by=created_by
        )
        
        self.config_db.add(calculation)
        self.config_db.commit()
        self.config_db.refresh(calculation)
        
        return self._to_response(calculation)

    # === RETRIEVAL METHODS ===

    def get_calculation_by_id(self, calc_id: int) -> Optional[CalculationResponse]:
        """Get a calculation by ID"""
        calculation = self.config_db.query(Calculation).filter_by(id=calc_id, is_active=True).first()
        return self._to_response(calculation) if calculation else None

    def get_user_calculation_by_id(self, calc_id: int) -> Optional[CalculationResponse]:
        """Get a user calculation by ID"""
        calculation = self.config_db.query(Calculation).filter_by(
            id=calc_id, 
            calculation_type=CalculationType.USER_AGGREGATION,
            is_active=True
        ).first()
        return self._to_response(calculation) if calculation else None

    def get_system_calculation_by_id(self, calc_id: int) -> Optional[CalculationResponse]:
        """Get a system calculation by ID"""
        calculation = self.config_db.query(Calculation).filter(
            Calculation.id == calc_id,
            Calculation.calculation_type.in_([CalculationType.SYSTEM_SQL, CalculationType.SYSTEM_FIELD]),
            Calculation.is_active == True
        ).first()
        return self._to_response(calculation) if calculation else None

    def get_user_calculation_by_source_field(self, source_field: str) -> Optional[CalculationResponse]:
        """Get a user calculation by source field"""
        calculation = self.config_db.query(Calculation).filter_by(
            source_field=source_field,
            calculation_type=CalculationType.USER_AGGREGATION,
            is_active=True
        ).first()
        return self._to_response(calculation) if calculation else None

    def get_user_calculation_by_source_field_and_scope(self, source_field: str, scope: str) -> Optional[CalculationResponse]:
        """Get a user calculation by source field and scope (group level)"""
        # Convert scope to group level
        if scope.upper() == "DEAL":
            group_level = GroupLevel.DEAL
        elif scope.upper() == "TRANCHE":
            group_level = GroupLevel.TRANCHE
        else:
            return None
        
        calculation = self.config_db.query(Calculation).filter_by(
            source_field=source_field,
            calculation_type=CalculationType.USER_AGGREGATION,
            group_level=group_level,
            is_active=True
        ).first()
        return self._to_response(calculation) if calculation else None

    def get_system_calculation_by_result_column(self, result_column: str) -> Optional[CalculationResponse]:
        """Get a system calculation by result column name"""
        calculation = self.config_db.query(Calculation).filter(
            Calculation.result_column_name == result_column,
            Calculation.calculation_type.in_([CalculationType.SYSTEM_SQL, CalculationType.SYSTEM_FIELD]),
            Calculation.is_active == True
        ).first()
        return self._to_response(calculation) if calculation else None

    def list_calculations(
        self, 
        calculation_type: Optional[CalculationType] = None,
        group_level: Optional[GroupLevel] = None,
        search_term: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List calculations with filtering and pagination"""
        
        query = self.config_db.query(Calculation).filter_by(is_active=True)
        
        # Apply filters
        if calculation_type:
            query = query.filter(Calculation.calculation_type == calculation_type)
        
        if group_level:
            query = query.filter(Calculation.group_level == group_level)
        
        if search_term:
            search_filter = or_(
                Calculation.name.ilike(f"%{search_term}%"),
                Calculation.description.ilike(f"%{search_term}%")
            )
            query = query.filter(search_filter)
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination and ordering
        calculations = query.order_by(Calculation.name).offset(offset).limit(limit).all()
        
        # Calculate statistics
        active_count = self.config_db.query(Calculation).filter_by(is_active=True).count()
        type_counts = {}
        for calc_type in CalculationType:
            count = self.config_db.query(Calculation).filter_by(
                calculation_type=calc_type, is_active=True
            ).count()
            type_counts[calc_type.value] = count
        
        return {
            "calculations": [self._to_response(calc) for calc in calculations],
            "total_count": total_count,
            "active_count": active_count,
            "calculation_types": type_counts
        }

    def get_available_placeholders(self) -> List[PlaceholderInfo]:
        """Get list of available SQL placeholders"""
        # Create a dummy calculation to get placeholder info
        dummy_calc = Calculation(
            name="dummy",
            description="dummy",
            calculation_type=CalculationType.SYSTEM_SQL,
            group_level=GroupLevel.DEAL,
            created_by="system"
        )
        
        placeholder_map = dummy_calc.get_available_placeholders()
        
        placeholders = []
        example_values = {
            "current_cycle": "202404",
            "previous_cycle": "202403",
            "cycle_minus_2": "202402",
            "deal_filter": "dl_nbr IN (101, 102, 103)",
            "tranche_filter": "(dl_nbr = 101 AND tr_id IN ('A', 'B'))",
            "deal_tranche_filter": "((dl_nbr = 101 AND tr_id IN ('A', 'B')) OR (dl_nbr = 102))",
            "deal_numbers": "101, 102, 103",
            "tranche_ids": "A', 'B', 'C",
        }
        
        for name, description in placeholder_map.items():
            placeholders.append(PlaceholderInfo(
                name=name,
                description=description,
                example_value=example_values.get(name, f"example_{name}")
            ))
        
        return placeholders

    # === UPDATE METHODS ===

    def update_calculation(self, calc_id: int, request: CalculationUpdate) -> CalculationResponse:
        """Update an existing calculation"""
        
        calculation = self.config_db.query(Calculation).filter_by(id=calc_id, is_active=True).first()
        if not calculation:
            raise CalculationNotFoundError(f"Calculation with ID {calc_id} not found")
        
        # Update fields
        for field, value in request.model_dump(exclude_unset=True).items():
            if hasattr(calculation, field):
                setattr(calculation, field, value)
        
        calculation.updated_at = datetime.utcnow()
        
        # Re-validate SQL if it was updated
        if request.raw_sql and calculation.calculation_type in [CalculationType.SYSTEM_SQL, CalculationType.CDI_VARIABLE]:
            validation_result = self.validate_sql(SqlValidationRequest(
                sql_text=request.raw_sql,
                group_level=calculation.group_level,
                result_column_name=calculation.result_column_name
            ))
            
            if not validation_result.is_valid:
                raise InvalidCalculationError(f"SQL validation failed: {'; '.join(validation_result.errors)}")
        
        self.config_db.commit()
        self.config_db.refresh(calculation)
        
        return self._to_response(calculation)

    def delete_calculation(self, calc_id: int) -> bool:
        """Soft delete a calculation"""
        calculation = self.config_db.query(Calculation).filter_by(id=calc_id, is_active=True).first()
        if not calculation:
            return False
        
        calculation.is_active = False
        self.config_db.commit()
        return True

    # === VALIDATION METHODS ===

    def validate_sql(self, request: SqlValidationRequest) -> SqlValidationResult:
        """Validate SQL with placeholder support"""
        
        # Create a dummy calculation for validation
        dummy_calc = Calculation(
            name="validation",
            description="validation",
            calculation_type=CalculationType.SYSTEM_SQL,
            group_level=request.group_level,
            raw_sql=request.sql_text,
            result_column_name=request.result_column_name,
            created_by="validation"
        )
        
        # Extract placeholders
        placeholders_used = list(dummy_calc.get_used_placeholders())
        
        # Basic validation
        errors = []
        warnings = []
        
        # Check for dangerous operations
        dangerous_patterns = [
            r'\bDROP\b', r'\bDELETE\s+FROM\b', r'\bTRUNCATE\b',
            r'\bINSERT\s+INTO\b', r'\bUPDATE\s+.*\bSET\b', r'\bALTER\b',
            r'\bCREATE\b', r'\bEXEC\b', r'\bEXECUTE\b'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, request.sql_text, re.IGNORECASE):
                errors.append("SQL contains dangerous operations that are not allowed")
                break
        
        # Validate placeholders
        valid_placeholders = dummy_calc.get_available_placeholders()
        for placeholder in placeholders_used:
            if placeholder not in valid_placeholders:
                errors.append(f"Invalid placeholder '{{{placeholder}}}'")
        
        # Check basic SQL structure
        sql_upper = request.sql_text.upper().strip()
        has_ctes = sql_upper.startswith('WITH')
        has_subqueries = '(' in request.sql_text and 'SELECT' in sql_upper
        
        if not has_ctes and not sql_upper.startswith('SELECT'):
            errors.append("SQL must be a SELECT statement or start with WITH for CTEs")
        
        # Validate required columns based on group level
        if request.group_level == GroupLevel.DEAL:
            if not re.search(r'\bdl_nbr\b', request.sql_text, re.IGNORECASE):
                errors.append("Deal-level calculations must include dl_nbr in SELECT clause")
        elif request.group_level == GroupLevel.TRANCHE:
            if not re.search(r'\bdl_nbr\b', request.sql_text, re.IGNORECASE):
                errors.append("Tranche-level calculations must include dl_nbr in SELECT clause")
            if not re.search(r'\btr_id\b', request.sql_text, re.IGNORECASE):
                errors.append("Tranche-level calculations must include tr_id in SELECT clause")
        
        # Check for result column
        if not re.search(rf'\b{re.escape(request.result_column_name)}\b', request.sql_text, re.IGNORECASE):
            errors.append(f"SQL must include result column '{request.result_column_name}'")
        
        # Extract table names and columns (simplified)
        used_tables = []
        table_pattern = r'(?:FROM|JOIN)\s+(\w+)'
        for match in re.finditer(table_pattern, request.sql_text, re.IGNORECASE):
            used_tables.append(match.group(1).lower())
        
        final_select_columns = []
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', request.sql_text, re.IGNORECASE | re.DOTALL)
        if select_match:
            # Simplified column extraction
            columns_text = select_match.group(1)
            # This is a basic extraction - a full parser would be more robust
            final_select_columns = [col.strip() for col in columns_text.split(',')]
        
        # Performance warnings
        if len(placeholders_used) > 5:
            warnings.append(f"High number of placeholders ({len(placeholders_used)}) may impact readability")
        
        if has_ctes and len(re.findall(r'WITH\s+\w+\s+AS', request.sql_text, re.IGNORECASE)) > 5:
            warnings.append("High number of CTEs may impact performance")
        
        return SqlValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            has_ctes=has_ctes,
            has_subqueries=has_subqueries,
            final_select_columns=final_select_columns,
            used_tables=used_tables,
            placeholders_used=placeholders_used
        )

    # === EXECUTION METHODS ===

    def preview_calculation(
        self,
        calc_id: int,
        deal_tranche_map: Dict[int, List[str]],
        cycle_code: int,
        report_scope: str = "TRANCHE"
    ) -> Dict[str, Any]:
        """Preview a single calculation with parameter injection"""
        
        calc_request = CalculationRequest(calc_id=calc_id, alias=f"calc_{calc_id}")
        filters = QueryFilters(
            deal_tranche_map=deal_tranche_map,
            cycle_code=cycle_code,
            report_scope=report_scope
        )
        
        return self.resolver.resolve_single_calculation(calc_request, filters)

    def execute_report(
        self,
        calculation_requests: List[CalculationRequest],
        deal_tranche_map: Dict[int, List[str]],
        cycle_code: int,
        report_scope: str = "TRANCHE"
    ) -> Dict[str, Any]:
        """Execute a full report with multiple calculations"""
        
        # calculation_requests is already a list of CalculationRequest objects
        filters = QueryFilters(
            deal_tranche_map=deal_tranche_map,
            cycle_code=cycle_code,
            report_scope=report_scope
        )
        
        return self.resolver.resolve_report(calculation_requests, filters)

    def preview_report_sql(
        self,
        calculation_requests: List[CalculationRequest],
        deal_tranche_map: Dict[int, List[str]],
        cycle_code: int,
        report_scope: str = "TRANCHE"
    ) -> Dict[str, Any]:
        """Preview the SQL that would be generated for a report without executing it"""
        
        filters = QueryFilters(
            deal_tranche_map=deal_tranche_map,
            cycle_code=cycle_code,
            report_scope=report_scope
        )
        
        try:
            # Initialize the parameter injector first
            from .resolver import DynamicParameterInjector
            self.resolver.parameter_injector = DynamicParameterInjector(filters)
            
            # Use the resolver to generate the unified SQL without execution
            unified_sql = self.resolver._build_unified_query(calculation_requests, filters)
            
            return {
                "sql_preview": unified_sql,
                "parameters_used": self.resolver.parameter_injector.get_parameter_values(),
                "calculation_count": len(calculation_requests),
                "deal_count": len(deal_tranche_map),
                "scope": report_scope
            }
        except Exception as e:
            return {
                "error": f"Failed to generate SQL preview: {str(e)}",
                "calculation_requests": [{"calc_id": req.calc_id, "alias": req.alias} for req in calculation_requests],
                "debug_info": {
                    "deal_tranche_map": deal_tranche_map,
                    "cycle_code": cycle_code,
                    "report_scope": report_scope
                }
            }

    # === UTILITY METHODS ===

    def _to_response(self, calculation: Calculation) -> CalculationResponse:
        """Convert calculation model to response schema"""
        return CalculationResponse(
            id=calculation.id,
            name=calculation.name,
            description=calculation.description,
            calculation_type=calculation.calculation_type,
            group_level=calculation.group_level,
            aggregation_function=calculation.aggregation_function,
            source_model=calculation.source_model,
            source_field=calculation.source_field,
            weight_field=calculation.weight_field,
            raw_sql=calculation.raw_sql,
            result_column_name=calculation.result_column_name,
            sql_parameters=calculation.sql_parameters,
            metadata_config=calculation.metadata_config,
            created_by=calculation.created_by,
            approved_by=calculation.approved_by,
            is_active=calculation.is_active,
            display_formula=calculation.get_display_formula(),
            complexity_score=calculation.get_complexity_score(),
            used_placeholders=list(calculation.get_used_placeholders()),
            required_models=calculation.get_required_models()
        )

    def _generate_cdi_sql(self, request: CDIVariableCalculationCreate) -> str:
        """Generate SQL for CDI variable calculation"""
        
        if request.group_level == GroupLevel.DEAL:
            # Deal-level CDI calculation
            variable_name = request.variable_pattern  # Should be exact variable name for deal level
            return f"""
SELECT 
    cdi.dl_nbr,
    cdi.dl_cdi_var_value as {request.result_column_name}
FROM deal_cdi_var_rpt cdi
WHERE cdi.dl_cdi_var_nme = '{variable_name.ljust(32)}'
    AND cdi.cycle_cde = {{current_cycle}}
    AND {{deal_filter}}
ORDER BY cdi.dl_nbr
""".strip()
        
        else:
            # Tranche-level CDI calculation with mappings
            if not request.tranche_mappings:
                raise InvalidCalculationError("Tranche mappings are required for tranche-level CDI calculations")
            
            union_queries = []
            for suffix, tr_id_list in request.tranche_mappings.items():
                variable_name = request.variable_pattern.replace("{tranche_suffix}", suffix)
                tr_id_filter = "', '".join(tr_id_list)
                
                union_queries.append(f"""
    SELECT 
        cdi.dl_nbr,
        tb.tr_id,
        cdi.dl_cdi_var_value as {request.result_column_name}
    FROM deal_cdi_var_rpt cdi
    INNER JOIN tranchebal tb ON cdi.dl_nbr = tb.dl_nbr AND cdi.cycle_cde = tb.cycle_cde
    WHERE cdi.dl_cdi_var_nme = '{variable_name.ljust(32)}'
        AND cdi.cycle_cde = {{current_cycle}}
        AND {{deal_tranche_filter}}
        AND tb.tr_id IN ('{tr_id_filter}')""")
            
            return ("\nUNION ALL\n".join(union_queries) + "\nORDER BY dl_nbr, tr_id").strip()