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
        if filters.report_scope == "TRANCHE" and ("Tranche" in required_models or "TrancheBal" in required_models):
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

    def _build_from_clause(self, required_models: List[str]) -> str:
        """Build FROM/JOIN clause based on required models"""
        base = "FROM deal"
        if "Tranche" in required_models:
            base += "\nJOIN tranche ON deal.dl_nbr = tranche.dl_nbr"
        if "TrancheBal" in required_models:
            base += "\nJOIN tranchebal ON tranche.dl_nbr = tranchebal.dl_nbr AND tranche.tr_id = tranchebal.tr_id"
        return base

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

    def _inject_filters_into_raw_sql(self, raw_sql: str, filters: QueryFilters) -> str:
        """Enhanced filter injection for complex SQL including CTEs"""
        sql_upper = raw_sql.upper()
        
        # Enhanced table detection - check for table references in FROM/JOIN clauses
        import re
        
        # Parse the SQL structure to understand CTEs vs main query
        sql_structure = self._parse_sql_structure(raw_sql)
        
        # Build appropriate filters based on tables used in the FINAL query OR CTE definitions
        filter_parts = []
        
        # Get tables from the final SELECT (after CTEs)
        final_query_tables = sql_structure.get('final_query_tables', set())
        all_tables = sql_structure.get('all_tables', set())
        
        # For CTEs, we need to check if the underlying CTE uses the standard tables
        # even if the final SELECT only references the CTE name
        if sql_structure.get('has_ctes', False):
            # If we have CTEs, use all tables from the entire SQL (including CTE definitions)
            # This ensures we add filters even when final SELECT only references CTE names
            tables_for_filtering = all_tables
        else:
            # For simple queries, only use final query tables
            tables_for_filtering = final_query_tables
        
        # Only add cycle filter if tranchebal table exists in any part of the query
        if 'TRANCHEBAL' in tables_for_filtering:
            filter_parts.append(f"tranchebal.cycle_cde = {filters.cycle_code}")
        
        # Build deal-tranche conditions based on tables used anywhere in the query
        deal_conditions = []
        for deal_id, tranche_ids in filters.deal_tranche_map.items():
            if 'TRANCHE' in tables_for_filtering and 'TRANCHEBAL' in tables_for_filtering and tranche_ids:
                # We have both tranche and tranchebal tables with specific tranches
                tranche_list = "', '".join(tranche_ids)
                deal_conditions.append(f"(deal.dl_nbr = {deal_id} AND tranche.tr_id IN ('{tranche_list}'))")
            elif 'DEAL' in tables_for_filtering:
                # We have deal table or want all tranches for this deal
                deal_conditions.append(f"deal.dl_nbr = {deal_id}")

        if deal_conditions:
            filter_parts.append(f"({' OR '.join(deal_conditions)})")
        
        # If no valid filters can be applied, return original SQL
        if not filter_parts:
            return raw_sql
            
        full_filter = ' AND '.join(filter_parts)

        # Smart injection based on SQL structure
        if sql_structure.get('has_ctes', False):
            # For CTEs, inject filters into the CTE definitions themselves, not the final SELECT
            return self._inject_filters_into_cte_definitions(raw_sql, full_filter)
        else:
            # Simple query - use existing logic
            return self._inject_filters_into_simple_query(raw_sql, full_filter)

    def _parse_sql_structure(self, sql: str) -> dict:
        """Parse SQL to understand CTEs, subqueries, and table usage"""
        import re
        
        structure = {
            'has_ctes': False,
            'has_subqueries': False,
            'cte_definitions': [],
            'final_query_start': 0,
            'final_query_tables': set(),
            'all_tables': set()
        }
        
        sql_upper = sql.upper()
        
        # Check for CTEs
        structure['has_ctes'] = sql_upper.strip().startswith('WITH')
        
        # Check for subqueries
        structure['has_subqueries'] = '(SELECT' in sql_upper
        
        if structure['has_ctes']:
            # Find where CTEs end and final query begins
            # Look for the pattern ") SELECT" that indicates end of CTE and start of main query
            cte_end_pattern = r'\)\s*SELECT\b'
            match = re.search(cte_end_pattern, sql, re.IGNORECASE)
            if match:
                structure['final_query_start'] = match.start() + 1  # Start after the )
                final_query = sql[structure['final_query_start']:]
                structure['final_query_tables'] = self._extract_tables_from_query(final_query)
            else:
                # Fallback: assume the entire query
                structure['final_query_tables'] = self._extract_tables_from_query(sql)
        else:
            # No CTEs, analyze the whole query
            structure['final_query_tables'] = self._extract_tables_from_query(sql)
        
        structure['all_tables'] = self._extract_tables_from_query(sql)
        
        return structure

    def _extract_tables_from_query(self, sql: str) -> set:
        """Extract table names from SQL query"""
        import re
        
        # Find all table references in FROM and JOIN clauses
        from_join_pattern = r'(?:FROM|JOIN)\s+(\w+)'
        table_matches = re.findall(from_join_pattern, sql.upper())
        
        return set(table_matches)

    def _inject_filters_into_cte_query(self, sql: str, filters: str, structure: dict) -> str:
        """Inject filters into CTE-based queries"""
        import re
        
        # Find the final SELECT statement after CTEs
        final_query_start = structure.get('final_query_start', 0)
        
        if final_query_start > 0:
            # Split the SQL into CTE part and final query part
            cte_part = sql[:final_query_start]
            final_part = sql[final_query_start:]
            
            # Inject filters into the final part
            modified_final = self._inject_filters_into_simple_query(final_part, filters)
            
            return cte_part + modified_final
        else:
            # Fallback to simple injection
            return self._inject_filters_into_simple_query(sql, filters)

    def _inject_filters_into_cte_definitions(self, sql: str, filters: str) -> str:
        """Inject filters into CTE definitions where the actual tables are referenced"""
        import re
        
        # Strategy: Find the CTE definition that contains the actual table joins
        # and inject filters there, rather than in the final SELECT
        
        # Split the SQL into CTE part and final SELECT part
        cte_end_pattern = r'\)\s*SELECT\b'
        match = re.search(cte_end_pattern, sql, re.IGNORECASE)
        
        if not match:
            # Fallback to simple injection if we can't parse the CTE structure
            return self._inject_filters_into_simple_query(sql, filters)
        
        cte_part = sql[:match.start() + 1]  # Include the closing )
        final_part = sql[match.start() + 1:]  # Start from SELECT
        
        # Find individual CTE definitions within the CTE part
        # Look for pattern: CTE_NAME AS (SELECT ... FROM actual_tables ...)
        cte_def_pattern = r'(\w+)\s+AS\s*\((.*?)\)(?=\s*,\s*\w+\s+AS\s*\(|\s*\)\s*SELECT|\s*$)'
        
        def inject_into_cte_def(match):
            cte_name = match.group(1)
            cte_body = match.group(2)
            
            # Check if this CTE definition contains actual table references
            if any(table in cte_body.upper() for table in ['DEAL', 'TRANCHE', 'TRANCHEBAL']):
                # This CTE uses actual tables, inject filters here
                modified_body = self._inject_filters_into_simple_query(cte_body, filters)
                return f"{cte_name} AS ({modified_body})"
            else:
                # This CTE doesn't use actual tables, leave it unchanged
                return match.group(0)
        
        # Apply the injection to each CTE definition
        modified_cte_part = re.sub(cte_def_pattern, inject_into_cte_def, cte_part, flags=re.IGNORECASE | re.DOTALL)
        
        # Return the complete modified SQL
        return modified_cte_part + final_part

    def _inject_filters_into_simple_query(self, sql: str, filters: str) -> str:
        """Inject filters into simple (non-CTE) queries"""
        import re
        
        sql_upper = sql.upper()
        
        if " WHERE " in sql_upper:
            # Already has WHERE clause, append with AND
            return sql + f" AND {filters}"
        else:
            # Find the correct insertion point using case-insensitive regex
            # WHERE must come before GROUP BY, HAVING, ORDER BY, LIMIT
            insert_keywords = [r'\bGROUP\s+BY\b', r'\bHAVING\b', r'\bORDER\s+BY\b', r'\bLIMIT\b']
            insert_position = len(sql)

            # Find the earliest clause that should come after WHERE
            for pattern in insert_keywords:
                match = re.search(pattern, sql, re.IGNORECASE)
                if match and match.start() < insert_position:
                    insert_position = match.start()

            # Insert WHERE clause at the correct position
            where_clause = f" WHERE {filters}"
            return sql[:insert_position] + where_clause + sql[insert_position:]
    
    def _execute_sql(self, sql: str) -> List[Dict[str, Any]]:
        """Execute SQL and return results as list of dictionaries"""
        try:
            result = self.dw_db.execute(text(sql))
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in result.fetchall()]
            
            # DEBUG: Log SQL execution for static fields - fixed the condition check
            sql_lower = sql.lower()
            if ('deal.' in sql_lower or 'cdi_file' in sql_lower or 'issr_cde' in sql_lower):
                print(f"DEBUG SQL: {sql}")
                print(f"DEBUG Result columns: {list(columns)}")
                print(f"DEBUG Result data: {data}")
            
            return data
        except Exception as e:
            # Return empty result set on error, but log it
            print(f"SQL Execution Error: {e}")
            print(f"Failed SQL: {sql}")
            return []