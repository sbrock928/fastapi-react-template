# app/calculations/resolver.py
"""Enhanced unified calculation resolver with dynamic SQL parameter injection"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
import re

from .models import Calculation, CalculationType, AggregationFunction


@dataclass
class CalculationRequest:
    """Represents a single calculation to resolve"""
    calc_id: Any  # FIXED: Changed from int to Any to support string calc_ids
    alias: Optional[str] = None

    def __post_init__(self):
        if not self.alias:
            # Handle both int and string calc_ids
            if isinstance(self.calc_id, int):
                self.alias = f"calc_{self.calc_id}"
            else:
                self.alias = str(self.calc_id)


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
        
        # Separate different types of requests
        static_field_requests = []
        regular_calc_requests = []
        user_calc_string_requests = []
        system_calc_string_requests = []
        
        for request in calc_requests:
            if isinstance(request.calc_id, str):
                if request.calc_id.startswith("static_field:"):
                    static_field_requests.append(request)
                elif request.calc_id.startswith("user."):
                    user_calc_string_requests.append(request)
                elif request.calc_id.startswith("system."):
                    system_calc_string_requests.append(request)
                else:
                    regular_calc_requests.append(request)
            else:
                regular_calc_requests.append(request)
        
        # Load calculations from database for regular requests
        calculations = {}
        for request in regular_calc_requests:
            calc = self.config_db.query(Calculation).filter_by(id=request.calc_id, is_active=True).first()
            if calc:
                calculations[request.calc_id] = calc
        
        # FIXED: Handle user calculation string references more robustly
        # Map string identifiers like "user.tr_pass_thru_rte" to actual calculation records
        for request in user_calc_string_requests:
            source_field = request.calc_id.replace("user.", "")  # Extract the source field
            print(f"DEBUG: Looking for user calculation with source_field: {source_field}")
            
            # Find user calculation by source_field (more robust approach)
            calc = self.config_db.query(Calculation).filter(
                Calculation.calculation_type == CalculationType.USER_AGGREGATION,
                Calculation.source_field == source_field,
                Calculation.is_active == True
            ).first()
            
            if calc:
                calculations[request.calc_id] = calc
                regular_calc_requests.append(request)
                print(f"DEBUG: Mapped {request.calc_id} to calculation ID {calc.id}: {calc.name}")
            else:
                # Try fallback mapping by known patterns
                name_mapping = {
                    "tr_pass_thru_rte": "Average Pass Through Rate",
                    "tr_end_bal_amt": "Total Ending Balance",
                    "tr_int_dstrb_amt": "Interest Distribution"
                }
                
                if source_field in name_mapping:
                    calc = self.config_db.query(Calculation).filter(
                        Calculation.name == name_mapping[source_field],
                        Calculation.is_active == True
                    ).first()
                    
                    if calc:
                        calculations[request.calc_id] = calc
                        regular_calc_requests.append(request)
                        print(f"DEBUG: Mapped {request.calc_id} to calculation by name: {calc.name}")
                
                if not calc:
                    print(f"WARNING: No user calculation found for {request.calc_id} (source_field: {source_field})")

        # FIXED: Handle system calculation string references
        for request in system_calc_string_requests:
            result_column = request.calc_id.replace("system.", "")  # Extract the result column
            print(f"DEBUG: Looking for system calculation with result_column: {result_column}")
            
            # Find system calculation by result_column_name
            calc = self.config_db.query(Calculation).filter(
                Calculation.calculation_type == CalculationType.SYSTEM_SQL,
                Calculation.result_column_name == result_column,
                Calculation.is_active == True
            ).first()
            
            if calc:
                calculations[request.calc_id] = calc
                regular_calc_requests.append(request)
                print(f"DEBUG: Mapped {request.calc_id} to calculation ID {calc.id}: {calc.name}")
            else:
                # Try fallback mapping by known patterns
                name_mapping = {
                    "issuer_type": "Issuer Type Classification",
                    "investment_income": "Investment Income",
                    "deal_status": "Deal Status"
                }
                
                if result_column in name_mapping:
                    calc = self.config_db.query(Calculation).filter(
                        Calculation.name == name_mapping[result_column],
                        Calculation.is_active == True
                    ).first()
                    
                    if calc:
                        calculations[request.calc_id] = calc
                        regular_calc_requests.append(request)
                        print(f"DEBUG: Mapped {request.calc_id} to calculation by name: {calc.name}")
                
                if not calc:
                    print(f"WARNING: No system calculation found for {request.calc_id} (result_column: {result_column})")

        # Group calculations by type for batch processing
        user_aggregation_calcs = []
        system_field_calcs = []
        system_sql_calcs = []

        for request in regular_calc_requests:
            calc = calculations.get(request.calc_id)
            if not calc:
                print(f"Warning: Calculation {request.calc_id} not found, skipping")
                continue

            if calc.calculation_type == CalculationType.USER_AGGREGATION:
                user_aggregation_calcs.append((request, calc))
            elif calc.calculation_type == CalculationType.SYSTEM_FIELD:
                system_field_calcs.append((request, calc))
            elif calc.calculation_type == CalculationType.SYSTEM_SQL:
                system_sql_calcs.append((request, calc))

        print(f"  User aggregations: {len(user_aggregation_calcs)}")
        print(f"  System fields: {len(system_field_calcs)}")
        print(f"  System SQL: {len(system_sql_calcs)}")
        print(f"  Static fields: {len(static_field_requests)}")

        # FIXED: Completely restructure CTE handling to avoid nesting
        ctes = []
        created_cte_names = set()
        system_sql_with_ctes = []  # Track system SQL that needs special handling

        # First pass: Handle system SQL calculations
        for request, calc in system_sql_calcs:
            injected_sql = self.parameter_injector.inject_parameters(calc.raw_sql, calc)
            sql_trimmed = injected_sql.strip()
            has_existing_ctes = sql_trimmed.upper().startswith('WITH ')
            
            if has_existing_ctes:
                # For SQL with CTEs, we need to merge their CTEs with our main query
                print(f"DEBUG: System SQL calculation '{calc.name}' contains CTEs. Will merge CTEs.")
                system_sql_with_ctes.append((request, calc, injected_sql))
            else:
                # Regular system SQL without CTEs
                cte = self._build_system_sql_cte(request, calc, filters)
                if cte:
                    cte_name = request.alias.replace(' ', '_').replace('-', '_').replace('.', '_') + "_cte"
                    if cte_name not in created_cte_names:
                        ctes.append(cte)
                        created_cte_names.add(cte_name)
                        print(f"DEBUG: Added regular system SQL CTE: {cte_name}")

        # Handle system SQL with CTEs by extracting and merging their CTEs
        for request, calc, injected_sql in system_sql_with_ctes:
            extracted_ctes, final_select = self._extract_and_merge_ctes(injected_sql, request, calc)
            
            # Add the extracted CTEs to our main CTE list
            for cte_name, cte_def in extracted_ctes.items():
                if cte_name not in created_cte_names:
                    ctes.append(cte_def)
                    created_cte_names.add(cte_name)
                    print(f"DEBUG: Added extracted CTE: {cte_name}")
            
            # Create a wrapper CTE for the final calculation result
            safe_cte_name = request.alias.replace(' ', '_').replace('-', '_').replace('.', '_')
            quoted_alias = f'"{request.alias}"' if ' ' in request.alias or any(c in request.alias for c in ['-', '.', '/', '\\']) else request.alias
            
            if calc.group_level.value == "deal":
                wrapper_cte = f"""{safe_cte_name}_cte AS (
    SELECT 
        dl_nbr,
        {calc.result_column_name} AS {quoted_alias}
    FROM (
        {self._indent_sql(final_select, 8)}
    ) AS calc_result
)"""
            else:  # TRANCHE level
                wrapper_cte = f"""{safe_cte_name}_cte AS (
    SELECT 
        dl_nbr,
        tr_id,
        {calc.result_column_name} AS {quoted_alias}
    FROM (
        {self._indent_sql(final_select, 8)}
    ) AS calc_result
)"""
            
            cte_name = safe_cte_name + "_cte"
            if cte_name not in created_cte_names:
                ctes.append(wrapper_cte)
                created_cte_names.add(cte_name)
                print(f"DEBUG: Added wrapper CTE for complex SQL: {cte_name}")

        # Add user aggregation CTEs
        for request, calc in user_aggregation_calcs:
            cte = self._build_user_aggregation_cte(request, calc, filters)
            if cte:
                # Extract CTE name to check for duplicates
                cte_name = request.alias.replace(' ', '_').replace('-', '_').replace('.', '_') + "_cte"
                if cte_name not in created_cte_names:
                    ctes.append(cte)
                    created_cte_names.add(cte_name)
                    print(f"DEBUG: Added user aggregation CTE: {cte_name}")
                else:
                    print(f"DEBUG: Skipped duplicate user aggregation CTE: {cte_name}")
        
        # Build base query with system fields and static fields
        base_query = self._build_base_query(system_field_calcs, static_field_requests, filters, calc_requests)
        
        # Combine: WITH all_ctes final_select
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

    def _extract_and_merge_ctes(self, sql_with_ctes: str, request: CalculationRequest, calc: Calculation) -> tuple:
        """Extract CTEs from user SQL and return them separately from the final SELECT"""
        try:
            # Parse the SQL to extract CTEs and the final SELECT
            sql_trimmed = sql_with_ctes.strip()
            
            # Find the WITH keyword and the start of CTEs
            with_pattern = r'WITH\s+'
            with_match = re.search(with_pattern, sql_trimmed, re.IGNORECASE)
            if not with_match:
                return {}, sql_trimmed
            
            # Find the final SELECT statement (the one not inside parentheses)
            # We need to find the last SELECT that's not inside a CTE
            select_positions = []
            paren_depth = 0
            in_quotes = False
            quote_char = ''
            
            for i, char in enumerate(sql_trimmed):
                if char in ('"', "'") and (i == 0 or sql_trimmed[i-1] != '\\'):
                    if not in_quotes:
                        in_quotes = True
                        quote_char = char
                    elif char == quote_char:
                        in_quotes = False
                        quote_char = ''
                
                if not in_quotes:
                    if char == '(':
                        paren_depth += 1
                    elif char == ')':
                        paren_depth -= 1
                    elif paren_depth == 0 and sql_trimmed[i:i+6].upper() == 'SELECT':
                        select_positions.append(i)
            
            if not select_positions:
                raise ValueError("Could not find final SELECT statement")
            
            # The final SELECT is the last one at depth 0
            final_select_start = select_positions[-1]
            final_select = sql_trimmed[final_select_start:].strip()
            
            # FIXED: Remove ORDER BY clause from final SELECT since it will be used in a CTE
            # SQL Server doesn't allow ORDER BY in CTEs unless TOP, OFFSET, or FOR XML is used
            final_select = self._remove_order_by_from_select(final_select)
            
            # Extract the CTE section (everything between WITH and the final SELECT)
            cte_section = sql_trimmed[with_match.end():final_select_start].strip()
            
            # Parse individual CTEs using improved regex
            extracted_ctes = {}
            
            # Find all CTE definitions - improved pattern
            # This pattern looks for: word AS ( ... balanced parentheses ... )
            cte_pattern = r'(\w+)\s+AS\s*\('
            cte_matches = list(re.finditer(cte_pattern, cte_section, re.IGNORECASE))
            
            for i, match in enumerate(cte_matches):
                cte_name = match.group(1)
                cte_start_pos = match.end()  # Position after the opening parenthesis
                
                # Find the matching closing parenthesis
                paren_count = 1
                cte_end_pos = len(cte_section)
                in_quotes = False
                quote_char = ''
                
                for j in range(cte_start_pos, len(cte_section)):
                    char = cte_section[j]
                    
                    # Handle quotes
                    if char in ('"', "'") and (j == 0 or cte_section[j-1] != '\\'):
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
                            if paren_count == 0:
                                cte_end_pos = j
                                break
                
                # Extract the CTE body (without the outer parentheses)
                cte_body = cte_section[cte_start_pos:cte_end_pos].strip()
                
                # Skip empty CTEs
                if not cte_body:
                    print(f"WARNING: Skipping empty CTE: {cte_name}")
                    continue
                
                # Create a unique CTE name to avoid conflicts
                unique_cte_name = f"{request.alias}_{cte_name}".replace(' ', '_').replace('-', '_').replace('.', '_')
                cte_definition = f"{unique_cte_name} AS (\n{self._indent_sql(cte_body, 4)}\n)"
                
                extracted_ctes[unique_cte_name] = cte_definition
                
                # Replace references to this CTE in the final SELECT
                # Use word boundaries to avoid partial matches
                final_select = re.sub(rf'\b{re.escape(cte_name)}\b', unique_cte_name, final_select, flags=re.IGNORECASE)
            
            return extracted_ctes, final_select
            
        except Exception as e:
            print(f"ERROR: Failed to extract CTEs from SQL: {str(e)}")
            print(f"SQL that failed: {sql_with_ctes[:500]}...")  # Show first 500 chars for debugging
            # Fallback: return empty CTEs and original SQL
            return {}, sql_with_ctes

    def _remove_order_by_from_select(self, sql: str) -> str:
        """Remove ORDER BY clause from a SELECT statement since it's invalid in CTEs"""
        try:
            # Find the ORDER BY clause at the end of the SELECT statement
            # We need to be careful not to remove ORDER BY from subqueries
            
            # Work backwards from the end to find the outermost ORDER BY
            sql_upper = sql.upper()
            order_by_pos = sql_upper.rfind('ORDER BY')
            
            if order_by_pos == -1:
                return sql  # No ORDER BY found
            
            # Check if this ORDER BY is at the outer level (not inside parentheses)
            paren_count = 0
            in_quotes = False
            quote_char = ''
            
            for i in range(order_by_pos + len('ORDER BY'), len(sql)):
                char = sql[i]
                
                # Handle quotes
                if char in ('"', "'") and (i == 0 or sql[i-1] != '\\'):
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
                        if paren_count < 0:
                            # We've gone outside the current scope, ORDER BY is at outer level
                            break
            
            # If we're at the outer level, remove the ORDER BY clause
            if paren_count >= 0:
                result = sql[:order_by_pos].rstrip()
                print(f"DEBUG: Removed ORDER BY clause from SELECT statement for CTE compatibility")
                return result
            
            return sql
            
        except Exception as e:
            print(f"WARNING: Failed to remove ORDER BY clause: {str(e)}")
            return sql

    def _build_user_aggregation_cte(self, request: CalculationRequest, calc: Calculation, filters: QueryFilters) -> Optional[str]:
        """Build CTE for a user aggregation calculation"""
        try:
            print(f"DEBUG: Building user aggregation CTE for {request.alias} (calc_id: {request.calc_id})")
            print(f"DEBUG: Calculation details - Name: {calc.name}, Type: {calc.calculation_type}, Source: {calc.source_model}, Field: {calc.source_field}")
            
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
                    print(f"ERROR: Weighted average calculation {calc.name} missing weight_field")
                    return None
                weight_field = f"{calc.source_model.value.lower()}.{calc.weight_field}"
                agg_expr = f"SUM({agg_field} * {weight_field}) / NULLIF(SUM({weight_field}), 0)"
            else:
                print(f"ERROR: Unknown aggregation function: {calc.aggregation_function}")
                return None
            
            print(f"DEBUG: Aggregation expression: {agg_expr}")
            
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
            
            # Log the parameter values being used
            parameter_values = self.parameter_injector.get_parameter_values()
            print(f"DEBUG: Filter parameters for {request.alias}:")
            print(f"  - cycle_code: {parameter_values['current_cycle']}")
            print(f"  - deal_tranche_filter: {parameter_values['deal_tranche_filter']}")
            
            cte_sql = f"""{safe_cte_name}_cte AS (
    SELECT {', '.join(select_columns)}
    FROM deal
    JOIN tranche ON deal.dl_nbr = tranche.dl_nbr
    JOIN tranchebal ON tranche.dl_nbr = tranchebal.dl_nbr AND tranche.tr_id = tranchebal.tr_id
    {where_clause}
    GROUP BY {', '.join(group_columns)}
)"""
            
            print(f"DEBUG: Generated CTE for {request.alias}:")
            print(cte_sql)
            
            return cte_sql
        
        except Exception as e:
            # Return a comment CTE for debugging
            safe_cte_name = request.alias.replace(' ', '_').replace('-', '_').replace('.', '_')
            error_cte = f"""{safe_cte_name}_cte AS (
    -- ERROR: {str(e)}
    -- Calculation: {calc.name if calc else 'Unknown'}
    -- Source: {calc.source_model.value if calc and calc.source_model else 'Unknown'}.{calc.source_field if calc else 'Unknown'}
    -- Function: {calc.aggregation_function.value if calc and calc.aggregation_function else 'Unknown'}
    SELECT NULL AS dl_nbr, NULL AS "{request.alias}"
    WHERE FALSE
)"""
            print(f"ERROR: Failed to build user aggregation CTE for {request.alias}: {str(e)}")
            return error_cte

    def _build_system_sql_cte(self, request: CalculationRequest, calc: Calculation, filters: QueryFilters) -> Optional[str]:
        """Build CTE for a system SQL calculation with parameter injection"""
        try:
            # Create safe CTE name
            safe_cte_name = request.alias.replace(' ', '_').replace('-', '_').replace('.', '_')
            quoted_alias = f'"{request.alias}"' if ' ' in request.alias or any(c in request.alias for c in ['-', '.', '/', '\\']) else request.alias
            
            # Inject parameters into the raw SQL
            injected_sql = self.parameter_injector.inject_parameters(calc.raw_sql, calc)
            
            # FIXED: Check if the injected SQL already starts with WITH (has CTEs)
            # If so, we need to handle it differently to avoid nested CTEs
            sql_trimmed = injected_sql.strip()
            has_existing_ctes = sql_trimmed.upper().startswith('WITH ')
            
            # Determine expected columns based on group level
            if calc.group_level.value == "deal":
                if has_existing_ctes:
                    # For SQL that already has CTEs, we need to execute it separately
                    # and then join the results in a different way
                    print(f"DEBUG: System SQL calculation '{calc.name}' contains CTEs. Will handle as standalone query.")
                    
                    # Create a materialized view approach - execute the CTE query and make it available
                    materialized_cte = f"""{safe_cte_name}_cte AS (
    SELECT 
        dl_nbr,
        {calc.result_column_name} AS {quoted_alias}
    FROM (
        {self._indent_sql(injected_sql, 8)}
    ) AS materialized_result
)"""
                    
                    return materialized_cte
                else:
                    return f"""{safe_cte_name}_cte AS (
    SELECT 
        calc_result.dl_nbr,
        calc_result.{calc.result_column_name} AS {quoted_alias}
    FROM (
        {self._indent_sql(injected_sql, 8)}
    ) AS calc_result
)"""
            else:  # TRANCHE level
                if has_existing_ctes:
                    print(f"DEBUG: System SQL calculation '{calc.name}' contains CTEs. Will handle as standalone query.")
                    
                    # Create a materialized view approach - execute the CTE query and make it available
                    materialized_cte = f"""{safe_cte_name}_cte AS (
    SELECT 
        dl_nbr,
        tr_id,
        {calc.result_column_name} AS {quoted_alias}
    FROM (
        {self._indent_sql(injected_sql, 8)}
    ) AS materialized_result
)"""
                    
                    return materialized_cte
                else:
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

    def _build_base_query(self, system_field_calcs: List[tuple], static_field_requests: List[CalculationRequest], filters: QueryFilters, all_requests: List[CalculationRequest]) -> str:
        """Build the base query with system fields and proper joins"""
        
        # Determine required models - FIXED: Better logic for determining requirements
        required_models = set(['Deal'])  # Always need Deal
        
        # Check static field requests for required models
        for request in static_field_requests:
            field_path = request.calc_id.replace("static_field:", "")
            field_required_models = self._get_required_models_for_field_path(field_path)
            required_models.update(field_required_models)
        
        # Check system field calculations
        for request, calc in system_field_calcs:
            required_models.update(calc.get_required_models())
        
        # Check if any calculations need tranche-level data
        if filters.report_scope == "TRANCHE":
            required_models.add('Tranche')
            required_models.add('TrancheBal')
        
        # FIXED: Also check if any aggregation calculations require tranche-level data
        # We need to examine all_requests to see if any regular calculations need tranche data
        for request in all_requests:
            if not isinstance(request.calc_id, str) or not request.calc_id.startswith("static_field:"):
                # This is a regular calculation request
                calc = self.config_db.query(Calculation).filter_by(id=request.calc_id, is_active=True).first()
                if calc:
                    calc_models = calc.get_required_models()
                    required_models.update(calc_models)
                    # Also check if calculation is tranche-level
                    if calc.group_level and calc.group_level.value == "tranche":
                        required_models.add('Tranche')
                        required_models.add('TrancheBal')
        
        # Build base columns
        base_columns = ["deal.dl_nbr"]
        
        # FIXED: Only add tranche.tr_id if report scope is TRANCHE
        # For DEAL scope, we want to aggregate data to deal level, not show tranche details
        if filters.report_scope == "TRANCHE" and 'Tranche' in required_models:
            base_columns.append("tranche.tr_id")
        
        # FIXED: Only add cycle code if needed AND not doing DEAL-level aggregation
        # For DEAL scope, we shouldn't include tranche-level columns like cycle_cde 
        # because they can't be in GROUP BY without aggregation
        if 'TrancheBal' in required_models and filters.report_scope != "DEAL":
            base_columns.append("tranchebal.cycle_cde")
        elif 'TrancheBal' in required_models and filters.report_scope == "DEAL":
            # For DEAL scope, we can use MAX or MIN to get a single cycle value per deal
            # since all tranches in a deal should have the same cycle
            base_columns.append("MAX(tranchebal.cycle_cde) AS cycle_cde")
        
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
        
        # Add static field columns from requests
        for request in static_field_requests:
            # Extract field path from the static_field: prefix
            field_path = request.calc_id.replace("static_field:", "")
            
            # Determine required models for this field path
            field_required_models = self._get_required_models_for_field_path(field_path)
            required_models.update(field_required_models)
            
            # FIXED: Skip tranche-level static fields for DEAL scope reports
            if filters.report_scope == "DEAL" and field_path.startswith('tranche.'):
                print(f"DEBUG: Skipping tranche-level static field {field_path} for DEAL scope report")
                continue
            
            # FIXED: Handle tranchebal fields properly for DEAL scope aggregation
            if filters.report_scope == "DEAL" and field_path.startswith('tranchebal.'):
                # For DEAL scope, tranchebal fields need aggregation
                quoted_alias = f'"{request.alias}"' if ' ' in request.alias else request.alias
                
                # Special handling for cycle_cde since it should be the same for all tranches in a deal
                if field_path == 'tranchebal.cycle_cde':
                    base_columns.append(f"MAX({field_path}) AS {quoted_alias}")
                else:
                    # For other tranchebal fields, we might need SUM, AVG, etc. depending on the field
                    # For now, use MAX as a safe default, but this could be made configurable
                    base_columns.append(f"MAX({field_path}) AS {quoted_alias}")
                print(f"DEBUG: Adding aggregated tranchebal field for DEAL scope: MAX({field_path}) AS {quoted_alias}")
            else:
                # For TRANCHE scope or deal-level fields, add normally
                quoted_alias = f'"{request.alias}"' if ' ' in request.alias else request.alias
                base_columns.append(f"{field_path} AS {quoted_alias}")
                print(f"DEBUG: Adding static field from request {field_path} AS {quoted_alias}")  # Debug logging
        
        # Debug logging
        print(f"DEBUG: Report scope: {filters.report_scope}")
        print(f"DEBUG: Required models: {required_models}")
        print(f"DEBUG: system_field_calcs count: {len(system_field_calcs)}")
        print(f"DEBUG: static_field_requests count: {len(static_field_requests)}")
        print(f"DEBUG: base_columns: {base_columns}")
        
        # Build FROM clause
        from_clause = self._build_from_clause(list(required_models))
        
        # Build WHERE clause with parameter injection
        where_clause = self._build_dynamic_where_clause(filters, required_models)
        
        # FIXED: For DEAL scope, add GROUP BY to aggregate tranche-level data to deal level
        group_by_clause = ""
        if filters.report_scope == "DEAL" and ('Tranche' in required_models or 'TrancheBal' in required_models):
            # We need to group by deal-level columns only to aggregate tranche data
            deal_level_columns = set()  # Use set to avoid duplicates
            for col in base_columns:
                # Extract the actual column name (before AS clause)
                actual_col = col.split(' AS ')[0].strip() if ' AS ' in col else col
                
                # Only include deal-level columns in GROUP BY
                if actual_col.startswith('deal.') and not actual_col.startswith(('tranche.', 'tranchebal.')):
                    deal_level_columns.add(actual_col)
            
            if deal_level_columns:
                group_by_clause = f"\nGROUP BY {', '.join(sorted(deal_level_columns))}"
                print(f"DEBUG: Adding GROUP BY for DEAL scope: {group_by_clause}")
        
        return f"""SELECT DISTINCT {', '.join(base_columns)}
{from_clause}
{where_clause}{group_by_clause}"""

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
        
        # Determine what base columns are actually available by checking what's being built
        # FIXED: Check if we actually have TrancheBal in the base query
        has_tranche_bal = False
        required_models = set(['Deal'])
        
        # Check static field requests for TrancheBal
        for request in calc_requests:
            if isinstance(request.calc_id, str) and request.calc_id.startswith("static_field:"):
                field_path = request.calc_id.replace("static_field:", "")
                if field_path.startswith('tranchebal.'):
                    has_tranche_bal = True
                    required_models.add('TrancheBal')
                    required_models.add('Tranche')
        
        # Check regular calculations for TrancheBal
        for request in calc_requests:
            if request.calc_id in calculations:
                calc = calculations[request.calc_id]
                calc_models = calc.get_required_models()
                if 'TrancheBal' in calc_models:
                    has_tranche_bal = True
                    required_models.update(calc_models)
        
        # Check report scope for Tranche requirements
        if filters.report_scope == "TRANCHE":
            required_models.add('Tranche')
            required_models.add('TrancheBal')
            has_tranche_bal = True
        
        # Add base columns based on what's actually available
        select_columns.append("base_data.dl_nbr")
        
        # FIXED: Only add tr_id if report scope is TRANCHE and Tranche is involved
        if filters.report_scope == "TRANCHE" and 'Tranche' in required_models:
            select_columns.append("base_data.tr_id")
        
        # Only add cycle_cde if TrancheBal is involved
        if has_tranche_bal or 'TrancheBal' in required_models:
            select_columns.append("base_data.cycle_cde")

        # Build joins and add calculation columns
        joins = []
        for request in calc_requests:
            # Handle static field requests - FIXED: Skip tranche-level fields for DEAL scope
            if isinstance(request.calc_id, str) and request.calc_id.startswith("static_field:"):
                field_path = request.calc_id.replace("static_field:", "")
                
                # Skip tranche-level static fields for DEAL scope reports
                if filters.report_scope == "DEAL" and field_path.startswith('tranche.'):
                    print(f"DEBUG: Skipping tranche-level static field {field_path} in final SELECT for DEAL scope report")
                    continue
                
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
                
                # FIXED: Determine join condition based on calculation level, not report scope
                # Deal-level calculations only have dl_nbr, tranche-level calculations have both dl_nbr and tr_id
                if calc.group_level.value == "deal":
                    # Deal-level calculations: only join on dl_nbr (same value for all tranches in the deal)
                    join_condition = f"base_data.dl_nbr = {cte_alias}.dl_nbr"
                else:
                    # Tranche-level calculations: join on both dl_nbr and tr_id
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
        
        # FIXED: Only add tr_id to ORDER BY if report scope is TRANCHE and Tranche is involved
        if filters.report_scope == "TRANCHE" and 'Tranche' in required_models:
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