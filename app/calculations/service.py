# app/calculations/service.py
"""Enhanced unified calculation service with dynamic SQL parameter injection"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from .models import Calculation, CalculationType, AggregationFunction, SourceModel, GroupLevel
from .field_introspection import FieldIntrospectionService
from .schemas import (
    UserAggregationCalculationCreate,
    SystemFieldCalculationCreate,
    SystemSqlCalculationCreate,
    DependentCalculationCreate,
    CalculationUpdate,
    CalculationResponse,
    CalculationListResponse,
    BulkCalculationOperation,
    BulkCalculationResponse,
    SqlValidationRequest,
    SqlValidationResult,
    PlaceholderInfo
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
        
        # Check for duplicate calculation names across all group levels
        self._validate_unique_calculation_name(request.name)
        
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
        
        # Check for duplicate calculation names across all group levels
        self._validate_unique_calculation_name(request.name)
        
        # Parse field path and get field info using dynamic introspection
        field_info = FieldIntrospectionService.get_field_by_path(request.field_path)
        if not field_info:
            raise InvalidCalculationError(f"Invalid field path: {request.field_path}")
        
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
        
        # Check for duplicate calculation names across all group levels
        self._validate_unique_calculation_name(request.name)
        
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

    def create_dependent_calculation(
        self, 
        request: DependentCalculationCreate, 
        created_by: str
    ) -> CalculationResponse:
        """Create a new dependent calculation that references other calculations"""
        
        # Check for duplicate calculation names across all group levels
        self._validate_unique_calculation_name(request.name)
        
        # Validate that all dependencies exist
        self._validate_calculation_dependencies(request.calculation_dependencies)
        
        # Validate the expression syntax
        self._validate_calculation_expression(request.calculation_expression, request.calculation_dependencies)
        
        # Store dependencies and expression in metadata_config
        metadata_config = {
            "calculation_dependencies": request.calculation_dependencies,
            "calculation_expression": request.calculation_expression,
            "dependency_validation": {
                "validated_at": datetime.utcnow().isoformat(),
                "dependencies_count": len(request.calculation_dependencies)
            }
        }
        
        calculation = Calculation(
            name=request.name,
            description=request.description,
            calculation_type=CalculationType.DEPENDENT_CALCULATION,
            group_level=request.group_level,
            result_column_name=request.result_column_name,
            metadata_config=metadata_config,
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

    def get_calculations_by_type(self, calculation_type_str: str, group_level: Optional[str] = None) -> List[CalculationResponse]:
        """Get calculations by type string (for router compatibility)"""
        # Convert string to CalculationType enum
        try:
            if calculation_type_str == "USER_AGGREGATION":
                calc_type = CalculationType.USER_AGGREGATION
            elif calculation_type_str == "SYSTEM_SQL":
                calc_type = CalculationType.SYSTEM_SQL
            elif calculation_type_str == "SYSTEM_FIELD":
                calc_type = CalculationType.SYSTEM_FIELD
            elif calculation_type_str == "DEPENDENT_CALCULATION":
                calc_type = CalculationType.DEPENDENT_CALCULATION
            else:
                return []
        except:
            return []
        
        # Build query
        query = self.config_db.query(Calculation).filter(
            Calculation.calculation_type == calc_type,
            Calculation.is_active == True
        )
        
        # Apply group level filter if provided
        if group_level:
            try:
                if group_level.lower() == "deal":
                    group_level_enum = GroupLevel.DEAL
                elif group_level.lower() == "tranche":
                    group_level_enum = GroupLevel.TRANCHE
                else:
                    group_level_enum = None
                
                if group_level_enum:
                    query = query.filter(Calculation.group_level == group_level_enum)
            except:
                pass  # If group level conversion fails, ignore the filter
        
        calculations = query.order_by(Calculation.name).all()
        return [self._to_response(calc) for calc in calculations]

    def approve_calculation(self, calc_id: int, approved_by: str) -> CalculationResponse:
        """Approve a calculation"""
        calculation = self.config_db.query(Calculation).filter_by(id=calc_id, is_active=True).first()
        if not calculation:
            raise CalculationNotFoundError(f"Calculation with ID {calc_id} not found")
        
        calculation.approved_by = approved_by
        calculation.approval_date = datetime.utcnow()
        
        self.config_db.commit()
        self.config_db.refresh(calculation)
        
        return self._to_response(calculation)

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
        
        # Check for duplicate calculation names if name is being updated
        if request.name and request.name != calculation.name:
            self._validate_unique_calculation_name(request.name, exclude_id=calc_id)
        
        # Update fields
        for field, value in request.model_dump(exclude_unset=True).items():
            if hasattr(calculation, field):
                setattr(calculation, field, value)
        
        calculation.updated_at = datetime.utcnow()
        
        # Re-validate SQL if it was updated
        if request.raw_sql and calculation.calculation_type in [CalculationType.SYSTEM_SQL]:
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
        
        # ENHANCED: Extract final SELECT statement for proper alias validation (especially for CTEs)
        final_select_sql = self._extract_final_select_statement(request.sql_text)
        if not final_select_sql:
            errors.append("Could not identify the final SELECT statement")
            final_select_sql = request.sql_text  # Fallback to full SQL
        
        # ENHANCED: More precise result column validation using final SELECT only
        result_column_found = False
        aliased_columns = []
        
        # Extract all AS aliases from the FINAL SELECT only (not the entire SQL)
        alias_pattern = r'\bAS\s+([a-zA-Z_][a-zA-Z0-9_]*)\b'
        alias_matches = re.finditer(alias_pattern, final_select_sql, re.IGNORECASE)
        for match in alias_matches:
            aliased_columns.append(match.group(1).lower())
        
        # Check if the result column appears as an alias
        result_column_lower = request.result_column_name.lower()
        if result_column_lower in aliased_columns:
            result_column_found = True
        
        # Also check if it appears as a direct column reference (without AS) in final SELECT
        if not result_column_found:
            direct_column_pattern = rf'\b{re.escape(request.result_column_name)}\b'
            if re.search(direct_column_pattern, final_select_sql, re.IGNORECASE):
                result_column_found = True
        
        # Report detailed error if result column not found
        if not result_column_found:
            if aliased_columns:
                errors.append(f"Result column '{request.result_column_name}' not found in final SELECT. SQL returns columns with aliases: {', '.join(aliased_columns)}. Please ensure your SQL returns a column named '{request.result_column_name}' using AS alias.")
            else:
                errors.append(f"Result column '{request.result_column_name}' not found in final SELECT clause. Please ensure your SQL returns a column named '{request.result_column_name}' using AS alias.")
        
        # Extract table names and columns (simplified)
        used_tables = []
        table_pattern = r'(?:FROM|JOIN)\s+(\w+)'
        for match in re.finditer(table_pattern, request.sql_text, re.IGNORECASE):
            used_tables.append(match.group(1).lower())
        
        final_select_columns = []
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', final_select_sql, re.IGNORECASE | re.DOTALL)
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
    
    def _extract_final_select_statement(self, sql: str) -> str:
        """Extract the final SELECT statement from SQL (especially for CTEs)"""
        sql_trimmed = sql.strip()
        
        # If it starts with WITH, find the final SELECT after all CTEs
        if re.match(r'^\s*WITH\b', sql_trimmed, re.IGNORECASE):
            # Find the last SELECT that's not inside parentheses
            paren_count = 0
            in_quotes = False
            quote_char = ''
            last_select_at_zero_depth = -1
            
            for i in range(len(sql_trimmed)):
                char = sql_trimmed[i]
                prev_char = sql_trimmed[i-1] if i > 0 else ''
                
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
                    
                    # Look for SELECT at depth 0 (not inside parentheses)
                    if paren_count == 0 and sql_trimmed[i:i+6].upper() == 'SELECT':
                        last_select_at_zero_depth = i
            
            if last_select_at_zero_depth != -1:
                return sql_trimmed[last_select_at_zero_depth:].strip()
        
        # For simple queries or if extraction fails, return the whole query
        return sql_trimmed

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
        """Execute a full report with multiple calculations using separate execution for better error handling"""
        
        # calculation_requests is already a list of CalculationRequest objects
        filters = QueryFilters(
            deal_tranche_map=deal_tranche_map,
            cycle_code=cycle_code,
            report_scope=report_scope
        )
        
        # Use the new separate execution method for better error handling and partial results
        return self.resolver.resolve_report_separately(calculation_requests, filters)

    def execute_report_unified(
        self,
        calculation_requests: List[CalculationRequest],
        deal_tranche_map: Dict[int, List[str]],
        cycle_code: int,
        report_scope: str = "TRANCHE"
    ) -> Dict[str, Any]:
        """Execute a full report with multiple calculations using the original unified CTE approach"""
        
        # Keep the original method available for backward compatibility
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

    # === USAGE TRACKING METHODS ===

    def get_calculation_usage(self, calc_id: int, calc_type: str, report_scope: Optional[str] = None) -> Dict[str, Any]:
        """Get usage information for any calculation type"""
        try:
            # Import here to avoid circular imports
            from app.reporting.models import Report, ReportCalculation
            
            # Get the calculation details first
            calculation = self.get_calculation_by_id(calc_id)
            if not calculation:
                return {
                    "calculation_id": calc_id,
                    "calculation_name": "Unknown",
                    "is_in_use": False,
                    "report_count": 0,
                    "reports": [],
                    "error": f"Calculation with ID {calc_id} not found"
                }
            
            # Build the calculation_id string based on type and calculation details
            if calc_type.lower() == 'user' or calculation.calculation_type == 'USER_AGGREGATION':
                calc_id_str = f"user.{calculation.source_field}"
            elif calc_type.lower() == 'system' or calculation.calculation_type == 'SYSTEM_SQL':
                calc_id_str = f"system.{calculation.result_column_name}"
            elif calc_type.lower() == 'dependent' or calculation.calculation_type == 'DEPENDENT_CALCULATION':
                # Dependent calculations use numeric IDs in reports
                calc_id_str = str(calc_id)
            else:
                # Fallback to numeric ID for unknown types
                calc_id_str = str(calc_id)
            
            # Query reports that use this calculation
            query = self.config_db.query(Report, ReportCalculation).join(
                ReportCalculation, Report.id == ReportCalculation.report_id
            ).filter(
                ReportCalculation.calculation_id == calc_id_str,
                Report.is_active == True
            )
            
            # Apply scope filter if provided
            if report_scope and report_scope.upper() in ['DEAL', 'TRANCHE']:
                query = query.filter(Report.scope == report_scope.upper())
            
            results = query.all()
            
            # Format the response
            reports = []
            for report, report_calc in results:
                reports.append({
                    "report_id": report.id,
                    "report_name": report.name,
                    "report_description": report.description,
                    "scope": report.scope,
                    "created_by": report.created_by,
                    "created_date": report.created_date.isoformat() if report.created_date else None,
                    "display_name": report_calc.display_name,
                    "display_order": report_calc.display_order
                })
            
            return {
                "calculation_id": calc_id,
                "calculation_name": calculation.name,
                "is_in_use": len(reports) > 0,
                "report_count": len(reports),
                "reports": reports,
                "calculation_type": calculation.calculation_type.value if calculation.calculation_type else "unknown",
                "scope_filter": report_scope
            }
            
        except Exception as e:
            print(f"Error getting calculation usage: {str(e)}")
            return {
                "calculation_id": calc_id,
                "calculation_name": "Unknown",
                "is_in_use": False,
                "report_count": 0,
                "reports": [],
                "error": str(e)
            }

    def get_user_calculation_usage(self, calc_id: int, report_scope: Optional[str] = None) -> Dict[str, Any]:
        """Get usage information for a user calculation"""
        return self.get_calculation_usage(calc_id, 'user', report_scope)

    def get_system_calculation_usage(self, calc_id: int, report_scope: Optional[str] = None) -> Dict[str, Any]:
        """Get usage information for a system calculation"""
        return self.get_calculation_usage(calc_id, 'system', report_scope)

    def get_dependent_calculation_usage(self, calc_id: int, report_scope: Optional[str] = None) -> Dict[str, Any]:
        """Get usage information for a dependent calculation"""
        return self.get_calculation_usage(calc_id, 'dependent', report_scope)

    # === UTILITY METHODS ===

    def _validate_unique_calculation_name(self, name: str, exclude_id: Optional[int] = None) -> None:
        """Validate that calculation name is unique across all group levels"""
        query = self.config_db.query(Calculation).filter(
            Calculation.name == name,
            Calculation.is_active == True
        )
        
        # Exclude the current calculation if updating
        if exclude_id:
            query = query.filter(Calculation.id != exclude_id)
        
        existing_calculation = query.first()
        if existing_calculation:
            raise InvalidCalculationError(
                f"Calculation name '{name}' already exists (ID: {existing_calculation.id}, "
                f"Group Level: {existing_calculation.group_level.value}). "
                f"Calculation names must be unique across all group levels."
            )

    def _validate_calculation_dependencies(self, dependencies: List[str]) -> None:
        """Validate that all calculation dependencies exist and are accessible"""
        for dep in dependencies:
            if dep.startswith("user."):
                source_field = dep[5:]  # Remove "user." prefix
                calc = self.config_db.query(Calculation).filter(
                    Calculation.calculation_type == CalculationType.USER_AGGREGATION,
                    Calculation.source_field == source_field,
                    Calculation.is_active == True
                ).first()
                if not calc:
                    raise InvalidCalculationError(f"Dependency not found: {dep}. No active user calculation with source_field '{source_field}'")
            
            elif dep.startswith("system."):
                result_column = dep[7:]  # Remove "system." prefix
                calc = self.config_db.query(Calculation).filter(
                    Calculation.calculation_type == CalculationType.SYSTEM_SQL,
                    Calculation.result_column_name == result_column,
                    Calculation.is_active == True
                ).first()
                if not calc:
                    raise InvalidCalculationError(f"Dependency not found: {dep}. No active system calculation with result_column '{result_column}'")
            
            else:
                raise InvalidCalculationError(f"Invalid dependency format: {dep}. Must be 'user.field_name' or 'system.column_name'")

    def _validate_calculation_expression(self, expression: str, dependencies: List[str]) -> None:
        """Validate that the calculation expression is syntactically correct"""
        # Check that all dependencies referenced in the expression are declared
        import re
        pattern = r'\$\{([^}]+)\}'
        referenced_vars = re.findall(pattern, expression)
        
        # Map dependencies to their variable names
        declared_vars = set()
        for dep in dependencies:
            if dep.startswith("user.") or dep.startswith("system."):
                var_name = dep.split(".", 1)[1]  # Get the part after the dot
                declared_vars.add(var_name)
        
        # Check that all referenced variables are declared
        for var in referenced_vars:
            if var not in declared_vars:
                raise InvalidCalculationError(
                    f"Expression references undefined variable: ${{{var}}}. "
                    f"Available variables: {', '.join(f'${{{v}}}' for v in sorted(declared_vars))}"
                )
        
        # Basic SQL injection protection for expressions
        dangerous_patterns = [
            r'\bDROP\b', r'\bDELETE\b', r'\bTRUNCATE\b',
            r'\bINSERT\b', r'\bUPDATE\b', r'\bALTER\b',
            r'\bEXEC\b', r'\bEXECUTE\b', r'--', r'/\*', r'\*/'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, expression, re.IGNORECASE):
                raise InvalidCalculationError(f"Expression contains potentially dangerous SQL operations")

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