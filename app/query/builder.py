"""
Core QueryBuilder class for constructing SQL queries in a type-safe, extensible way.

This is the single source of truth for all query construction. Both preview
and execution operations use the same code paths through this builder.
"""

from typing import Dict, List, Optional, Any, Set, Tuple, Union
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.sql import Select

from .schemas import (
    QueryParameters, QueryResult, PreviewResult, CalculationDefinition,
    FieldDefinition, TableRelationship, AggregationLevel, FieldType,
    AggregationFunction, DealTrancheFilter
)


class QueryBuilder:
    """
    Builds SQL queries for the reporting system using a CTE-based approach.
    
    This class provides a single, authoritative way to construct queries
    that ensures preview and execution use identical SQL generation logic.
    """
    
    def __init__(self, dw_session: Session):
        self.dw_session = dw_session
        self._table_registry = self._initialize_table_registry()
        self._relationship_registry = self._initialize_relationships()
        self._system_fields = self._initialize_system_fields()
    
    def build_query(self, params: QueryParameters) -> Select:
        """
        Build a complete SQLAlchemy query from parameters.
        
        This is the main entry point that both preview and execution use.
        Returns a SQLAlchemy Select object that can be executed or compiled to SQL.
        """
        # Separate system fields from user-defined calculations
        system_fields = [calc for calc in params.calculations if calc.is_system_field()]
        user_calculations = [calc for calc in params.calculations if calc.is_user_defined()]
        
        # Build the base CTE with all required data
        base_cte = self._build_base_data_cte(params, system_fields + user_calculations)
        
        # If we only have system fields, return a simple query
        if not user_calculations:
            return self._build_system_fields_only_query(base_cte, system_fields, params.aggregation_level)
        
        # Build calculation CTEs for user-defined calculations
        calculation_ctes = {}
        for calc in user_calculations:
            calc_cte = self._build_calculation_cte(base_cte, calc, params.aggregation_level)
            calculation_ctes[calc.name] = calc_cte
        
        # Build final query that combines everything
        return self._build_final_query(
            base_cte, calculation_ctes, system_fields, user_calculations, params.aggregation_level
        )
    
    def build_preview(self, params: QueryParameters) -> PreviewResult:
        """
        Build a query preview using the exact same logic as execution.
        
        Returns both the query and metadata about the query structure.
        """
        query = self.build_query(params)
        sql_string = self._compile_query_to_sql(query)
        
        # Analyze the query structure
        system_field_count = sum(1 for calc in params.calculations if calc.is_system_field())
        user_calc_count = sum(1 for calc in params.calculations if calc.is_user_defined())
        
        calculation_summary = {
            "total_calculations": len(params.calculations),
            "system_fields": system_field_count,
            "user_defined_calculations": user_calc_count,
            "aggregation_level": params.aggregation_level.value,
            "deals_included": len(params.deal_tranche_filters),
            "total_deal_numbers": params.get_all_deal_numbers(),
        }
        
        # Extract column names from Select object
        columns = [str(col.key) for col in query.selected_columns]
        
        query_result = QueryResult(
            sql=sql_string,
            parameters=self._extract_query_parameters(params),
            columns=columns
        )
        
        return PreviewResult(
            query_result=query_result,
            calculation_summary=calculation_summary
        )
    
    def _build_base_data_cte(self, params: QueryParameters, all_calculations: List[CalculationDefinition]) -> Any:
        """
        Build the base CTE that contains all filtered data and required fields.
        
        This CTE includes:
        - All deals and tranches based on filters
        - Cycle filtering
        - All fields needed by any calculation
        """
        from app.datawarehouse.models import Deal, Tranche, TrancheBal
        
        # Determine required columns based on aggregation level
        base_columns = [
            Deal.dl_nbr.label('deal_number'),
            TrancheBal.cycle_cde.label('cycle_code')
        ]
        
        if params.aggregation_level == AggregationLevel.TRANCHE:
            base_columns.append(Tranche.tr_id.label('tranche_id'))
        
        # Add all fields that calculations will need
        required_fields = self._get_required_fields(all_calculations)
        for field_def in required_fields:
            model_class = self._get_model_for_table(field_def.table_name)
            if model_class and hasattr(model_class, field_def.column_name):
                column = getattr(model_class, field_def.column_name)
                base_columns.append(column.label(f"{field_def.table_name}_{field_def.column_name}"))
        
        # Build base query with joins
        base_query = select(*base_columns)
        base_query = base_query.select_from(Deal)
        
        # Add required joins based on calculations
        required_tables = self._get_required_tables(all_calculations)
        if 'Tranche' in required_tables:
            base_query = base_query.join(Tranche, Deal.dl_nbr == Tranche.dl_nbr)
        if 'TrancheBal' in required_tables:
            base_query = base_query.join(TrancheBal, and_(
                Tranche.dl_nbr == TrancheBal.dl_nbr,
                Tranche.tr_id == TrancheBal.tr_id
            ))
        
        # Apply filters
        filter_conditions = [TrancheBal.cycle_cde == params.cycle_code]
        
        # Build optimized deal-tranche filters
        deal_conditions = self._build_deal_tranche_conditions(params.deal_tranche_filters)
        if deal_conditions is not None:
            filter_conditions.append(deal_conditions)
        
        base_query = base_query.filter(and_(*filter_conditions))
        
        return base_query.cte('base_data')
    
    def _build_calculation_cte(self, base_cte: Any, calculation: CalculationDefinition, aggregation_level: AggregationLevel) -> Any:
        """Build a CTE for a single user-defined calculation."""
        if not calculation.is_user_defined():
            raise ValueError(f"Cannot build calculation CTE for non-user-defined calculation: {calculation.name}")
        
        # Get the source field from the base CTE
        field_name = f"{calculation.source_table}_{calculation.source_column}"
        if not hasattr(base_cte.c, field_name):
            available_fields = [col.name for col in base_cte.c]
            raise ValueError(f"Field '{field_name}' not found in base CTE. Available: {available_fields}")
        
        source_field = getattr(base_cte.c, field_name)
        
        # Build aggregation function
        agg_field = self._build_aggregation_expression(
            calculation.aggregation_function, source_field, calculation.weight_field, base_cte
        )
        
        # Build grouping columns and select columns
        if aggregation_level == AggregationLevel.TRANCHE:
            group_columns = [base_cte.c.deal_number, base_cte.c.tranche_id]
            select_columns = [
                base_cte.c.deal_number.label('calc_deal_number'),
                base_cte.c.tranche_id.label('calc_tranche_id'),
                agg_field.label(self._get_calculation_column_name(calculation))
            ]
        else:
            group_columns = [base_cte.c.deal_number]
            select_columns = [
                base_cte.c.deal_number.label('calc_deal_number'),
                agg_field.label(self._get_calculation_column_name(calculation))
            ]
        
        # Build the calculation query
        calc_query = select(*select_columns)\
            .select_from(base_cte)\
            .group_by(*group_columns)
        
        return calc_query.cte(f'calc_{self._get_calculation_column_name(calculation)}')
    
    def _build_system_fields_only_query(self, base_cte: Any, system_fields: List[CalculationDefinition], aggregation_level: AggregationLevel) -> Select:
        """Build a query that only selects system fields (no aggregation needed)."""
        select_columns = [
            base_cte.c.deal_number,
            base_cte.c.cycle_code
        ]
        
        if aggregation_level == AggregationLevel.TRANCHE:
            select_columns.append(base_cte.c.tranche_id)
        
        # Add system field columns
        for calc in system_fields:
            if calc.source_field:
                field_name = f"{calc.source_field.table_name}_{calc.source_field.column_name}"
                if hasattr(base_cte.c, field_name):
                    field_column = getattr(base_cte.c, field_name)
                    select_columns.append(field_column.label(calc.name))
        
        return select(*select_columns).select_from(base_cte).distinct()
    
    def _build_final_query(
        self, 
        base_cte: Any, 
        calculation_ctes: Dict[str, Any], 
        system_fields: List[CalculationDefinition],
        user_calculations: List[CalculationDefinition], 
        aggregation_level: AggregationLevel
    ) -> Select:
        """Build the final query that combines base CTE with calculation CTEs."""
        # Start with base columns
        select_columns = [
            base_cte.c.deal_number,
            base_cte.c.cycle_code
        ]
        
        if aggregation_level == AggregationLevel.TRANCHE:
            select_columns.append(base_cte.c.tranche_id)
        
        # Add system field columns
        for calc in system_fields:
            if calc.source_field:
                field_name = f"{calc.source_field.table_name}_{calc.source_field.column_name}"
                if hasattr(base_cte.c, field_name):
                    field_column = getattr(base_cte.c, field_name)
                    select_columns.append(field_column.label(calc.name))
        
        # Build a list of all columns for the final select
        all_columns = list(select_columns)
        
        # Add calculation columns
        for calc in user_calculations:
            calc_cte = calculation_ctes[calc.name]
            column_name = self._get_calculation_column_name(calc)
            all_columns.append(getattr(calc_cte.c, column_name).label(calc.name))
        
        # Build the final query with all columns
        final_query = select(*all_columns).select_from(base_cte)
        
        # Add joins to calculation CTEs
        for calc in user_calculations:
            calc_cte = calculation_ctes[calc.name]
            
            # Add LEFT JOIN to the calculation CTE
            if aggregation_level == AggregationLevel.TRANCHE:
                final_query = final_query.outerjoin(
                    calc_cte,
                    and_(
                        base_cte.c.deal_number == calc_cte.c.calc_deal_number,
                        base_cte.c.tranche_id == calc_cte.c.calc_tranche_id
                    )
                )
            else:
                final_query = final_query.outerjoin(
                    calc_cte,
                    base_cte.c.deal_number == calc_cte.c.calc_deal_number
                )
        
        return final_query.distinct()
    
    def _build_aggregation_expression(self, agg_func: AggregationFunction, source_field, weight_field: Optional[FieldDefinition], base_cte: Any):
        """Build the SQLAlchemy aggregation expression for a calculation."""
        if agg_func == AggregationFunction.SUM:
            return func.sum(source_field)
        elif agg_func == AggregationFunction.AVG:
            return func.avg(source_field)
        elif agg_func == AggregationFunction.COUNT:
            return func.count(source_field)
        elif agg_func == AggregationFunction.MIN:
            return func.min(source_field)
        elif agg_func == AggregationFunction.MAX:
            return func.max(source_field)
        elif agg_func == AggregationFunction.WEIGHTED_AVG:
            if not weight_field:
                raise ValueError("Weighted average requires a weight field")
            weight_field_name = f"{weight_field.table_name}_{weight_field.column_name}"
            if not hasattr(base_cte.c, weight_field_name):
                raise ValueError(f"Weight field '{weight_field_name}' not found in base CTE")
            weight_column = getattr(base_cte.c, weight_field_name)
            return func.sum(source_field * weight_column) / func.nullif(func.sum(weight_column), 0)
        else:
            raise ValueError(f"Unsupported aggregation function: {agg_func}")
    
    def _build_deal_tranche_conditions(self, filters: List[DealTrancheFilter]):
        """Build optimized WHERE conditions for deal-tranche filtering."""
        from app.datawarehouse.models import Deal, Tranche
        
        if not filters:
            return None
        
        # Separate deals with specific tranche selections from those with all tranches
        specific_tranche_conditions = []
        all_tranche_deals = []
        
        for deal_filter in filters:
            if deal_filter.includes_all_tranches():
                all_tranche_deals.append(deal_filter.deal_number)
            else:
                # This deal has specific tranche selections
                specific_tranche_conditions.append(and_(
                    Deal.dl_nbr == deal_filter.deal_number,
                    Tranche.tr_id.in_(deal_filter.tranche_ids)
                ))
        
        # Combine conditions
        conditions = []
        
        if all_tranche_deals:
            conditions.append(Deal.dl_nbr.in_(all_tranche_deals))
        
        if specific_tranche_conditions:
            conditions.append(or_(*specific_tranche_conditions))
        
        if len(conditions) == 1:
            return conditions[0]
        elif len(conditions) > 1:
            return or_(*conditions)
        else:
            return None
    
    def _get_required_fields(self, calculations: List[CalculationDefinition]) -> Set[FieldDefinition]:
        """Get all fields required by the given calculations."""
        fields = set()
        for calc in calculations:
            if calc.source_field:
                fields.add(calc.source_field)
            if calc.weight_field:
                fields.add(calc.weight_field)
        return fields
    
    def _get_required_tables(self, calculations: List[CalculationDefinition]) -> Set[str]:
        """Get all table names required by the given calculations."""
        tables = {'Deal'}  # Always need Deal as base
        for calc in calculations:
            if calc.source_table:
                tables.add(calc.source_table)
                # Add dependent tables based on relationships
                if calc.source_table in ['Tranche', 'TrancheBal']:
                    tables.add('Tranche')
                if calc.source_table == 'TrancheBal':
                    tables.add('TrancheBal')
        return tables
    
    def _get_calculation_column_name(self, calculation: CalculationDefinition) -> str:
        """Get normalized column name for a calculation."""
        return calculation.name.lower().replace(" ", "_").replace("-", "_")
    
    def _compile_query_to_sql(self, query: Select) -> str:
        """Compile SQLAlchemy query to raw SQL string."""
        return str(query.compile(
            dialect=self.dw_session.bind.dialect,
            compile_kwargs={"literal_binds": True}
        ))
    
    def _extract_query_parameters(self, params: QueryParameters) -> Dict[str, Any]:
        """Extract key parameters for debugging/logging."""
        return {
            "cycle_code": params.cycle_code,
            "deal_numbers": params.get_all_deal_numbers(),
            "tranche_ids": params.get_all_tranche_ids(),
            "aggregation_level": params.aggregation_level.value,
            "calculation_count": len(params.calculations)
        }
    
    def _initialize_table_registry(self) -> Dict[str, Any]:
        """Initialize the registry of available tables."""
        from app.datawarehouse.models import Deal, Tranche, TrancheBal
        return {
            'Deal': Deal,
            'Tranche': Tranche,
            'TrancheBal': TrancheBal
        }
    
    def _initialize_relationships(self) -> List[TableRelationship]:
        """Initialize the registry of table relationships."""
        return [
            TableRelationship(
                parent_table='Deal',
                child_table='Tranche',
                join_conditions=[('dl_nbr', 'dl_nbr')]
            ),
            TableRelationship(
                parent_table='Tranche',
                child_table='TrancheBal',
                join_conditions=[('dl_nbr', 'dl_nbr'), ('tr_id', 'tr_id')]
            )
        ]
    
    def _initialize_system_fields(self) -> List[FieldDefinition]:
        """Initialize the registry of system fields (raw fields available to users)."""
        return [
            # Deal fields
            FieldDefinition(
                name="Deal Number",
                table_name="Deal",
                column_name="dl_nbr",
                field_type=FieldType.SYSTEM,
                data_type="number",
                description="Unique deal identifier"
            ),
            FieldDefinition(
                name="Issuer Code",
                table_name="Deal",
                column_name="issr_cde",
                field_type=FieldType.SYSTEM,
                data_type="string",
                description="Deal issuer code"
            ),
            # Tranche fields
            FieldDefinition(
                name="Tranche ID",
                table_name="Tranche",
                column_name="tr_id",
                field_type=FieldType.SYSTEM,
                data_type="string",
                description="Tranche identifier within the deal"
            ),
            # TrancheBal fields
            FieldDefinition(
                name="Ending Balance Amount",
                table_name="TrancheBal",
                column_name="tr_end_bal_amt",
                field_type=FieldType.SYSTEM,
                data_type="currency",
                description="Outstanding principal balance at period end"
            ),
            FieldDefinition(
                name="Pass Through Rate",
                table_name="TrancheBal",
                column_name="tr_pass_thru_rte",
                field_type=FieldType.SYSTEM,
                data_type="percentage",
                description="Interest rate passed through to investors"
            ),
            FieldDefinition(
                name="Cycle Code",
                table_name="TrancheBal",
                column_name="cycle_cde",
                field_type=FieldType.SYSTEM,
                data_type="number",
                description="Reporting cycle identifier"
            ),
        ]
    
    def _get_model_for_table(self, table_name: str):
        """Get the SQLAlchemy model class for a table name."""
        return self._table_registry.get(table_name)
    
    def get_available_system_fields(self) -> List[FieldDefinition]:
        """Get all available system fields."""
        return self._system_fields.copy()
    
    def get_available_tables(self) -> List[str]:
        """Get all available table names."""
        return list(self._table_registry.keys())