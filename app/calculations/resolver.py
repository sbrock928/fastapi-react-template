# app/calculations/resolver.py
"""Enhanced unified calculation resolver with dynamic SQL parameter injection"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
import re

from .models import Calculation, CalculationType, AggregationFunction, get_static_field_info


@dataclass
class CalculationRequest:
    """Represents a single calculation to resolve"""
    calc_id: int
    alias: Optional[str] = None

    def __post_init__(self):
        if not self.alias:
            self.alias = f"calc_{self.calc_id}"


@dataclass
class QueryFilters:
    """Standard filters applied to all calculations with enhanced parameter support"""
    deal_tranche_map: Dict[int, List[str]]  # deal_id -> [tranche_ids] or [] for all
    cycle_code: int
    report_scope: Optional[str] = None  # "DEAL" or "TRANCHE" - determines output grouping


class DynamicParameterInjector:
    """Handles dynamic parameter injection for SQL placeholders"""
    
    def __init__(self, filters: QueryFilters):
        self.filters = filters
    
    def get_parameter_values(self) -> Dict[str, Any]:
        """Generate all available parameter values"""
        deal_numbers = list(self.filters.deal_tranche_map.keys())
        
        # Build deal filter clause with table qualification
        deal_filter = f"deal.dl_nbr IN ({', '.join(map(str, deal_numbers))})"
        
        # Build tranche filter clause with table qualification
        tranche_conditions = []
        for deal_id, tranche_ids in self.filters.deal_tranche_map.items():
            if tranche_ids:  # Specific tranches
                tranche_list = "', '".join(tranche_ids)
                tranche_conditions.append(f"(deal.dl_nbr = {deal_id} AND tranche.tr_id IN ('{tranche_list}'))")
            else:  # All tranches for this deal
                tranche_conditions.append(f"deal.dl_nbr = {deal_id}")
        
        tranche_filter = ' OR '.join(tranche_conditions) if tranche_conditions else "1=1"
        
        # Build combined deal-tranche filter with proper table qualification
        deal_tranche_filter = f"({tranche_filter})"
        
        # Build tranche IDs list
        all_tranche_ids = []
        for tranche_ids in self.filters.deal_tranche_map.values():
            all_tranche_ids.extend(tranche_ids)
        tranche_ids_quoted = "', '".join(all_tranche_ids) if all_tranche_ids else ""
        
        return {
            "current_cycle": self.filters.cycle_code,
            "previous_cycle": self.filters.cycle_code - 1,
            "cycle_minus_2": self.filters.cycle_code - 2,
            "deal_filter": deal_filter,
            "tranche_filter": tranche_filter,
            "deal_tranche_filter": deal_tranche_filter,
            "deal_numbers": ', '.join(map(str, deal_numbers)),
            "tranche_ids": tranche_ids_quoted,
        }
    
    def inject_parameters(self, sql: str, calculation: Calculation) -> str:
        """Inject parameter values into SQL placeholders"""
        if not sql:
            return sql
        
        parameter_values = self.get_parameter_values()
        used_placeholders = calculation.get_used_placeholders()
        
        # Replace each placeholder with its value
        injected_sql = sql
        for placeholder in used_placeholders:
            if placeholder in parameter_values:
                placeholder_pattern = f"{{{placeholder}}}"
                value = parameter_values[placeholder]
                injected_sql = injected_sql.replace(placeholder_pattern, str(value))
        
        return injected_sql


class EnhancedCalculationResolver:
    """Enhanced calculation resolver with dynamic parameter injection support"""

    def __init__(self, dw_db: Session, config_db: Session):
        self.dw_db = dw_db
        self.config_db = config_db
        self.parameter_injector = None

    def resolve_report(self, calc_requests: List[CalculationRequest], filters: QueryFilters) -> Dict[str, Any]:
        """Generate a unified SQL query with parameter injection for all calculations"""
        
        self.parameter_injector = DynamicParameterInjector(filters)
        
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
                    'parameter_injections': self._get_parameter_injection_info(calc_requests),
                    'query_type': 'unified_with_parameters',
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
                    'query_type': 'unified_with_parameters',
                    'execution_error': True,
                    'error_message': str(e)
                }
            }

    def _build_unified_query(self, calc_requests: List[CalculationRequest], filters: QueryFilters) -> str:
        """Build a unified SQL query with parameter injection for all calculations"""
        
        # Load calculations from database
        calculations = {}
        for request in calc_requests:
            calc = self.config_db.query(Calculation).filter_by(id=request.calc_id, is_active=True).first()
            if calc:
                calculations[request.calc_id] = calc
        
        # Separate calculations by type
        user_agg_calcs = []
        system_field_calcs = []
        system_sql_calcs = []
        cdi_variable_calcs = []
        
        for request in calc_requests:
            # FIXED: Handle special static field requests
            if isinstance(request.calc_id, str) and request.calc_id.startswith("static_field:"):
                # Extract field path from the special format
                field_path = request.calc_id.replace("static_field:", "")
                
                # Create a pseudo-calculation for static fields with proper method
                class PseudoCalculation:
                    def __init__(self, field_path, resolver):
                        self.calculation_type = CalculationType.SYSTEM_FIELD
                        self.metadata_config = {'field_path': field_path}
                        self.source_model = None
                        self.source_field = field_path.split('.')[-1] if '.' in field_path else field_path
                        self.field_path = field_path
                        self.resolver = resolver
                    
                    def get_required_models(self):
                        return self.resolver._get_required_models_for_field_path(self.field_path)
                
                pseudo_calc = PseudoCalculation(field_path, self)
                
                system_field_calcs.append((request, pseudo_calc))
                print(f"DEBUG: Added static field calculation: {field_path} with alias: {request.alias}")
                continue
            
            calc = calculations.get(request.calc_id)
            if not calc:
                print(f"DEBUG: No calculation found for ID: {request.calc_id}")
                continue
                
            if calc.calculation_type == CalculationType.USER_AGGREGATION:
                user_agg_calcs.append((request, calc))
            elif calc.calculation_type == CalculationType.SYSTEM_FIELD:
                system_field_calcs.append((request, calc))
            elif calc.calculation_type == CalculationType.SYSTEM_SQL:
                system_sql_calcs.append((request, calc))
            elif calc.calculation_type == CalculationType.CDI_VARIABLE:
                cdi_variable_calcs.append((request, calc))
        
        print(f"DEBUG: Calculation separation:")
        print(f"  User aggregation: {len(user_agg_calcs)}")
        print(f"  System fields: {len(system_field_calcs)}")
        print(f"  System SQL: {len(system_sql_calcs)}")
        print(f"  CDI variables: {len(cdi_variable_calcs)}")
        
        # Build CTEs for calculations that need them
        ctes = []
        
        # Add user aggregation CTEs
        for request, calc in user_agg_calcs:
            cte = self._build_user_aggregation_cte(request, calc, filters)
            if cte:
                ctes.append(cte)
        
        # Add system SQL CTEs with parameter injection
        for request, calc in system_sql_calcs:
            cte = self._build_system_sql_cte(request, calc, filters)
            if cte:
                ctes.append(cte)
        
        # Add CDI variable CTEs (these are special system SQL with CDI logic)
        for request, calc in cdi_variable_calcs:
            cte = self._build_cdi_variable_cte(request, calc, filters)
            if cte:
                ctes.append(cte)
        
        # Build base query with system fields
        base_query = self._build_base_query(system_field_calcs, filters, calc_requests)
        
        # Combine everything
        if ctes:
            # Add base_data CTE to the list
            base_cte = f"base_data AS (\n{self._indent_sql(base_query, 4)}\n)"
            ctes.append(base_cte)
            
            # Build the final SELECT that joins everything
            final_select = self._build_final_select(calc_requests, calculations, filters)
            
            # Combine: WITH all_ctes final_select
            return "WITH " + ",\n\n".join(ctes) + "\n\n" + final_select
        else:
            # No CTEs needed, just return the base query
            return base_query

    def _build_user_aggregation_cte(self, request: CalculationRequest, calc: Calculation, filters: QueryFilters) -> Optional[str]:
        """Build CTE for a user aggregation calculation"""
        try:
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
            
            # Create safe CTE name
            safe_cte_name = request.alias.replace(' ', '_').replace('-', '_').replace('.', '_')
            quoted_alias = f'"{request.alias}"' if ' ' in request.alias or any(c in request.alias for c in ['-', '.', '/', '\\']) else request.alias
            
            # Build GROUP BY and SELECT based on calculation level
            if calc.group_level.value == "deal":
                group_columns = ["deal.dl_nbr"]
                select_columns = ["deal.dl_nbr", f"{agg_expr} AS {quoted_alias}"]
            else:  # TRANCHE level
                group_columns = ["deal.dl_nbr", "tranche.tr_id"]
                select_columns = ["deal.dl_nbr", "tranche.tr_id", f"{agg_expr} AS {quoted_alias}"]
            
            # Build the CTE with dynamic filter injection
            where_clause = self._build_dynamic_where_clause(filters)
            
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

    def _build_system_sql_cte(self, request: CalculationRequest, calc: Calculation, filters: QueryFilters) -> Optional[str]:
        """Build CTE for a system SQL calculation with parameter injection"""
        try:
            # Create safe CTE name
            safe_cte_name = request.alias.replace(' ', '_').replace('-', '_').replace('.', '_')
            quoted_alias = f'"{request.alias}"' if ' ' in request.alias or any(c in request.alias for c in ['-', '.', '/', '\\']) else request.alias
            
            # Inject parameters into the raw SQL
            injected_sql = self.parameter_injector.inject_parameters(calc.raw_sql, calc)
            
            # Determine expected columns based on group level
            if calc.group_level.value == "deal":
                return f"""{safe_cte_name}_cte AS (
    SELECT 
        calc_result.dl_nbr,
        calc_result.{calc.result_column_name} AS {quoted_alias}
    FROM (
        {self._indent_sql(injected_sql, 8)}
    ) AS calc_result
)"""
            else:  # TRANCHE level
                return f"""{safe_cte_name}_cte AS (
    SELECT 
        calc_result.dl_nbr,
        calc_result.tr_id,
        calc_result.{calc.result_column_name} AS {quoted_alias}
    FROM (
        {self._indent_sql(injected_sql, 8)}
    ) AS calc_result
)"""
        
        except Exception as e:
            # Return a comment CTE for debugging
            safe_cte_name = request.alias.replace(' ', '_').replace('-', '_').replace('.', '_')
            return f"""{safe_cte_name}_cte AS (
    -- ERROR: {str(e)}
    SELECT NULL AS dl_nbr, NULL AS "{request.alias}"
    WHERE FALSE
)"""

    def _build_cdi_variable_cte(self, request: CalculationRequest, calc: Calculation, filters: QueryFilters) -> Optional[str]:
        """Build CTE for a CDI variable calculation (special case of system SQL)"""
        # CDI variables use the same logic as system SQL but with CDI-specific metadata
        return self._build_system_sql_cte(request, calc, filters)

    def _build_base_query(self, system_field_calcs: List[tuple], filters: QueryFilters, all_requests: List[CalculationRequest]) -> str:
        """Build the base query with system fields and proper joins"""
        
        # Determine required models
        required_models = set(['Deal'])  # Always need Deal
        
        for request, calc in system_field_calcs:
            required_models.update(calc.get_required_models())
        
        # Check if any calculations need tranche-level data
        if filters.report_scope == "TRANCHE":
            required_models.add('Tranche')
            required_models.add('TrancheBal')
        
        # Build base columns
        base_columns = ["deal.dl_nbr"]
        
        # Add tranche info if needed
        if 'Tranche' in required_models or 'TrancheBal' in required_models:
            base_columns.append("tranche.tr_id")
        
        # Add cycle code if needed  
        if 'TrancheBal' in required_models:
            base_columns.append("tranchebal.cycle_cde")
        
        # Add all system field columns - FIXED: Better field path extraction
        for request, calc in system_field_calcs:
            field_path = ""
            
            # Try to get field_path from metadata_config first
            if calc.metadata_config and 'field_path' in calc.metadata_config:
                field_path = calc.metadata_config['field_path']
            # Fallback: construct from source_model and source_field if available
            elif calc.source_model and calc.source_field:
                field_path = f"{calc.source_model.value.lower()}.{calc.source_field}"
            
            if field_path:
                quoted_alias = f'"{request.alias}"' if ' ' in request.alias else request.alias
                base_columns.append(f"{field_path} AS {quoted_alias}")
                print(f"DEBUG: Adding static field {field_path} AS {quoted_alias}")  # Debug logging
            else:
                print(f"DEBUG: No field_path found for calculation {calc.name} (ID: {calc.id})")  # Debug logging
        
        # Debug logging
        print(f"DEBUG: system_field_calcs count: {len(system_field_calcs)}")
        print(f"DEBUG: base_columns: {base_columns}")
        
        # Build FROM clause
        from_clause = self._build_from_clause(list(required_models))
        
        # Build WHERE clause with parameter injection
        where_clause = self._build_dynamic_where_clause(filters, required_models)
        
        return f"""SELECT DISTINCT {', '.join(base_columns)}
{from_clause}
{where_clause}"""

    def _get_required_models_for_field_path(self, field_path: str) -> List[str]:
        """Helper method to determine required models for a field path"""
        if field_path.startswith('deal.'):
            return ['Deal']
        elif field_path.startswith('tranche.'):
            return ['Deal', 'Tranche']
        elif field_path.startswith('tranchebal.'):
            return ['Deal', 'Tranche', 'TrancheBal']
        else:
            # Default to Deal for unknown paths
            return ['Deal']

    def _build_final_select(self, calc_requests: List[CalculationRequest], calculations: Dict[int, Calculation], filters: QueryFilters) -> str:
        """Build the final SELECT that joins all CTEs"""
        
        # Build select columns
        select_columns = []
        
        # Add base columns
        if filters.report_scope == "TRANCHE":
            select_columns.extend(["base_data.dl_nbr", "base_data.tr_id", "base_data.cycle_cde"])
        else:
            select_columns.extend(["base_data.dl_nbr", "base_data.cycle_cde"])
        
        # Build joins and add calculation columns
        joins = []
        for request in calc_requests:
            # FIXED: Handle static field requests
            if isinstance(request.calc_id, str) and request.calc_id.startswith("static_field:"):
                # Static fields are in base_data
                quoted_alias = f'"{request.alias}"' if ' ' in request.alias else request.alias
                select_columns.append(f"base_data.{quoted_alias}")
                print(f"DEBUG: Adding static field column to final SELECT: base_data.{quoted_alias}")
                continue
            
            calc = calculations.get(request.calc_id)
            if not calc:
                print(f"DEBUG: No calculation found for final SELECT: {request.calc_id}")
                continue
                
            if calc.calculation_type == CalculationType.SYSTEM_FIELD:
                # System fields are in base_data
                quoted_alias = f'"{request.alias}"' if ' ' in request.alias else request.alias
                select_columns.append(f"base_data.{quoted_alias}")
                print(f"DEBUG: Adding system field column to final SELECT: base_data.{quoted_alias}")
            else:
                # Other calculations are in CTEs
                safe_cte_name = request.alias.replace(' ', '_').replace('-', '_').replace('.', '_')
                cte_alias = f"{safe_cte_name}_cte"
                
                # Determine join condition based on calculation level
                if calc.group_level.value == "deal":
                    join_condition = f"base_data.dl_nbr = {cte_alias}.dl_nbr"
                else:
                    join_condition = f"base_data.dl_nbr = {cte_alias}.dl_nbr AND base_data.tr_id = {cte_alias}.tr_id"
                
                joins.append(f"LEFT JOIN {cte_alias} ON {join_condition}")
                
                quoted_alias = f'"{request.alias}"' if ' ' in request.alias else request.alias
                select_columns.append(f"{cte_alias}.{quoted_alias}")
                print(f"DEBUG: Adding CTE column to final SELECT: {cte_alias}.{quoted_alias}")
        
        print(f"DEBUG: Final SELECT columns: {select_columns}")
        
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

    def _build_dynamic_where_clause(self, filters: QueryFilters, required_models: Optional[Set[str]] = None) -> str:
        """Build WHERE clause with dynamic parameter injection"""
        conditions = []
        
        # Build deal-tranche conditions using parameter injector
        parameter_values = self.parameter_injector.get_parameter_values()
        
        # Add cycle filter if TrancheBal is involved
        if not required_models or "TrancheBal" in required_models:
            conditions.append(f"tranchebal.cycle_cde = {parameter_values['current_cycle']}")
        
        # Add deal-tranche filter - this is already table-qualified in parameter_values
        conditions.append(parameter_values['deal_tranche_filter'])
        
        return f"WHERE {' AND '.join(conditions)}" if conditions else ""

    def _get_parameter_injection_info(self, calc_requests: List[CalculationRequest]) -> Dict[str, Any]:
        """Get debug information about parameter injections"""
        calculations = {}
        for request in calc_requests:
            calc = self.config_db.query(Calculation).filter_by(id=request.calc_id, is_active=True).first()
            if calc:
                calculations[request.calc_id] = calc
        
        injection_info = {
            'parameter_values': self.parameter_injector.get_parameter_values(),
            'calculations_with_placeholders': []
        }
        
        for request in calc_requests:
            calc = calculations.get(request.calc_id)
            if calc and calc.raw_sql:
                used_placeholders = calc.get_used_placeholders()
                if used_placeholders:
                    injection_info['calculations_with_placeholders'].append({
                        'calc_id': calc.id,
                        'calc_name': calc.name,
                        'placeholders_used': list(used_placeholders)
                    })
        
        return injection_info

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
        """Preview a single calculation with parameter injection"""
        try:
            calc = self.config_db.query(Calculation).filter_by(id=calc_request.calc_id, is_active=True).first()
            if not calc:
                return {"error": "Calculation not found"}
            
            # Set up parameter injector
            self.parameter_injector = DynamicParameterInjector(filters)
            
            # Build a minimal unified query with just this one calculation
            unified_sql = self._build_unified_query([calc_request], filters)
            
            # Get parameter injection info
            parameter_info = self._get_parameter_injection_info([calc_request])
            
            return {
                "sql": unified_sql,
                "calculation_type": calc.calculation_type.value,
                "group_level": calc.group_level.value,
                "alias": calc_request.alias,
                "parameter_injections": parameter_info,
                "placeholders_used": list(calc.get_used_placeholders()) if calc.raw_sql else []
            }
            
        except Exception as e:
            return {
                "sql": f"-- ERROR: {str(e)}",
                "calculation_type": "error",
                "group_level": None,
                "alias": calc_request.alias,
                "error": str(e)
            }