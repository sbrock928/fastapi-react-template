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
            
            # SKIP CDI VARIABLE CALCULATIONS - they should be handled separately
            if (calc.metadata_config and 
                calc.metadata_config.get("calculation_type") == "cdi_variable"):
                return None  # Don't create CTE for CDI calculations
            
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
        
        # Build joins and add calculation columns - SKIP CDI CALCULATIONS
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
        """Inject filters into system SQL with improved logic for deal vs tranche level and table aliases"""
        
        # Check if the SQL contains tranchebal - if not, we can't use tranchebal filters
        sql_upper = raw_sql.upper()
        has_tranchebal = 'TRANCHEBAL' in sql_upper
        has_tranche = 'TRANCHE' in sql_upper and 'TRANCHE' != 'TRANCHEBAL'  # Avoid matching tranchebal
        
        # Detect table aliases by parsing FROM clauses
        import re
        
        # Find deal table alias (look for "FROM deal" or "FROM deal alias")
        deal_alias_match = re.search(r'\bFROM\s+deal\s+(\w+)\b', raw_sql, re.IGNORECASE)
        deal_ref = deal_alias_match.group(1) if deal_alias_match else 'deal'
        
        # Find tranche table alias if present
        tranche_alias_match = re.search(r'\bFROM\s+tranche\s+(\w+)\b|\bJOIN\s+tranche\s+(\w+)\b', raw_sql, re.IGNORECASE)
        tranche_ref = None
        if tranche_alias_match:
            tranche_ref = tranche_alias_match.group(1) or tranche_alias_match.group(2)
        elif has_tranche:
            tranche_ref = 'tranche'
        
        # Find tranchebal table alias if present
        tranchebal_alias_match = re.search(r'\bFROM\s+tranchebal\s+(\w+)\b|\bJOIN\s+tranchebal\s+(\w+)\b', raw_sql, re.IGNORECASE)
        tranchebal_ref = None
        if tranchebal_alias_match:
            tranchebal_ref = tranchebal_alias_match.group(1) or tranchebal_alias_match.group(2)
        elif has_tranchebal:
            tranchebal_ref = 'tranchebal'
        
        # Build filter parts based on what tables are available
        filter_parts = []
        
        # Only add cycle filter if tranchebal is in the query
        if has_tranchebal and tranchebal_ref:
            filter_parts.append(f"{tranchebal_ref}.cycle_cde = {filters.cycle_code}")
        
        # Build deal-tranche conditions based on available tables
        deal_conditions = []
        for deal_id, tranche_ids in filters.deal_tranche_map.items():
            if has_tranche and tranche_ids and tranche_ref:
                # We have tranche table and specific tranche filtering
                tranche_list = "', '".join(tranche_ids)
                deal_conditions.append(f"({deal_ref}.dl_nbr = {deal_id} AND {tranche_ref}.tr_id IN ('{tranche_list}'))")
            else:
                # Deal-only filtering (either no tranche table or no tranche filtering needed)
                deal_conditions.append(f"{deal_ref}.dl_nbr = {deal_id}")
        
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