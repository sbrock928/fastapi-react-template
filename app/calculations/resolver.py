# app/calculations/resolver.py
"""Unified calculation resolver that generates optimized SQL queries with CTEs"""

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
        
        # FIXED: Filter out CDI calculations from system requests
        regular_system_requests = []
        for request in system_requests:
            if request.calc_id:
                calc = self.config_db.query(SystemCalculation).filter_by(id=request.calc_id, is_active=True).first()
                if not (calc and calc.metadata_config and 
                        calc.metadata_config.get("calculation_type") == "cdi_variable"):
                    regular_system_requests.append(request)
        
        # Build CTEs for calculations
        ctes = []
        
        # Add user calculation CTEs
        for request in user_requests:
            cte = self._build_user_calculation_cte(request, filters)
            if cte:
                ctes.append(cte)
        
        # Add system calculation CTEs (only non-CDI ones)
        for request in regular_system_requests:
            cte = self._build_system_calculation_cte(request, filters)
            if cte:
                ctes.append(cte)
        
        # FIXED: Always build a base query, even if no static fields
        # This ensures we have the foundation data structure
        base_query = self._build_base_query(static_requests, filters, user_requests + regular_system_requests)
        
        # Combine everything
        if ctes:
            # Add base_data CTE to the list
            base_cte = f"base_data AS (\n{self._indent_sql(base_query, 4)}\n)"
            ctes.append(base_cte)
            
            # Build the final SELECT that joins everything
            final_select = self._build_final_select(static_requests + user_requests + regular_system_requests, filters)
            
            # Combine: WITH all_ctes final_select
            return "WITH " + ",\n\n".join(ctes) + "\n\n" + final_select
        else:
            # No CTEs needed, just return the base query
            return base_query

    def _build_base_query(self, static_requests: List[CalculationRequest], filters: QueryFilters, calculation_requests: List[CalculationRequest] = None) -> str:
        """Build the base query with all static fields - FIXED to always provide foundation data"""
        
        # Determine required models from static fields
        required_models = set(['Deal'])  # Always need Deal
        
        for request in static_requests:
            if request.field_path:
                field_info = get_static_field_info(request.field_path)
                required_models.update(field_info['required_models'])
        
        # FIXED: If no static fields but we have calculations, ensure we have proper scope support
        if not static_requests and calculation_requests:
            # Check if any calculations need tranche-level data
            for request in calculation_requests:
                if request.calc_type == 'user_calculation' and request.calc_id:
                    calc = self.config_db.query(UserCalculation).filter_by(id=request.calc_id, is_active=True).first()
                    if calc and calc.group_level.value == "tranche":
                        required_models.add('Tranche')
                        required_models.add('TrancheBal')
                elif request.calc_type == 'system_calculation' and request.calc_id:
                    calc = self.config_db.query(SystemCalculation).filter_by(id=request.calc_id, is_active=True).first()
                    if calc and calc.group_level.value == "tranche":
                        required_models.add('Tranche')
                        required_models.add('TrancheBal')
        
        # Build base columns
        base_columns = ["deal.dl_nbr"]
        
        # Add tranche info if needed
        if filters.report_scope == "TRANCHE" or any(req.calc_type in ['user_calculation', 'system_calculation'] for req in (calculation_requests or [])):
            if 'Tranche' in required_models or 'TrancheBal' in required_models or filters.report_scope == "TRANCHE":
                base_columns.append("tranche.tr_id")
                required_models.add('Tranche')
        
        # Add cycle code if needed  
        if 'TrancheBal' in required_models or any(req.calc_type in ['user_calculation', 'system_calculation'] for req in (calculation_requests or [])):
            base_columns.append("tranchebal.cycle_cde")
            required_models.add('TrancheBal')
        
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
        """Build CTE for a system calculation with CLEAN filter wrapping approach - FIXED join logic"""
        try:
            calc = self.config_db.query(SystemCalculation).filter_by(id=request.calc_id, is_active=True).first()
            if not calc:
                return None
            
            # SKIP CDI VARIABLE CALCULATIONS - they should be handled separately
            if (calc.metadata_config and 
                calc.metadata_config.get("calculation_type") == "cdi_variable"):
                return None  # Don't create CTE for CDI calculations
            
            # Create safe CTE name by removing spaces and special characters
            safe_cte_name = request.alias.replace(' ', '_').replace('-', '_').replace('.', '_')
            
            # Quote the result alias if it contains spaces or special characters
            quoted_alias = f'"{request.alias}"' if ' ' in request.alias or any(c in request.alias for c in ['-', '.', '/', '\\']) else request.alias
            
            # CLEAN APPROACH: Never modify the original SQL - wrap it and filter the results
            raw_sql = calc.raw_sql.strip()
            
            # Build filter conditions for the wrapper
            filter_conditions = self._build_filter_conditions(filters)
            
            # FIXED: Determine what columns the system SQL should provide based on group level
            if calc.group_level.value == "deal":
                # Deal-level: expect dl_nbr and result column - NO tr_id expected
                return f"""{safe_cte_name}_cte AS (
    SELECT 
        raw_calc.dl_nbr,
        raw_calc.{calc.result_column_name} AS {quoted_alias}
    FROM (
        {self._indent_sql(raw_sql, 8)}
    ) AS raw_calc
    WHERE {filter_conditions['deal_filter']}
)"""
            else:  # TRANCHE level
                # Tranche-level: expect dl_nbr, tr_id, and result column
                return f"""{safe_cte_name}_cte AS (
    SELECT 
        raw_calc.dl_nbr,
        raw_calc.tr_id,
        raw_calc.{calc.result_column_name} AS {quoted_alias}
    FROM (
        {self._indent_sql(raw_sql, 8)}
    ) AS raw_calc
    WHERE {filter_conditions['tranche_filter']}
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
        """Build the final SELECT that joins all CTEs - FIXED to handle deal vs tranche level joins"""
        
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
        
        # Build joins and add calculation columns - SKIP CDI CALCULATIONS + FIXED JOIN LOGIC
        joins = []
        for request in calc_requests:
            if request.calc_type in ['user_calculation', 'system_calculation']:
                
                # SKIP CDI VARIABLE CALCULATIONS - they should be handled separately
                if request.calc_type == 'system_calculation' and request.calc_id:
                    calc = self.config_db.query(SystemCalculation).filter_by(id=request.calc_id, is_active=True).first()
                    if (calc and calc.metadata_config and 
                        calc.metadata_config.get("calculation_type") == "cdi_variable"):
                        continue  # Skip CDI calculations in the unified query
                
                # Create safe CTE name by removing spaces and special characters
                safe_cte_name = request.alias.replace(' ', '_').replace('-', '_').replace('.', '_')
                cte_alias = f"{safe_cte_name}_cte"
                
                # FIXED: Determine join condition based on CALCULATION level, not report scope
                if request.calc_type == 'system_calculation' and request.calc_id:
                    calc = self.config_db.query(SystemCalculation).filter_by(id=request.calc_id, is_active=True).first()
                    if calc and calc.group_level.value == "deal":
                        # Deal-level calculation: join only on dl_nbr
                        join_condition = f"base_data.dl_nbr = {cte_alias}.dl_nbr"
                    else:
                        # Tranche-level calculation: join on both dl_nbr and tr_id
                        join_condition = f"base_data.dl_nbr = {cte_alias}.dl_nbr AND base_data.tr_id = {cte_alias}.tr_id"
                elif request.calc_type == 'user_calculation' and request.calc_id:
                    calc = self.config_db.query(UserCalculation).filter_by(id=request.calc_id, is_active=True).first()
                    if calc and calc.group_level.value == "deal":
                        # Deal-level calculation: join only on dl_nbr
                        join_condition = f"base_data.dl_nbr = {cte_alias}.dl_nbr"
                    else:
                        # Tranche-level calculation: join on both dl_nbr and tr_id
                        join_condition = f"base_data.dl_nbr = {cte_alias}.dl_nbr AND base_data.tr_id = {cte_alias}.tr_id"
                else:
                    # Default to tranche-level join for safety
                    join_condition = f"base_data.dl_nbr = {cte_alias}.dl_nbr AND base_data.tr_id = {cte_alias}.tr_id"
                
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

    def _build_filter_conditions(self, filters: QueryFilters) -> Dict[str, str]:
        """Build filter conditions for wrapping system calculations - FIXED to not assume cycle_cde exists"""
        
        # Build deal-only filter (for deal-level calculations)
        deal_ids = list(filters.deal_tranche_map.keys())
        deal_filter = f"raw_calc.dl_nbr IN ({', '.join(map(str, deal_ids))})"
        
        # Build tranche-level filter (for tranche-level calculations)
        tranche_conditions = []
        for deal_id, tranche_ids in filters.deal_tranche_map.items():
            if tranche_ids:  # Specific tranches
                tranche_list = "', '".join(tranche_ids)
                tranche_conditions.append(f"(raw_calc.dl_nbr = {deal_id} AND raw_calc.tr_id IN ('{tranche_list}'))")
            else:  # All tranches for this deal
                tranche_conditions.append(f"raw_calc.dl_nbr = {deal_id}")
        
        tranche_filter = ' OR '.join(tranche_conditions) if tranche_conditions else "1=1"
        
        # FIXED: Don't assume cycle_cde exists in the system calculation result
        # Many system calculations (like the FNMA parser) don't include cycle_cde
        # The cycle filtering should be handled within the system calculation itself if needed
        
        return {
            'deal_filter': deal_filter,
            'tranche_filter': tranche_filter
        }

    def _inject_filters_into_raw_sql(self, raw_sql: str, filters: QueryFilters) -> str:
        """Inject filters into system SQL with ULTRA-CONSERVATIVE logic to prevent SQL corruption"""
        
        # ULTRA-CONSERVATIVE: Don't inject filters at all for most queries
        sql_upper = raw_sql.upper()
        
        # Skip filter injection for ANY complex query patterns
        if (sql_upper.startswith('WITH') or 
            'CASE WHEN' in sql_upper or 
            'UNION' in sql_upper or
            'SUBQUERY' in sql_upper or
            'INNER JOIN' in sql_upper or  # Skip any INNER JOINs
            'LEFT JOIN' in sql_upper or   # Skip any LEFT JOINs
            'RIGHT JOIN' in sql_upper or  # Skip any RIGHT JOINs
            'FULL JOIN' in sql_upper):    # Skip any FULL JOINs
            return raw_sql
        
        # Skip if query already has WHERE clause with ANY existing filters
        if " WHERE " in sql_upper:
            return raw_sql
        
        # ULTRA-CONSERVATIVE: Only inject for the most basic single-table queries
        # Skip any query with multiple tables or complex patterns
        if ('JOIN' in sql_upper or 
            'FROM' in sql_upper and sql_upper.count('FROM') > 1):
            return raw_sql
        
        # At this point, only very basic single-table queries should remain
        # For maximum safety, let's just return the original SQL without injection
        # This prevents any corruption but means system calculations need to handle their own filtering
        return raw_sql

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

    def resolve_single_calculation(self, calc_request: CalculationRequest, filters: QueryFilters) -> Dict[str, Any]:
        """Preview a single calculation by creating a minimal unified query with just that calculation"""
        try:
            # Build a minimal unified query with just this one calculation
            unified_sql = self._build_unified_query([calc_request], filters)
            
            # Determine what columns this calculation will return
            columns = ["dl_nbr", "cycle_cde"]
            if filters.report_scope == "TRANCHE":
                columns.append("tr_id")
            columns.append(calc_request.alias)
            
            # Determine calculation type for response
            calc_type = calc_request.calc_type
            
            # Determine group level based on calculation type
            group_level = None
            if calc_request.calc_type == "user_calculation" and calc_request.calc_id:
                user_calc = self.config_db.query(UserCalculation).filter_by(id=calc_request.calc_id, is_active=True).first()
                if user_calc:
                    group_level = user_calc.group_level.value
            elif calc_request.calc_type == "system_calculation" and calc_request.calc_id:
                system_calc = self.config_db.query(SystemCalculation).filter_by(id=calc_request.calc_id, is_active=True).first()
                if system_calc:
                    group_level = system_calc.group_level.value
            elif calc_request.calc_type == "static_field":
                # Determine group level based on field path
                if calc_request.field_path:
                    if calc_request.field_path.startswith("tranche.") or calc_request.field_path.startswith("tranchebal."):
                        group_level = "tranche"
                    else:
                        group_level = "deal"
            
            return {
                "sql": unified_sql,
                "columns": columns,
                "calculation_type": calc_type,
                "group_level": group_level,
                "alias": calc_request.alias
            }
            
        except Exception as e:
            return {
                "sql": f"-- ERROR: {str(e)}",
                "columns": [],
                "calculation_type": "error",
                "group_level": None,
                "alias": calc_request.alias,
                "error": str(e)
            }