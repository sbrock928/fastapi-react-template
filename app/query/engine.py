# app/query/engine.py
"""Enhanced query engine supporting User Defined, System Field, and System SQL calculations."""

from sqlalchemy.orm import Session
from sqlalchemy import and_, text, select, func
from typing import List, Dict, Any, Optional, Tuple, Union, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from app.calculations.models import Calculation

from app.datawarehouse.models import Deal, Tranche, TrancheBal


class QueryEngine:
    """Enhanced query engine supporting multiple calculation types including custom SQL."""
    
    def __init__(self, dw_db: Session, config_db: Session):
        self.dw_db = dw_db
        self.config_db = config_db
    
    # ===== MAIN QUERY BUILDING METHOD =====
    
    def build_consolidated_query(
        self, 
        deal_tranche_map: Dict[int, List[str]],
        cycle_code: int, 
        calculations: List["Calculation"], 
        aggregation_level: str
    ):
        """Build consolidated query supporting all calculation types."""
        
        # Separate calculations by type
        user_defined_calcs = [calc for calc in calculations if calc.is_user_defined()]
        system_field_calcs = [calc for calc in calculations if calc.is_system_field()]
        system_sql_calcs = [calc for calc in calculations if calc.is_system_sql()]
        
        # If we have no calculations, return empty result
        if not calculations:
            return self.dw_db.query().filter(False)  # Empty query
        
        # If we have system SQL calculations, we need to handle them differently
        # We'll build a query without them first, then add them via post-processing
        regular_calculations = user_defined_calcs + system_field_calcs
        
        # Build base CTE with deal-tranche mapping and required fields
        base_cte = self._build_base_cte(
            deal_tranche_map=deal_tranche_map,
            cycle_code=cycle_code, 
            calculations=regular_calculations,  # Only regular calculations for base
            aggregation_level=aggregation_level
        )
        
        # If we only have system fields, return simplified query
        if not user_defined_calcs and not system_sql_calcs:
            return self._build_system_fields_only_query(base_cte, system_field_calcs, aggregation_level)
        
        # Build calculation CTEs for user-defined calculations
        user_defined_ctes = {}
        for calc in user_defined_calcs:
            calc_cte = self._build_user_defined_calculation_cte(base_cte, calc, aggregation_level)
            user_defined_ctes[calc.name] = calc_cte
        
        # For system SQL calculations, we'll execute them separately and store results
        system_sql_data = {}
        if system_sql_calcs:
            print(f"Debug: Found {len(system_sql_calcs)} system SQL calculations, executing them separately")
            for calc in system_sql_calcs:
                try:
                    print(f"Debug: Processing system SQL calculation: {calc.name}")
                    print(f"Debug: Raw SQL: {calc.raw_sql}")
                    print(f"Debug: Result column: {calc.result_column_name}")
                    
                    # Execute the system SQL calculation separately
                    system_sql_data[calc.name] = self._execute_system_sql_separately(
                        calc, deal_tranche_map, cycle_code, aggregation_level
                    )
                    print(f"Debug: Successfully executed {calc.name}")
                except Exception as e:
                    print(f"Warning: Failed to execute system SQL calculation '{calc.name}': {e}")
                    import traceback
                    traceback.print_exc()
                    # Store empty data to avoid errors
                    system_sql_data[calc.name] = []
        
        # Build final query that combines regular calculations
        query = self._build_final_combined_query(
            base_cte, user_defined_ctes, {}, system_field_calcs, 
            user_defined_calcs, [], aggregation_level  # Empty system_sql_calcs for now
        )
        
        # Store system SQL data on the query object for post-processing
        query._system_sql_data = system_sql_data
        
        return query
    
    def _build_base_cte(
        self,
        deal_tranche_map: Dict[int, List[str]],
        cycle_code: int,
        calculations: List["Calculation"],
        aggregation_level: str
    ):
        """Build the base CTE with filtered dataset and all required fields."""
        
        # Determine which models we need based on calculations
        required_models = set()
        for calc in calculations:
            if calc.is_user_defined() or calc.is_system_field():
                required_models.update(calc.get_required_models())
            elif calc.is_system_sql():
                # For system SQL, we include all models to be safe
                # In a more sophisticated implementation, we could parse the SQL to determine requirements
                required_models.update([Deal, Tranche, TrancheBal])
        
        # Start with base columns
        base_columns = [
            Deal.dl_nbr.label('deal_number'),
            TrancheBal.cycle_cde.label('cycle_code')
        ]
        
        if aggregation_level == "tranche":
            base_columns.append(Tranche.tr_id.label('tranche_id'))
        
        # Add all fields that calculations will need
        fields_needed = set()
        for calc in calculations:
            if calc.is_user_defined():
                # Get the source model value (handle enum)
                source_model_value = calc.source_model.value if hasattr(calc.source_model, 'value') else calc.source_model
                # Add the main source field
                fields_needed.add((source_model_value, calc.source_field))
                # Add weight field if needed
                if calc.weight_field:
                    fields_needed.add((source_model_value, calc.weight_field))
            elif calc.is_system_field():
                # Add system field
                source_model_value = calc.source_model.value if hasattr(calc.source_model, 'value') else calc.source_model
                fields_needed.add((source_model_value, calc.field_name))
            # For system SQL calculations, we don't add specific fields since they define their own
        
        # Map source models to SQLAlchemy models
        model_map = {
            'Deal': Deal,
            'Tranche': Tranche, 
            'TrancheBal': TrancheBal
        }
        
        # Add the required fields to base columns
        for source_model, field_name in fields_needed:
            model_class = model_map.get(source_model)
            if model_class and hasattr(model_class, field_name):
                field = getattr(model_class, field_name)
                base_columns.append(field.label(f"{source_model}_{field_name}"))
        
        # Build base query
        base_query = self.dw_db.query(*base_columns)
        
        # Add joins based on required models
        base_query = base_query.select_from(Deal)
        
        if Tranche in required_models:
            base_query = base_query.join(Tranche, Deal.dl_nbr == Tranche.dl_nbr)
        
        if TrancheBal in required_models:
            base_query = base_query.join(TrancheBal, and_(
                Tranche.dl_nbr == TrancheBal.dl_nbr,
                Tranche.tr_id == TrancheBal.tr_id
            ))
        
        # Apply filters with proper deal-tranche relationships
        filter_conditions = [TrancheBal.cycle_cde == cycle_code]
        
        # Build optimized deal-specific tranche filters
        if Tranche in required_models and deal_tranche_map:
            deal_conditions = self._build_deal_tranche_conditions_fixed(deal_tranche_map)
            if deal_conditions is not None:
                filter_conditions.append(deal_conditions)
        else:
            # Simple deal filtering when no tranche model needed
            filter_conditions.append(Deal.dl_nbr.in_(list(deal_tranche_map.keys())))
        
        # Apply all filter conditions together using and_()
        base_query = base_query.filter(and_(*filter_conditions))
        
        return base_query.cte('base_data')
    
    def _build_user_defined_calculation_cte(self, base_cte, calc: "Calculation", aggregation_level: str):
        """Build a CTE for a single user-defined aggregated calculation."""
        
        # Get the source model value (handle enum)
        source_model_value = calc.source_model.value if hasattr(calc.source_model, 'value') else calc.source_model
        
        # Get the field reference from the base CTE
        field_name = f"{source_model_value}_{calc.source_field}"
        
        # Check if the field exists in the base CTE
        if not hasattr(base_cte.c, field_name):
            available_fields = [col.name for col in base_cte.c]
            raise ValueError(f"Field '{field_name}' not found in base CTE. Available fields: {available_fields}")
        
        field = getattr(base_cte.c, field_name)
        
        # Build aggregation function
        agg_func_value = calc.aggregation_function.value if hasattr(calc.aggregation_function, 'value') else calc.aggregation_function
        
        if agg_func_value == 'SUM':
            agg_field = func.sum(field)
        elif agg_func_value == 'AVG':
            agg_field = func.avg(field)
        elif agg_func_value == 'COUNT':
            agg_field = func.count(field)
        elif agg_func_value == 'MIN':
            agg_field = func.min(field)
        elif agg_func_value == 'MAX':
            agg_field = func.max(field)
        elif agg_func_value == 'WEIGHTED_AVG':
            if not calc.weight_field:
                raise ValueError(f"Weighted average calculation '{calc.name}' requires weight_field")
            weight_field_name = f"{source_model_value}_{calc.weight_field}"
            if not hasattr(base_cte.c, weight_field_name):
                available_fields = [col.name for col in base_cte.c]
                raise ValueError(f"Weight field '{weight_field_name}' not found in base CTE. Available fields: {available_fields}")
            weight_field = getattr(base_cte.c, weight_field_name)
            agg_field = func.sum(field * weight_field) / func.nullif(func.sum(weight_field), 0)
        else:
            raise ValueError(f"Unsupported aggregation function: {agg_func_value}")
        
        # Build group by columns
        if aggregation_level == "tranche":
            group_columns = [
                base_cte.c.deal_number,
                base_cte.c.tranche_id
            ]
            select_columns = [
                base_cte.c.deal_number.label('calc_deal_nbr'),
                base_cte.c.tranche_id.label('calc_tranche_id'),
                agg_field.label(self._get_calc_column_name(calc))
            ]
        else:
            group_columns = [base_cte.c.deal_number]
            select_columns = [
                base_cte.c.deal_number.label('calc_deal_nbr'),
                agg_field.label(self._get_calc_column_name(calc))
            ]
        
        # Build calculation query
        calc_query = self.dw_db.query(*select_columns)\
            .select_from(base_cte)\
            .group_by(*group_columns)
        
        return calc_query.cte(f'calc_{self._get_calc_column_name(calc)}')
    
    def _build_system_sql_cte(
        self, 
        calc: "Calculation", 
        deal_tranche_map: Dict[int, List[str]], 
        cycle_code: int, 
        aggregation_level: str
    ):
        """Build a subquery for a system SQL calculation."""
        
        if not calc.is_system_sql():
            raise ValueError(f"Calculation {calc.name} is not a system SQL calculation")
        
        # Get the raw SQL from the calculation
        raw_sql = calc.raw_sql
        if not raw_sql:
            raise ValueError(f"System SQL calculation {calc.name} has no raw_sql defined")
        
        # Parse and modify the SQL to include our filters
        modified_sql = self._inject_filters_into_system_sql(
            raw_sql, deal_tranche_map, cycle_code, aggregation_level
        )
        
        # Instead of trying to create a complex CTE, we'll create a simple subquery
        # that can be joined later. We'll use text() to create a simple subquery.
        from sqlalchemy import text
        
        # Create the CTE name for reference
        cte_name = f'system_sql_{self._get_calc_column_name(calc)}'
        
        # Create a simple text-based subquery that we can use in joins
        # We'll return this as a simple subquery that can be aliased
        subquery_sql = f"({modified_sql})"
        
        # Create a mock CTE-like object that has the columns we need
        # This is a simplified approach that avoids the SQLAlchemy CTE complexity
        class MockCTE:
            def __init__(self, sql, result_column, aggregation_level):
                self.sql = sql
                self.result_column = result_column
                self.aggregation_level = aggregation_level
                # Create column references
                self.c = type('MockColumns', (), {
                    'dl_nbr': text('dl_nbr'),
                    result_column: text(result_column)
                })()
                if aggregation_level == "tranche":
                    setattr(self.c, 'tr_id', text('tr_id'))
        
        return MockCTE(subquery_sql, calc.result_column_name, aggregation_level)
    
    def _inject_filters_into_system_sql(
        self, 
        raw_sql: str, 
        deal_tranche_map: Dict[int, List[str]], 
        cycle_code: int, 
        aggregation_level: str
    ) -> str:
        """Inject our filtering conditions into custom SQL."""
        
        # This is a simplified implementation. In a production system, you might want to use
        # a more sophisticated SQL parser to inject filters properly.
        
        # For now, we'll inject basic filters by appending WHERE conditions
        # This assumes the SQL doesn't already have complex WHERE clauses
        
        deal_numbers = list(deal_tranche_map.keys())
        deal_filter = f"deal.dl_nbr IN ({','.join(map(str, deal_numbers))})"
        
        # Inject cycle filter if the SQL references tranchebal
        cycle_filter = ""
        if "tranchebal" in raw_sql.lower():
            cycle_filter = f" AND tranchebal.cycle_cde = {cycle_code}"
        
        # Inject tranche filters if needed
        tranche_filter = ""
        if "tranche" in raw_sql.lower() and aggregation_level == "tranche":
            # For tranche-level reports, we might need specific tranche filters
            # This is a simplified implementation
            all_tranches = []
            for tranches in deal_tranche_map.values():
                all_tranches.extend(tranches)
            if all_tranches:
                escaped_tranches = [f"'{t}'" for t in all_tranches]
                tranche_filter = f" AND tranche.tr_id IN ({','.join(escaped_tranches)})"
        
        # Simple injection strategy: look for WHERE clause or add one
        sql_upper = raw_sql.upper()
        
        if " WHERE " in sql_upper:
            # SQL already has WHERE clause, append our conditions with AND
            modified_sql = raw_sql + f" AND {deal_filter}{cycle_filter}{tranche_filter}"
        else:
            # No WHERE clause, add one
            # Find a good place to insert it (before GROUP BY, ORDER BY, etc.)
            insert_keywords = [" GROUP BY ", " ORDER BY ", " HAVING ", " LIMIT "]
            insert_position = len(raw_sql)  # Default to end
            
            for keyword in insert_keywords:
                pos = sql_upper.find(keyword)
                if pos != -1 and pos < insert_position:
                    insert_position = pos
            
            where_clause = f" WHERE {deal_filter}{cycle_filter}{tranche_filter}"
            modified_sql = raw_sql[:insert_position] + where_clause + raw_sql[insert_position:]
        
        return modified_sql
    
    def _build_system_fields_only_query(self, base_cte, system_field_calcs: List["Calculation"], aggregation_level: str):
        """Build query for system fields only (no aggregation needed)."""
        
        # Start with base columns
        select_columns = [
            base_cte.c.deal_number,
            base_cte.c.cycle_code
        ]
        
        if aggregation_level == "tranche":
            select_columns.append(base_cte.c.tranche_id)
        
        # Add system field columns
        for calc in system_field_calcs:
            source_model_value = calc.source_model.value if hasattr(calc.source_model, 'value') else calc.source_model
            field_name = f"{source_model_value}_{calc.field_name}"
            
            if not hasattr(base_cte.c, field_name):
                available_fields = [col.name for col in base_cte.c]
                raise ValueError(f"System field '{field_name}' not found in base CTE. Available fields: {available_fields}")
            
            field = getattr(base_cte.c, field_name)
            select_columns.append(field.label(calc.name))
        
        return self.dw_db.query(*select_columns).select_from(base_cte).distinct()
    
    def _build_final_combined_query(
        self, 
        base_cte, 
        user_defined_ctes: Dict[str, Any],
        system_sql_ctes: Dict[str, Any],
        system_field_calcs: List["Calculation"],
        user_defined_calcs: List["Calculation"],
        system_sql_calcs: List["Calculation"],
        aggregation_level: str
    ):
        """Build the final query that combines all calculation types."""
        
        # Start with base columns
        select_columns = [
            base_cte.c.deal_number,
            base_cte.c.cycle_code
        ]
        
        if aggregation_level == "tranche":
            select_columns.append(base_cte.c.tranche_id)
        
        # Add system field columns
        for calc in system_field_calcs:
            source_model_value = calc.source_model.value if hasattr(calc.source_model, 'value') else calc.source_model
            field_name = f"{source_model_value}_{calc.field_name}"
            
            if not hasattr(base_cte.c, field_name):
                available_fields = [col.name for col in base_cte.c]
                raise ValueError(f"System field '{field_name}' not found in base CTE. Available fields: {available_fields}")
            
            field = getattr(base_cte.c, field_name)
            select_columns.append(field.label(calc.name))
        
        # Start with base query
        final_query = self.dw_db.query(*select_columns).select_from(base_cte)
        
        # Add user-defined calculation columns and joins
        for calc in user_defined_calcs:
            calc_cte = user_defined_ctes[calc.name]
            
            # Add the calculation column
            column_name = self._get_calc_column_name(calc)
            final_query = final_query.add_columns(
                getattr(calc_cte.c, column_name).label(calc.name)
            )
            
            # Add LEFT JOIN to the calculation CTE
            if aggregation_level == "tranche":
                final_query = final_query.outerjoin(
                    calc_cte,
                    and_(
                        base_cte.c.deal_number == calc_cte.c.calc_deal_nbr,
                        base_cte.c.tranche_id == calc_cte.c.calc_tranche_id
                    )
                )
            else:
                final_query = final_query.outerjoin(
                    calc_cte,
                    base_cte.c.deal_number == calc_cte.c.calc_deal_nbr
                )
        
        # Add system SQL calculation columns and joins
        for calc in system_sql_calcs:
            sql_cte = system_sql_ctes[calc.name]
            
            # Handle MockCTE objects differently from real SQLAlchemy CTEs
            if hasattr(sql_cte, 'sql'):  # This is our MockCTE
                # For MockCTE, we need to create a subquery and join it
                from sqlalchemy import text, literal_column
                
                # Create an alias for the subquery
                subquery_alias = f"sql_{self._get_calc_column_name(calc)}"
                
                # Add the SQL calculation column using a literal column reference
                # We'll create a subquery join that SQLAlchemy can handle
                final_query = final_query.add_columns(
                    literal_column(f"{subquery_alias}.{calc.result_column_name}").label(calc.name)
                )
                
                # Add LEFT JOIN using text() for the subquery
                if aggregation_level == "tranche":
                    join_condition = text(f"""
                        LEFT JOIN {sql_cte.sql} AS {subquery_alias} 
                        ON base_data.deal_number = {subquery_alias}.dl_nbr 
                        AND base_data.tranche_id = {subquery_alias}.tr_id
                    """)
                else:
                    join_condition = text(f"""
                        LEFT JOIN {sql_cte.sql} AS {subquery_alias} 
                        ON base_data.deal_number = {subquery_alias}.dl_nbr
                    """)
                
                # Note: This approach is getting complex. Let's use a simpler method.
                # For now, we'll add a placeholder null value and handle system SQL separately
                final_query = final_query.add_columns(
                    literal_column("NULL").label(calc.name)
                )
            else:
                # This would be a real SQLAlchemy CTE (fallback)
                final_query = final_query.add_columns(
                    getattr(sql_cte.c, calc.result_column_name).label(calc.name)
                )
                
                if aggregation_level == "tranche":
                    final_query = final_query.outerjoin(
                        sql_cte,
                        and_(
                            base_cte.c.deal_number == sql_cte.c.dl_nbr,
                            base_cte.c.tranche_id == sql_cte.c.tr_id
                        )
                    )
                else:
                    final_query = final_query.outerjoin(
                        sql_cte,
                        base_cte.c.deal_number == sql_cte.c.dl_nbr
                    )
        
        return final_query.distinct()
    
    def _build_deal_tranche_conditions_fixed(self, deal_tranche_map: Dict[int, List[str]]):
        """Build optimized WHERE conditions with MANUAL EXPLICIT PARENTHESES for deal-tranche filtering."""
        from app.datawarehouse.dao import DatawarehouseDAO
        from sqlalchemy import and_, or_, text
        
        if not deal_tranche_map:
            return None
        
        # Get all available tranches for each deal to determine "all vs specific"
        dw_dao = DatawarehouseDAO(self.dw_db)
        
        deals_with_specific_tranches = []
        deals_with_all_tranches = []
        
        for dl_nbr, selected_tranches in deal_tranche_map.items():
            if selected_tranches:
                # Get all available tranches for this deal
                all_deal_tranches = dw_dao.get_tranches_by_dl_nbr(dl_nbr)
                all_tranche_ids = [t.tr_id for t in all_deal_tranches]
                
                # Check if selected tranches == all available tranches
                if set(selected_tranches) == set(all_tranche_ids):
                    # This deal has ALL tranches selected - no need for explicit tranche filtering
                    deals_with_all_tranches.append(dl_nbr)
                else:
                    # This deal has specific tranche selections - needs explicit filtering
                    deals_with_specific_tranches.append((dl_nbr, selected_tranches))
            else:
                # Empty list means all tranches (should have been populated by service layer)
                deals_with_all_tranches.append(dl_nbr)
        
        # Build SQL condition string manually with explicit parentheses
        condition_parts = []
        
        # For deals with all tranches: simple deal filter
        if deals_with_all_tranches:
            deal_numbers = ','.join(map(str, deals_with_all_tranches))
            condition_parts.append(f"deal.dl_nbr IN ({deal_numbers})")
        
        # For deals with specific tranches: manual SQL with explicit parentheses
        for dl_nbr, selected_tranches in deals_with_specific_tranches:
            # Escape tranche IDs for SQL safety
            escaped_tranches = ','.join(f"'{t.replace(chr(39), chr(39)+chr(39))}'" for t in selected_tranches)
            condition_parts.append(f"(deal.dl_nbr = {dl_nbr} AND tranche.tr_id IN ({escaped_tranches}))")
        
        # Combine all conditions with OR and return as text()
        if condition_parts:
            full_condition = " OR ".join(condition_parts)
            return text(full_condition)
        else:
            # Fallback if no valid conditions
            return Deal.dl_nbr.in_(list(deal_tranche_map.keys()))
    
    def _get_calc_column_name(self, calc: "Calculation") -> str:
        """Get normalized column name for calculation."""
        return calc.name.lower().replace(" ", "_").replace("-", "_")
    
    # ===== EXECUTION METHODS =====
    
    def execute_report_query(
        self,
        deal_tranche_map: Dict[int, List[str]],
        cycle_code: int,
        calculations: List["Calculation"],
        aggregation_level: str
    ) -> List[Any]:
        """Execute consolidated report query and return results."""
        query = self.build_consolidated_query(
            deal_tranche_map, cycle_code, calculations, aggregation_level
        )
        
        # Execute the main query
        results = query.all()
        
        # If there are system SQL calculations with actual data, merge their results
        if hasattr(query, '_system_sql_data') and query._system_sql_data:
            # Only merge if there's actual data (not empty lists)
            has_real_data = any(len(data) > 0 for data in query._system_sql_data.values())
            if has_real_data:
                results = self._merge_system_sql_results(
                    results, query._system_sql_data, calculations, aggregation_level
                )
        
        return results
    
    def execute_calculation_query(
        self,
        calculation: "Calculation",
        deal_tranche_map: Dict[int, List[str]],
        cycle_code: int,
        aggregation_level: str
    ) -> List[Any]:
        """Execute single calculation query and return results."""
        return self.execute_report_query(
            deal_tranche_map, cycle_code, [calculation], aggregation_level
        )
    
    # ===== PREVIEW METHODS =====
    
    def preview_calculation_sql(
        self,
        calculation: "Calculation",
        aggregation_level: str = "deal",
        sample_deals: List[int] = None,
        sample_tranches: List[str] = None,
        sample_cycle: int = None
    ) -> Dict[str, Any]:
        """Generate SQL preview for a single calculation using mapping approach."""
        
        # Use defaults if not provided
        sample_deals = sample_deals or [101, 102, 103]
        sample_tranches = sample_tranches or ["A", "B"]
        sample_cycle = sample_cycle or 202404
        
        # Convert to mapping format - create a simple mapping for preview
        deal_tranche_map = {}
        for deal in sample_deals:
            deal_tranche_map[deal] = sample_tranches  # Each deal gets the same sample tranches
        
        query = self.build_consolidated_query(
            deal_tranche_map=deal_tranche_map,
            cycle_code=sample_cycle,
            calculations=[calculation],
            aggregation_level=aggregation_level
        )
        
        # Determine calculation type for display
        if calculation.is_system_sql():
            calc_type = "Custom SQL"
        elif calculation.is_system_field():
            calc_type = "System Field"
        elif calculation.is_user_defined():
            calc_type = f"User Defined ({calculation.aggregation_function.value})"
        else:
            calc_type = "Unknown"
        
        return {
            "calculation_name": calculation.name,
            "aggregation_level": aggregation_level,
            "calculation_type": calc_type,
            "generated_sql": self._compile_query_to_sql(query),
            "sample_parameters": {
                "deal_tranche_mapping": deal_tranche_map,
                "cycle": sample_cycle
            }
        }
    
    def preview_report_sql(
        self,
        report_name: str,
        deal_tranche_map: Dict[int, List[str]],
        cycle_code: int,
        calculations: List["Calculation"],
        aggregation_level: str
    ) -> Dict[str, Any]:
        """Generate SQL preview for a full report."""
        
        # Build and compile query using the mapping
        query = self.build_consolidated_query(
            deal_tranche_map=deal_tranche_map,
            cycle_code=cycle_code,
            calculations=calculations,
            aggregation_level=aggregation_level
        )
        
        # Analyze the calculations by type
        user_defined_count = sum(1 for calc in calculations if calc.is_user_defined())
        system_field_count = sum(1 for calc in calculations if calc.is_system_field())
        system_sql_count = sum(1 for calc in calculations if calc.is_system_sql())
        
        # Extract deal numbers and tranche IDs for the response
        deal_numbers = list(deal_tranche_map.keys())
        all_tranche_ids = []
        for tranches in deal_tranche_map.values():
            all_tranche_ids.extend(tranches)
        
        return {
            "template_name": report_name,
            "aggregation_level": aggregation_level,
            "calculation_summary": {
                "total_calculations": len(calculations),
                "user_defined_calculations": user_defined_count,
                "system_field_calculations": system_field_count,
                "system_sql_calculations": system_sql_count
            },
            "deal_tranche_mapping": deal_tranche_map,
            "sql_query": self._compile_query_to_sql(query),
            "parameters": {
                "cycle_code": cycle_code,
                "deal_numbers": deal_numbers,
                "tranche_ids": all_tranche_ids
            }
        }

    # ===== UTILITY METHODS =====
    
    def _compile_query_to_sql(self, query) -> str:
        """Compile SQLAlchemy query to raw SQL string."""
        return str(query.statement.compile(
            dialect=self.dw_db.bind.dialect, 
            compile_kwargs={"literal_binds": True}
        ))
    
    # ===== DATA ACCESS METHODS =====
    
    def get_calculations_by_names(self, names: List[str]) -> List["Calculation"]:
        """Get calculations by names from config database."""
        from app.calculations.models import Calculation
        return self.config_db.query(Calculation).filter(
            Calculation.name.in_(names),
            Calculation.is_active == True
        ).all()
    
    def get_calculation_by_id(self, calc_id: int) -> Optional["Calculation"]:
        """Get calculation by ID from config database."""
        from app.calculations.models import Calculation
        return self.config_db.query(Calculation).filter(
            Calculation.id == calc_id,
            Calculation.is_active == True
        ).first()

    # ===== RESULT PROCESSING =====
    
    def process_report_results(
        self, 
        results: List[Any], 
        calculations: List["Calculation"], 
        aggregation_level: str
    ) -> List[Dict[str, Any]]:
        """Process raw query results into structured report data."""
        
        data = []
        for result in results:
            # Start with base fields
            row_data = {
                "dl_nbr": result.deal_number,
                "cycle_cde": result.cycle_code,
            }
            
            # Add tranche info for tranche-level reports
            if aggregation_level == "tranche":
                row_data["tr_id"] = result.tranche_id
            
            # Add calculation values directly to the row (flatten structure)
            for calc in calculations:
                # Handle normalized field names (spaces converted to underscores)
                calc_value = getattr(result, calc.name, None)
                
                # If the original name doesn't work, try the normalized name
                if calc_value is None and hasattr(result, '_fields'):
                    # Convert calculation name to normalized form
                    import re
                    normalized_name = re.sub(r'[^a-zA-Z0-9_]', '_', str(calc.name))
                    if normalized_name and not normalized_name[0].isalpha() and normalized_name[0] != '_':
                        normalized_name = '_' + normalized_name
                    normalized_name = re.sub(r'_+', '_', normalized_name)
                    normalized_name = normalized_name.rstrip('_')
                    
                    # Try to get the value using the normalized name
                    calc_value = getattr(result, normalized_name, None)
                
                row_data[calc.name] = calc_value
            
            data.append(row_data)
        
        return data
    
    def _execute_system_sql_separately(
        self, 
        calc: "Calculation", 
        deal_tranche_map: Dict[int, List[str]], 
        cycle_code: int, 
        aggregation_level: str
    ):
        """Execute a system SQL calculation separately and return the results."""
        
        # Build the SQL query directly from the calculation's raw SQL
        raw_sql = calc.raw_sql
        if not raw_sql:
            raise ValueError(f"System SQL calculation {calc.name} has no raw_sql defined")
        
        # Inject filters into the raw SQL
        modified_sql = self._inject_filters_into_system_sql(
            raw_sql, deal_tranche_map, cycle_code, aggregation_level
        )
        
        print(f"Debug: Executing system SQL for '{calc.name}':")
        print(f"Debug: Modified SQL: {modified_sql}")
        
        try:
            # Execute the modified SQL and return results
            result = self.dw_db.execute(text(modified_sql))
            rows = result.fetchall()
            print(f"Debug: System SQL '{calc.name}' returned {len(rows)} rows")
            return rows
        except Exception as e:
            print(f"Error executing system SQL '{calc.name}': {e}")
            raise
    
    def _merge_system_sql_results(
        self, 
        main_results: List[Any], 
        system_sql_data: Dict[str, Any], 
        calculations: List["Calculation"], 
        aggregation_level: str
    ) -> List[Any]:
        """Merge system SQL calculation results with main query results."""
        
        # Convert system SQL results to lookup dictionaries
        system_sql_lookups = {}
        for calc_name, sql_results in system_sql_data.items():
            lookup = {}
            for row in sql_results:
                if aggregation_level == "tranche":
                    key = (row.dl_nbr, row.tr_id)
                else:
                    key = row.dl_nbr
                
                # Get the result column value for this calculation
                calc = next((c for c in calculations if c.name == calc_name), None)
                if calc and hasattr(row, calc.result_column_name):
                    lookup[key] = getattr(row, calc.result_column_name)
                else:
                    lookup[key] = None
            
            system_sql_lookups[calc_name] = lookup
        
        # Create new result objects with merged data
        merged_results = []
        for result in main_results:
            # Create a new result object by copying the original
            result_dict = {}
            
            # Copy all original attributes
            for key in result._fields:
                result_dict[key] = getattr(result, key)
            
            # Add system SQL calculation values
            for calc_name, lookup in system_sql_lookups.items():
                if aggregation_level == "tranche":
                    key = (result.deal_number, result.tranche_id)
                else:
                    key = result.deal_number
                
                result_dict[calc_name] = lookup.get(key)
            
            # Create a new named tuple type with all the fields
            # Fix: Normalize field names to be valid Python identifiers
            from collections import namedtuple
            import re
            
            # Normalize field names to be valid Python identifiers
            normalized_fields = []
            field_mapping = {}
            for field_name in result_dict.keys():
                # Replace spaces and special characters with underscores
                normalized_name = re.sub(r'[^a-zA-Z0-9_]', '_', str(field_name))
                # Ensure it starts with a letter or underscore
                if normalized_name and not normalized_name[0].isalpha() and normalized_name[0] != '_':
                    normalized_name = '_' + normalized_name
                # Remove duplicate underscores
                normalized_name = re.sub(r'_+', '_', normalized_name)
                # Remove trailing underscores
                normalized_name = normalized_name.rstrip('_')
                
                normalized_fields.append(normalized_name)
                field_mapping[normalized_name] = field_name
            
            # Create the namedtuple with normalized field names
            ResultType = namedtuple('Result', normalized_fields)
            
            # Create the result with normalized field names
            normalized_data = {}
            for norm_field, orig_field in field_mapping.items():
                normalized_data[norm_field] = result_dict[orig_field]
            
            merged_result = ResultType(**normalized_data)
            
            # Don't try to add attributes to the immutable namedtuple
            # Instead, store the mapping in a simple way that won't cause errors
            merged_results.append(merged_result)
        
        return merged_results