# app/calculations/resolver.py
"""Simple calculation resolver that generates debuggable SQL queries"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .models import UserCalculation, SystemCalculation, AggregationFunction, get_static_field_info


@dataclass
class CalculationRequest:
    """Represents a single calculation to resolve"""
    calc_type: str  # "static_field", "user_calculation", "system_calculation"
    calc_id: Optional[int] = None  # For user/system calculations
    field_path: Optional[str] = None  # For static fields: "deal.dl_nbr", "tranche.tr_id", etc.
    alias: Optional[str] = None  # Custom alias for the result column

    def __post_init__(self):
        if not self.alias:
            if self.calc_id:
                self.alias = f"calc_{self.calc_id}"
            elif self.field_path:
                self.alias = self.field_path.replace(".", "_")
            else:
                self.alias = "unknown"


@dataclass
class QueryFilters:
    """Standard filters applied to all calculations"""
    deal_tranche_map: Dict[int, List[str]]  # deal_id -> [tranche_ids] or [] for all
    cycle_code: int
    report_scope: Optional[str] = None  # "DEAL" or "TRANCHE" - determines output grouping


@dataclass
class QueryResult:
    """Result from a single calculation resolution"""
    sql: str
    columns: List[str]
    calc_type: str
    group_level: Optional[str] = None


class SimpleCalculationResolver:
    """Generates simple, debuggable SQL for each calculation type"""

    def __init__(self, dw_db: Session, config_db: Session):
        self.dw_db = dw_db
        self.config_db = config_db

    def resolve_report(self, calc_requests: List[CalculationRequest], filters: QueryFilters) -> Dict[str, Any]:
        """Main entry point - resolves all calculations and merges results"""

        # 1. Resolve each calculation to individual SQL queries
        individual_results = {}
        # Store calculation requests for later reference
        calc_request_lookup = {req.alias: req for req in calc_requests}
        
        for request in calc_requests:
            try:
                query_result = self.resolve_single_calculation(request, filters)
                individual_results[request.alias] = {
                    'query_result': query_result,
                    'data': self._execute_sql(query_result.sql),
                    'original_request': request  # Store original request for field_path access
                }
            except Exception as e:
                # Store error but continue processing other calculations
                individual_results[request.alias] = {
                    'query_result': QueryResult(f"-- ERROR: {str(e)}", [], "error"),
                    'data': [],
                    'error': str(e),
                    'original_request': request
                }

        # 2. Merge results in memory based on common keys
        merged_data = self._merge_calculation_results(individual_results, filters)

        return {
            'merged_data': merged_data,
            'individual_queries': {alias: result['query_result'] for alias, result in individual_results.items()},
            'debug_info': {
                'total_calculations': len(calc_requests),
                'static_fields': len([r for r in calc_requests if r.calc_type == 'static_field']),
                'user_calculations': len([r for r in calc_requests if r.calc_type == 'user_calculation']),
                'system_calculations': len([r for r in calc_requests if r.calc_type == 'system_calculation']),
                'errors': [alias for alias, result in individual_results.items() if 'error' in result]
            }
        }

    def resolve_single_calculation(self, request: CalculationRequest, filters: QueryFilters) -> QueryResult:
        """Route to appropriate resolver for this calculation type"""
        if request.calc_type == "static_field":
            return self._resolve_static_field(request, filters)
        elif request.calc_type == "user_calculation":
            return self._resolve_user_calculation(request, filters)
        elif request.calc_type == "system_calculation":
            return self._resolve_system_calculation(request, filters)
        else:
            raise ValueError(f"Unknown calculation type: {request.calc_type}")

    def _resolve_static_field(self, request: CalculationRequest, filters: QueryFilters) -> QueryResult:
        """Generate SQL for static model fields (no aggregation)"""
        if not request.field_path:
            raise ValueError("field_path is required for static_field calculations")

        field_info = get_static_field_info(request.field_path)

        # Build simple SELECT with required JOINs based on what's actually needed
        base_columns = ["deal.dl_nbr AS deal_number"]
        
        # Only include cycle_code if we actually have TrancheBal data
        required_models = field_info['required_models']
        if "TrancheBal" in required_models:
            base_columns.append("tranchebal.cycle_cde AS cycle_code")

        # FIXED: Only include tranche_id if BOTH report scope is TRANCHE AND we need tranche data
        # This prevents tranche_id from appearing in deal-only static field queries
        if filters.report_scope == "TRANCHE" and ("Tranche" in required_models or "TrancheBal" in required_models):
            base_columns.append("tranche.tr_id AS tranche_id")

        # Add the requested field - handle special cases for quoted column names
        field_path = request.field_path
        # Quote the alias if it contains spaces or special characters
        quoted_alias = f'"{request.alias}"' if ' ' in request.alias or any(c in request.alias for c in ['-', '.', '/', '\\']) else request.alias
        
        if field_path == "deal.CDB_cdi_file_nme":
            # Special handling for the quoted column name
            base_columns.append(f'deal."CDB_cdi_file_nme" AS {quoted_alias}')
        else:
            base_columns.append(f"{field_path} AS {quoted_alias}")

        # Build FROM/JOIN clause based on required models
        from_clause = self._build_from_clause(required_models)

        # Build WHERE clause - only include cycle filter if TrancheBal is involved
        where_conditions = []
        
        # Build deal-tranche conditions
        deal_conditions = []
        for deal_id, tranche_ids in filters.deal_tranche_map.items():
            if "Tranche" in required_models and tranche_ids:  # Only filter tranches if we have Tranche model
                tranche_list = "', '".join(tranche_ids)
                deal_conditions.append(f"(deal.dl_nbr = {deal_id} AND tranche.tr_id IN ('{tranche_list}'))")
            else:  # Deal-only or all tranches for this deal
                deal_conditions.append(f"deal.dl_nbr = {deal_id}")

        if deal_conditions:
            where_conditions.append(f"({' OR '.join(deal_conditions)})")
        
        # Only add cycle filter if TrancheBal is involved
        if "TrancheBal" in required_models:
            where_conditions.append(f"tranchebal.cycle_cde = {filters.cycle_code}")

        where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""

        sql = f"""SELECT DISTINCT {', '.join(base_columns)}
{from_clause}
{where_clause}"""

        # Build result columns based on what's actually included
        columns = ["deal_number"]
        if "TrancheBal" in required_models:
            columns.append("cycle_code")
        if filters.report_scope == "TRANCE" and ("Tranche" in required_models or "TrancheBal" in required_models):
            columns.append("tranche_id")
        columns.append(request.alias)

        return QueryResult(sql, columns, "static_field")

    def _resolve_user_calculation(self, request: CalculationRequest, filters: QueryFilters) -> QueryResult:
        """Generate SQL for user-defined aggregations"""
        if not request.calc_id:
            raise ValueError("calc_id is required for user_calculation")

        calc = self.config_db.query(UserCalculation).filter_by(id=request.calc_id, is_active=True).first()
        if not calc:
            raise ValueError(f"User calculation {request.calc_id} not found")

        # Build aggregation expression
        agg_field = f"{calc.source_model.value.lower()}.{calc.source_field}"

        if calc.aggregation_function == AggregationFunction.SUM:
            agg_expr = f"SUM({agg_field})"
        elif calc.aggregation_function == AggregationFunction.AVG:
            agg_expr = f"AVG({agg_field})"
        elif calc.aggregation_function == AggregationFunction.COUNT:
            agg_expr = f"COUNT({agg_field})"
        elif calc.aggregation_function == AggregationFunction.MIN:
            agg_expr = f"MIN({agg_field})"
        elif calc.aggregation_function == AggregationFunction.MAX:
            agg_expr = f"MAX({agg_field})"
        elif calc.aggregation_function == AggregationFunction.WEIGHTED_AVG:
            if not calc.weight_field:
                raise ValueError(f"Weight field required for weighted average calculation {calc.name}")
            weight_field = f"{calc.source_model.value.lower()}.{calc.weight_field}"
            agg_expr = f"SUM({agg_field} * {weight_field}) / NULLIF(SUM({weight_field}), 0)"
        else:
            raise ValueError(f"Unsupported aggregation function: {calc.aggregation_function}")

        # Build GROUP BY columns
        if calc.group_level.value == "deal":
            group_columns = ["deal.dl_nbr"]
            select_columns = ["deal.dl_nbr AS deal_number", "tranchebal.cycle_cde AS cycle_code"]
            result_columns = ["deal_number", "cycle_code"]
        else:  # TRANCHE level
            group_columns = ["deal.dl_nbr", "tranche.tr_id"]
            select_columns = ["deal.dl_nbr AS deal_number", "tranche.tr_id AS tranche_id", "tranchebal.cycle_cde AS cycle_code"]
            result_columns = ["deal_number", "tranche_id", "cycle_code"]

        select_columns.append(f'{agg_expr} AS "{request.alias}"')
        result_columns.append(request.alias)

        # Build FROM/JOIN clause - always include all tables for user calculations
        from_clause = """FROM deal
JOIN tranche ON deal.dl_nbr = tranche.dl_nbr
JOIN tranchebal ON tranche.dl_nbr = tranchebal.dl_nbr AND tranche.tr_id = tranchebal.tr_id"""

        # Apply filters
        where_clause = self._build_where_clause(filters)

        # Apply any advanced config filters (future expansion)
        if calc.advanced_config and 'filters' in calc.advanced_config:
            additional_filters = self._build_advanced_filters(calc.advanced_config['filters'])
            where_clause = f"{where_clause} AND {additional_filters}"

        sql = f"""SELECT {', '.join(select_columns)}
{from_clause}
{where_clause}
GROUP BY {', '.join(group_columns)}"""

        return QueryResult(sql, result_columns, "user_calculation", calc.group_level.value)

    def _resolve_system_calculation(self, request: CalculationRequest, filters: QueryFilters) -> QueryResult:
        """Generate SQL for system-defined raw SQL calculations"""
        if not request.calc_id:
            raise ValueError("calc_id is required for system_calculation")

        calc = self.config_db.query(SystemCalculation).filter_by(id=request.calc_id, is_active=True).first()
        if not calc:
            raise ValueError(f"System calculation {request.calc_id} not found")

        # Inject filters into the raw SQL
        modified_sql = self._inject_filters_into_raw_sql(calc.raw_sql, filters)

        # Determine result columns based on group level
        if calc.group_level.value == "deal":
            result_columns = ["dl_nbr", calc.result_column_name]
        else:  # TRANCHE level
            result_columns = ["dl_nbr", "tr_id", calc.result_column_name]

        return QueryResult(modified_sql, result_columns, "system_calculation", calc.group_level.value)

    def _merge_calculation_results(self, individual_results: Dict[str, Any], filters: QueryFilters) -> List[Dict[str, Any]]:
        """Merge results from different calculations based on common keys"""

        # Group results by their key structure
        deal_level_data = {}  # key: (deal_id, cycle_code)
        tranche_level_data = {}  # key: (deal_id, tranche_id, cycle_code)

        # Organize data by level
        for alias, result_info in individual_results.items():
            if 'error' in result_info:
                continue  # Skip errored calculations

            data = result_info['data']
            query_result = result_info['query_result']

            for row in data:
                if query_result.group_level == "deal":
                    # Handle system calculations that may have different column names
                    deal_number = row.get('deal_number') or row.get('dl_nbr')
                    key = (deal_number, filters.cycle_code)
                    if key not in deal_level_data:
                        deal_level_data[key] = {'deal_number': deal_number, 'cycle_code': filters.cycle_code}
                    
                    # Store the result using the alias name, but get the actual value from the result column
                    result_value = row.get(alias)
                    if result_value is None and query_result.calc_type == "system_calculation":
                        # For system calculations, try to get the value using the result column name
                        # Fallback: try common result column patterns
                        for possible_col in row.keys():
                            if possible_col not in ['dl_nbr', 'deal_number', 'tr_id', 'tranche_id', 'cycle_code', 'cycle_cde']:
                                result_value = row.get(possible_col)
                                break
                    deal_level_data[key][alias] = result_value

                elif query_result.group_level == "tranche":
                    # Handle system calculations that may have different column names
                    deal_number = row.get('deal_number') or row.get('dl_nbr')
                    tranche_id = row.get('tranche_id') or row.get('tr_id')
                    key = (deal_number, tranche_id, filters.cycle_code)
                    if key not in tranche_level_data:
                        tranche_level_data[key] = {
                            'deal_number': deal_number,
                            'tranche_id': tranche_id,
                            'cycle_code': filters.cycle_code
                        }
                    
                    # Store the result using the alias name
                    result_value = row.get(alias)
                    if result_value is None and query_result.calc_type == "system_calculation":
                        # For system calculations, try to find the actual result column
                        for possible_col in row.keys():
                            if possible_col not in ['dl_nbr', 'deal_number', 'tr_id', 'tranche_id', 'cycle_code', 'cycle_cde']:
                                result_value = row.get(possible_col)
                                break
                    tranche_level_data[key][alias] = result_value

                else:  # Static fields - could be either level
                    # FIXED: For static fields, we need to properly extract the field value
                    # Use the original request to get the field_path
                    original_request = result_info.get('original_request')
                    
                    # DEBUG: Enhanced logging for static field value extraction
                    print(f"DEBUG: Processing static field - Alias: '{alias}'")
                    print(f"  Available row keys: {list(row.keys())}")
                    print(f"  Row data: {row}")
                    
                    # Try to get the field value using the alias first
                    field_value = row.get(alias)
                    print(f"  Initial field_value for alias '{alias}': {field_value}")
                    
                    # If not found by alias, try other methods
                    if field_value is None and original_request and original_request.field_path:
                        field_path = original_request.field_path
                        print(f"  Trying field_path: {field_path}")
                        
                        # Try the field path directly (e.g., 'deal.cdi_file_nme')
                        field_value = row.get(field_path)
                        print(f"  Field value by field_path: {field_value}")
                        
                        if field_value is None:
                            # Try just the field name (e.g., 'cdi_file_nme')
                            field_name = field_path.split('.')[-1] if '.' in field_path else field_path
                            field_value = row.get(field_name)
                            print(f"  Field value by field_name '{field_name}': {field_value}")
                            
                        # Try looking for any key that contains the field name
                        if field_value is None:
                            field_name = field_path.split('.')[-1] if '.' in field_path else field_path
                            for row_key in row.keys():
                                if field_name.lower() in row_key.lower():
                                    field_value = row.get(row_key)
                                    print(f"  Found field value by partial match '{row_key}': {field_value}")
                                    break
                    
                    print(f"  Final field_value: {field_value}")
                    
                    # FIXED: Determine level based on the field_path, not just presence of tranche_id in row
                    field_path = original_request.field_path if original_request else ""
                    is_deal_level_field = field_path.startswith("deal.") or field_path in ["deal.dl_nbr", "deal.issr_cde", "deal.cdi_file_nme", "deal.CDB_cdi_file_nme"]
                    
                    if is_deal_level_field:
                        # This is a deal-level static field - store in deal_level_data
                        key = (row.get('deal_number'), filters.cycle_code)
                        if key not in deal_level_data:
                            deal_level_data[key] = {'deal_number': row.get('deal_number'), 'cycle_code': filters.cycle_code}
                        deal_level_data[key][alias] = field_value
                        print(f"  Added deal-level static field to deal_level_data[{key}][{alias}] = {field_value}")
                    elif 'tranche_id' in row and row.get('tranche_id') is not None:
                        # This is a tranche-level static field or default field with tranche_id
                        key = (row.get('deal_number'), row.get('tranche_id'), filters.cycle_code)
                        if key not in tranche_level_data:
                            tranche_level_data[key] = {
                                'deal_number': row.get('deal_number'),
                                'tranche_id': row.get('tranche_id'),
                                'cycle_code': filters.cycle_code
                            }
                        tranche_level_data[key][alias] = field_value
                        print(f"  Added tranche-level static field to tranche_level_data[{key}][{alias}] = {field_value}")
                    else:
                        # Default static field without tranche info - treat as deal-level
                        key = (row.get('deal_number'), filters.cycle_code)
                        if key not in deal_level_data:
                            deal_level_data[key] = {'deal_number': row.get('deal_number'), 'cycle_code': filters.cycle_code}
                        deal_level_data[key][alias] = field_value
                        print(f"  Added default static field to deal_level_data[{key}][{alias}] = {field_value}")

        # Merge deal-level data into tranche-level data where appropriate
        final_data = []

        if tranche_level_data:
            # We have tranche-level results
            for (deal_id, tranche_id, cycle_code), tranche_row in tranche_level_data.items():
                # Merge in any deal-level calculations
                deal_key = (deal_id, cycle_code)
                if deal_key in deal_level_data:
                    for field, value in deal_level_data[deal_key].items():
                        if field not in ['deal_number', 'cycle_code']:  # Don't overwrite keys
                            tranche_row[field] = value
                final_data.append(tranche_row)
        else:
            # Only deal-level results
            final_data = list(deal_level_data.values())

        return final_data

    # ===== HELPER METHODS =====

    def _requires_tranche_data(self, field_path: str) -> bool:
        """Check if field requires tranche-level data"""
        return field_path.startswith("tranche.") or field_path.startswith("tranchebal.")

    def _build_advanced_filters(self, filter_config: List[Dict[str, Any]]) -> str:
        """Build additional WHERE conditions from advanced config (future expansion)"""
        conditions = []
        for filter_def in filter_config:
            field = filter_def['field']
            operator = filter_def['operator']
            value = filter_def['value']

            if isinstance(value, str):
                conditions.append(f"{field} {operator} '{value}'")
            else:
                conditions.append(f"{field} {operator} {value}")

        return ' AND '.join(conditions)

    def _execute_sql(self, sql: str) -> List[Dict[str, Any]]:
        """Execute SQL and return results as list of dictionaries"""
        try:
            result = self.dw_db.execute(text(sql))
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]
        except Exception as e:
            print(f"SQL Execution Error: {e}")
            print(f"Failed SQL: {sql}")
            raise

class UnifiedCalculationResolver:
    """Generates a single unified SQL query with CTEs for all calculations"""

    def __init__(self, dw_db: Session, config_db: Session):
        self.dw_db = dw_db
        self.config_db = config_db

    def resolve_report(self, calc_requests: List[CalculationRequest], filters: QueryFilters) -> Dict[str, Any]:
        """Generate a single unified SQL query with CTEs for all calculations"""
        
        # Build the unified SQL query
        unified_sql = self._build_unified_query(calc_requests, filters)
        
        # Execute the unified query
        try:
            result_data = self._execute_sql(unified_sql)
            
            return {
                'merged_data': result_data,
                'unified_sql': unified_sql,
                'debug_info': {
                    'total_calculations': len(calc_requests),
                    'static_fields': len([r for r in calc_requests if r.calc_type == 'static_field']),
                    'user_calculations': len([r for r in calc_requests if r.calc_type == 'user_calculation']),
                    'system_calculations': len([r for r in calc_requests if r.calc_type == 'system_calculation']),
                    'query_type': 'unified',
                    'rows_returned': len(result_data)
                }
            }
        except Exception as e:
            return {
                'merged_data': [],
                'unified_sql': unified_sql,
                'error': str(e),
                'debug_info': {
                    'total_calculations': len(calc_requests),
                    'query_type': 'unified',
                    'execution_error': True,
                    'error_message': str(e)
                }
            }

    def _build_unified_query(self, calc_requests: List[CalculationRequest], filters: QueryFilters) -> str:
        """Build a single SQL query with CTEs for all calculations"""
        
        # Separate requests by type
        static_requests = [r for r in calc_requests if r.calc_type == 'static_field']
        user_requests = [r for r in calc_requests if r.calc_type == 'user_calculation']
        system_requests = [r for r in calc_requests if r.calc_type == 'system_calculation']
        
        # Build CTEs for calculations
        ctes = []
        
        # Add user calculation CTEs
        for request in user_requests:
            cte = self._build_user_calculation_cte(request, filters)
            if cte:
                ctes.append(cte)
        
        # Add system calculation CTEs
        for request in system_requests:
            cte = self._build_system_calculation_cte(request, filters)
            if cte:
                ctes.append(cte)
        
        # Build base query with static fields
        base_query = self._build_base_query(static_requests, filters)
        
        # Combine everything
        if ctes:
            # Add base_data CTE to the list
            base_cte = f"base_data AS (\n{self._indent_sql(base_query, 4)}\n)"
            ctes.append(base_cte)
            
            # Build the final SELECT that joins everything
            final_select = self._build_final_select(calc_requests, filters)
            
            # Combine: WITH all_ctes final_select
            return "WITH " + ",\n\n".join(ctes) + "\n\n" + final_select
        else:
            # No CTEs needed, just return the base query
            return base_query

    def _build_base_query(self, static_requests: List[CalculationRequest], filters: QueryFilters) -> str:
        """Build the base query with all static fields"""
        
        # Determine required models from static fields
        required_models = set(['Deal'])  # Always need Deal
        
        for request in static_requests:
            if request.field_path:
                field_info = get_static_field_info(request.field_path)
                required_models.update(field_info['required_models'])
        
        # Build base columns
        base_columns = ["deal.dl_nbr"]
        
        # Add tranche info if needed
        if filters.report_scope == "TRANCHE" and ('Tranche' in required_models or 'TrancheBal' in required_models):
            base_columns.append("tranche.tr_id")
            required_models.add('Tranche')
        
        # Add cycle code if needed
        if 'TrancheBal' in required_models:
            base_columns.append("tranchebal.cycle_cde")
        
        # Add all static fields
        for request in static_requests:
            if request.field_path:
                # Quote the alias if it contains spaces or special characters
                quoted_alias = f'"{request.alias}"' if ' ' in request.alias or any(c in request.alias for c in ['-', '.', '/', '\\']) else request.alias
                
                if request.field_path == "deal.CDB_cdi_file_nme":
                    base_columns.append(f'deal."CDB_cdi_file_nme" AS {quoted_alias}')
                else:
                    base_columns.append(f"{request.field_path} AS {quoted_alias}")
        
        # Build FROM clause
        from_clause = self._build_from_clause(list(required_models))
        
        # Build WHERE clause
        where_clause = self._build_where_clause_for_base(filters, required_models)
        
        return f"""SELECT DISTINCT {', '.join(base_columns)}
{from_clause}
{where_clause}"""

    def _build_user_calculation_cte(self, request: CalculationRequest, filters: QueryFilters) -> Optional[str]:
        """Build CTE for a user calculation"""
        try:
            calc = self.config_db.query(UserCalculation).filter_by(id=request.calc_id, is_active=True).first()
            if not calc:
                return None
            
            # Build aggregation expression
            agg_field = f"{calc.source_model.value.lower()}.{calc.source_field}"
            
            if calc.aggregation_function == AggregationFunction.SUM:
                agg_expr = f"SUM({agg_field})"
            elif calc.aggregation_function == AggregationFunction.AVG:
                agg_expr = f"AVG({agg_field})"
            elif calc.aggregation_function == AggregationFunction.COUNT:
                agg_expr = f"COUNT({agg_field})"
            elif calc.aggregation_function == AggregationFunction.MIN:
                agg_expr = f"MIN({agg_field})"
            elif calc.aggregation_function == AggregationFunction.MAX:
                agg_expr = f"MAX({agg_field})"
            elif calc.aggregation_function == AggregationFunction.WEIGHTED_AVG:
                if not calc.weight_field:
                    return None
                weight_field = f"{calc.source_model.value.lower()}.{calc.weight_field}"
                agg_expr = f"SUM({agg_field} * {weight_field}) / NULLIF(SUM({weight_field}), 0)"
            else:
                return None
            
            # Create safe CTE name by removing spaces and special characters
            safe_cte_name = request.alias.replace(' ', '_').replace('-', '_').replace('.', '_')
            
            # Quote the result alias if it contains spaces or special characters
            quoted_alias = f'"{request.alias}"' if ' ' in request.alias or any(c in request.alias for c in ['-', '.', '/', '\\']) else request.alias
            
            # Build GROUP BY based on calculation level
            if calc.group_level.value == "deal":
                group_columns = ["deal.dl_nbr"]
                select_columns = ["deal.dl_nbr", f"{agg_expr} AS {quoted_alias}"]
            else:  # TRANCHE level
                group_columns = ["deal.dl_nbr", "tranche.tr_id"]
                select_columns = ["deal.dl_nbr", "tranche.tr_id", f"{agg_expr} AS {quoted_alias}"]
            
            # Build the CTE
            where_clause = self._build_where_clause(filters)
            
            return f"""{safe_cte_name}_cte AS (
    SELECT {', '.join(select_columns)}
    FROM deal
    JOIN tranche ON deal.dl_nbr = tranche.dl_nbr
    JOIN tranchebal ON tranche.dl_nbr = tranchebal.dl_nbr AND tranche.tr_id = tranchebal.tr_id
    {where_clause}
    GROUP BY {', '.join(group_columns)}
)"""
        
        except Exception as e:
            # Return a comment CTE for debugging
            safe_cte_name = request.alias.replace(' ', '_').replace('-', '_').replace('.', '_')
            return f"""{safe_cte_name}_cte AS (
    -- ERROR: {str(e)}
    SELECT NULL AS dl_nbr, NULL AS "{request.alias}"
    WHERE FALSE
)"""

    def _build_system_calculation_cte(self, request: CalculationRequest, filters: QueryFilters) -> Optional[str]:
        """Build CTE for a system calculation"""
        try:
            calc = self.config_db.query(SystemCalculation).filter_by(id=request.calc_id, is_active=True).first()
            if not calc:
                return None
            
            # Create safe CTE name by removing spaces and special characters
            safe_cte_name = request.alias.replace(' ', '_').replace('-', '_').replace('.', '_')
            
            # Inject filters into the system SQL
            modified_sql = self._inject_filters_into_raw_sql(calc.raw_sql, filters)
            
            # Quote the result alias if it contains spaces or special characters
            quoted_alias = f'"{request.alias}"' if ' ' in request.alias or any(c in request.alias for c in ['-', '.', '/', '\\']) else request.alias
            
            # SMART COLUMN DETECTION: Analyze the SQL to determine what columns are actually available
            sql_upper = modified_sql.upper()
            
            # Look for primary key column patterns in the SQL
            dl_nbr_column = None
            tr_id_column = None
            
            # Check for different dl_nbr column patterns
            if 'DEAL.DL_NBR AS DEAL_NUMBER' in sql_upper:
                dl_nbr_column = 'deal_number'
            elif 'DL_NBR AS DEAL_NUMBER' in sql_upper:
                dl_nbr_column = 'deal_number'
            elif 'DEAL.DL_NBR' in sql_upper or 'SELECT DL_NBR' in sql_upper:
                dl_nbr_column = 'dl_nbr'
            else:
                # Default fallback
                dl_nbr_column = 'dl_nbr'
            
            # Check for tr_id patterns if this is tranche level
            if calc.group_level.value == "tranche":
                if 'TRANCHE.TR_ID AS TRANCHE_ID' in sql_upper:
                    tr_id_column = 'tranche_id'
                elif 'TR_ID AS TRANCHE_ID' in sql_upper:
                    tr_id_column = 'tranche_id'
                elif 'TRANCHE.TR_ID' in sql_upper or 'SELECT TR_ID' in sql_upper:
                    tr_id_column = 'tr_id'
                else:
                    tr_id_column = 'tr_id'
            
            # Handle different group levels properly for system calculations
            if calc.group_level.value == "deal":
                # Deal-level system calculation - only select dl_nbr
                if calc.result_column_name != request.alias:
                    wrapped_sql = f"""SELECT sys_calc.{dl_nbr_column} as dl_nbr, {calc.result_column_name} AS {quoted_alias}
FROM ({modified_sql}) AS sys_calc"""
                else:
                    # Need to ensure dl_nbr is properly aliased
                    if dl_nbr_column != 'dl_nbr':
                        wrapped_sql = f"""SELECT sys_calc.{dl_nbr_column} as dl_nbr, sys_calc.{quoted_alias}
FROM ({modified_sql}) AS sys_calc"""
                    else:
                        wrapped_sql = modified_sql
            else:  # TRANCHE level
                # Tranche-level system calculation - select both dl_nbr and tr_id
                if calc.result_column_name != request.alias:
                    wrapped_sql = f"""SELECT sys_calc.{dl_nbr_column} as dl_nbr, sys_calc.{tr_id_column} as tr_id, {calc.result_column_name} AS {quoted_alias}
FROM ({modified_sql}) AS sys_calc"""
                else:
                    # Need to ensure columns are properly aliased
                    if dl_nbr_column != 'dl_nbr' or tr_id_column != 'tr_id':
                        wrapped_sql = f"""SELECT sys_calc.{dl_nbr_column} as dl_nbr, sys_calc.{tr_id_column} as tr_id, sys_calc.{quoted_alias}
FROM ({modified_sql}) AS sys_calc"""
                    else:
                        wrapped_sql = modified_sql
            
            # Wrap the system SQL in a CTE
            return f"""{safe_cte_name}_cte AS (
    {self._indent_sql(wrapped_sql, 4)}
)"""
        
        except Exception as e:
            # Return a comment CTE for debugging
            safe_cte_name = request.alias.replace(' ', '_').replace('-', '_').replace('.', '_')
            return f"""{safe_cte_name}_cte AS (
    -- ERROR: {str(e)}
    SELECT NULL AS dl_nbr, NULL AS "{request.alias}"
    WHERE FALSE
)"""

    def _build_final_select(self, calc_requests: List[CalculationRequest], filters: QueryFilters) -> str:
        """Build the final SELECT that joins all CTEs"""
        
        # Build select columns
        select_columns = []
        
        # Add base columns
        if filters.report_scope == "TRANCHE":
            select_columns.extend(["base_data.dl_nbr", "base_data.tr_id", "base_data.cycle_cde"])
        else:
            select_columns.extend(["base_data.dl_nbr", "base_data.cycle_cde"])
        
        # Add static field columns
        for request in calc_requests:
            if request.calc_type == 'static_field':
                # Quote the column reference if the alias contains spaces
                quoted_alias = f'"{request.alias}"' if ' ' in request.alias or any(c in request.alias for c in ['-', '.', '/', '\\']) else request.alias
                select_columns.append(f"base_data.{quoted_alias}")
        
        # Build joins and add calculation columns
        joins = []
        for request in calc_requests:
            if request.calc_type in ['user_calculation', 'system_calculation']:
                # Create safe CTE name by removing spaces and special characters
                safe_cte_name = request.alias.replace(' ', '_').replace('-', '_').replace('.', '_')
                cte_alias = f"{safe_cte_name}_cte"
                
                # Determine join condition based on report scope
                if filters.report_scope == "TRANCHE":
                    join_condition = f"base_data.dl_nbr = {cte_alias}.dl_nbr AND base_data.tr_id = {cte_alias}.tr_id"
                else:
                    join_condition = f"base_data.dl_nbr = {cte_alias}.dl_nbr"
                
                joins.append(f"LEFT JOIN {cte_alias} ON {join_condition}")
                
                # Quote the column reference if the alias contains spaces
                quoted_alias = f'"{request.alias}"' if ' ' in request.alias or any(c in request.alias for c in ['-', '.', '/', '\\']) else request.alias
                select_columns.append(f"{cte_alias}.{quoted_alias}")
        
        # Build final query
        final_query = f"""SELECT {', '.join(select_columns)}
FROM base_data
{chr(10).join(joins)}
ORDER BY base_data.dl_nbr"""
        
        if filters.report_scope == "TRANCHE":
            final_query += ", base_data.tr_id"
        
        return final_query

    def _build_from_clause(self, required_models: List[str]) -> str:
        """Build FROM/JOIN clause based on required models"""
        base = "FROM deal"
        if "Tranche" in required_models:
            base += "\nJOIN tranche ON deal.dl_nbr = tranche.dl_nbr"
        if "TrancheBal" in required_models:
            base += "\nJOIN tranchebal ON deal.dl_nbr = tranchebal.dl_nbr AND tranche.tr_id = tranchebal.tr_id"
        return base

    def _build_where_clause_for_base(self, filters: QueryFilters, required_models: set) -> str:
        """Build WHERE clause for base query"""
        conditions = []
        
        # Build deal-tranche conditions
        deal_conditions = []
        for deal_id, tranche_ids in filters.deal_tranche_map.items():
            if "Tranche" in required_models and tranche_ids:
                tranche_list = "', '".join(tranche_ids)
                deal_conditions.append(f"(deal.dl_nbr = {deal_id} AND tranche.tr_id IN ('{tranche_list}'))")
            else:
                deal_conditions.append(f"deal.dl_nbr = {deal_id}")
        
        if deal_conditions:
            conditions.append(f"({' OR '.join(deal_conditions)})")
        
        # Add cycle filter if TrancheBal is involved
        if "TrancheBal" in required_models:
            conditions.append(f"tranchebal.cycle_cde = {filters.cycle_code}")
        
        return f"WHERE {' AND '.join(conditions)}" if conditions else ""

    def _build_where_clause(self, filters: QueryFilters) -> str:
        """Build WHERE clause from standard filters"""
        conditions = [f"tranchebal.cycle_cde = {filters.cycle_code}"]

        # Build deal-tranche conditions
        deal_conditions = []
        for deal_id, tranche_ids in filters.deal_tranche_map.items():
            if tranche_ids:  # Specific tranches
                tranche_list = "', '".join(tranche_ids)
                deal_conditions.append(f"(deal.dl_nbr = {deal_id} AND tranche.tr_id IN ('{tranche_list}'))")
            else:  # All tranches for this deal
                deal_conditions.append(f"deal.dl_nbr = {deal_id}")

        if deal_conditions:
            conditions.append(f"({' OR '.join(deal_conditions)})")

        return f"WHERE {' AND '.join(conditions)}"

    def _inject_filters_into_raw_sql(self, raw_sql: str, filters: QueryFilters) -> str:
        """Inject filters into system SQL with improved logic for deal vs tranche level"""
        
        # Check if the SQL contains tranchebal - if not, we can't use tranchebal filters
        sql_upper = raw_sql.upper()
        has_tranchebal = 'TRANCHEBAL' in sql_upper
        has_tranche = 'TRANCHE' in sql_upper and 'TRANCHE' != 'TRANCHEBAL'  # Avoid matching tranchebal
        
        # Build filter parts based on what tables are available
        filter_parts = []
        
        # Only add cycle filter if tranchebal is in the query
        if has_tranchebal:
            filter_parts.append(f"tranchebal.cycle_cde = {filters.cycle_code}")
        
        # Build deal-tranche conditions based on available tables
        deal_conditions = []
        for deal_id, tranche_ids in filters.deal_tranche_map.items():
            if has_tranche and tranche_ids:
                # We have tranche table and specific tranche filtering
                tranche_list = "', '".join(tranche_ids)
                deal_conditions.append(f"(deal.dl_nbr = {deal_id} AND tranche.tr_id IN ('{tranche_list}'))")
            else:
                # Deal-only filtering (either no tranche table or no tranche filtering needed)
                deal_conditions.append(f"deal.dl_nbr = {deal_id}")
        
        if deal_conditions:
            filter_parts.append(f"({' OR '.join(deal_conditions)})")
        
        # If no filters can be applied, return original SQL
        if not filter_parts:
            return raw_sql
        
        full_filter = ' AND '.join(filter_parts)
        
        # Check if this is a complex CTE query that we should skip filter injection for
        if sql_upper.startswith('WITH') and 'FROM deal_metrics' in raw_sql:
            # This is the complex CTE calculation - return original SQL without filter injection
            return raw_sql
        
        # For simple queries, use the original logic
        if " WHERE " in sql_upper:
            return raw_sql + f" AND {full_filter}"
        else:
            # Find insertion point before GROUP BY, ORDER BY, etc.
            import re
            insert_keywords = [r'\bGROUP\s+BY\b', r'\bORDER\s+BY\b', r'\bHAVING\b', r'\bLIMIT\b']
            insert_position = len(raw_sql)
            
            for pattern in insert_keywords:
                match = re.search(pattern, raw_sql, re.IGNORECASE)
                if match and match.start() < insert_position:
                    insert_position = match.start()
            
            return raw_sql[:insert_position] + f" WHERE {full_filter} " + raw_sql[insert_position:]

    def _indent_sql(self, sql: str, spaces: int) -> str:
        """Indent SQL for better formatting in CTEs"""
        indent = " " * spaces
        return "\n".join(indent + line for line in sql.split("\n"))

    def _execute_sql(self, sql: str) -> List[Dict[str, Any]]:
        """Execute SQL and return results as list of dictionaries"""
        try:
            result = self.dw_db.execute(text(sql))
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]
        except Exception as e:
            print(f"SQL Execution Error: {e}")
            print(f"Failed SQL: {sql}")
            raise