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
        for request in calc_requests:
            try:
                query_result = self.resolve_single_calculation(request, filters)
                individual_results[request.alias] = {
                    'query_result': query_result,
                    'data': self._execute_sql(query_result.sql)
                }
            except Exception as e:
                # Store error but continue processing other calculations
                individual_results[request.alias] = {
                    'query_result': QueryResult(f"-- ERROR: {str(e)}", [], "error"),
                    'data': [],
                    'error': str(e)
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

        # Add tranche info if needed
        if self._requires_tranche_data(request.field_path):
            base_columns.append("tranche.tr_id AS tranche_id")

        # Add the requested field
        base_columns.append(f"{request.field_path} AS {request.alias}")

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
        if self._requires_tranche_data(request.field_path):
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
                    key = (row.get('deal_number'), filters.cycle_code)
                    if key not in deal_level_data:
                        deal_level_data[key] = {'deal_number': row.get('deal_number'), 'cycle_code': filters.cycle_code}
                    deal_level_data[key][alias] = row.get(alias)

                elif query_result.group_level == "tranche":
                    key = (row.get('deal_number'), row.get('tranche_id'), filters.cycle_code)
                    if key not in tranche_level_data:
                        tranche_level_data[key] = {
                            'deal_number': row.get('deal_number'),
                            'tranche_id': row.get('tranche_id'),
                            'cycle_code': filters.cycle_code
                        }
                    tranche_level_data[key][alias] = row.get(alias)

                else:  # Static fields - could be either level
                    # Determine level based on presence of tranche_id
                    if 'tranche_id' in row and row.get('tranche_id') is not None:
                        key = (row.get('deal_number'), row.get('tranche_id'), filters.cycle_code)
                        if key not in tranche_level_data:
                            tranche_level_data[key] = {
                                'deal_number': row.get('deal_number'),
                                'tranche_id': row.get('tranche_id'),
                                'cycle_code': filters.cycle_code
                            }
                        tranche_level_data[key][alias] = row.get(alias)
                    else:
                        key = (row.get('deal_number'), filters.cycle_code)
                        if key not in deal_level_data:
                            deal_level_data[key] = {'deal_number': row.get('deal_number'), 'cycle_code': filters.cycle_code}
                        deal_level_data[key][alias] = row.get(alias)

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
        """Inject standard filters into system calculation SQL"""
        filter_parts = [f"tranchebal.cycle_cde = {filters.cycle_code}"]

        # Build deal-tranche filter
        deal_conditions = []
        for deal_id, tranche_ids in filters.deal_tranche_map.items():
            if tranche_ids:
                tranche_list = "', '".join(tranche_ids)
                deal_conditions.append(f"(deal.dl_nbr = {deal_id} AND tranche.tr_id IN ('{tranche_list}'))")
            else:
                deal_conditions.append(f"deal.dl_nbr = {deal_id}")

        if deal_conditions:
            filter_parts.append(f"({' OR '.join(deal_conditions)})")

        full_filter = ' AND '.join(filter_parts)

        # Inject into SQL
        if " WHERE " in raw_sql.upper():
            modified_sql = raw_sql + f" AND {full_filter}"
        else:
            # Find good insertion point
            sql_upper = raw_sql.upper()
            insert_keywords = [" GROUP BY ", " ORDER BY ", " HAVING ", " LIMIT "]
            insert_position = len(raw_sql)

            for keyword in insert_keywords:
                pos = sql_upper.find(keyword)
                if pos != -1 and pos < insert_position:
                    insert_position = pos

            where_clause = f" WHERE {full_filter}"
            modified_sql = raw_sql[:insert_position] + where_clause + raw_sql[insert_position:]

        return modified_sql

    def _execute_sql(self, sql: str) -> List[Dict[str, Any]]:
        """Execute SQL and return results as list of dictionaries"""
        try:
            result = self.dw_db.execute(text(sql))
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]
        except Exception as e:
            # Return empty result set on error, but log it
            print(f"SQL Execution Error: {e}")
            print(f"Failed SQL: {sql}")
            return []