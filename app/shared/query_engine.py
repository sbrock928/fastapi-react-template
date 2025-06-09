# app/shared/query_engine.py
"""Unified query engine for calculations and reports - Updated with CTE-based optimization"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, text, select, func
from typing import List, Dict, Any, Optional, Tuple, Union, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from app.calculations.models import Calculation

from app.datawarehouse.models import Deal, Tranche, TrancheBal


class QueryEngine:
    """Unified engine for all ORM query operations, execution, and SQL preview with CTE-based optimization"""
    
    def __init__(self, dw_db: Session, config_db: Session):
        self.dw_db = dw_db
        self.config_db = config_db
    
    # Core Query Building
    def build_consolidated_query(
        self, 
        deal_numbers: List[int], 
        tranche_ids: List[str], 
        cycle_code: int, 
        calculations: List["Calculation"], 
        aggregation_level: str
    ):
        """Build the consolidated query using CTEs for optimal performance"""
        
        # Separate raw fields from aggregated calculations
        raw_calculations = [calc for calc in calculations if calc.is_raw_field()]
        aggregated_calculations = [calc for calc in calculations if not calc.is_raw_field()]
        
        # If we have no calculations, return empty result
        if not calculations:
            return self.dw_db.query().filter(False)  # Empty query
        
        # Build base CTE with all required fields
        base_cte = self._build_base_cte(
            deal_numbers, tranche_ids, cycle_code, calculations, aggregation_level
        )
        
        # If we only have raw fields, return the base CTE directly
        if not aggregated_calculations:
            return self._build_raw_fields_query(base_cte, raw_calculations, aggregation_level)
        
        # Build calculation CTEs for aggregated calculations
        calculation_ctes = {}
        for calc in aggregated_calculations:
            calc_cte = self._build_calculation_cte(base_cte, calc, aggregation_level)
            calculation_ctes[calc.name] = calc_cte
        
        # Build final query that joins base CTE with calculation CTEs
        return self._build_final_cte_query(
            base_cte, calculation_ctes, raw_calculations, aggregated_calculations, aggregation_level
        )
    
    def _build_base_cte(
        self,
        deal_numbers: List[int],
        tranche_ids: List[str], 
        cycle_code: int,
        calculations: List["Calculation"],
        aggregation_level: str,
        deal_tranche_map: Optional[Dict[int, List[str]]] = None
    ):
        """Build the base CTE with filtered dataset and all required fields"""
        
        # Determine which models we need based on calculations
        required_models = set()
        for calc in calculations:
            required_models.update(calc.get_required_models())
        
        # Start with base columns
        base_columns = [
            Deal.dl_nbr.label('deal_number'),
            TrancheBal.cycle_cde.label('cycle_code')
        ]
        
        if aggregation_level == "tranche":
            base_columns.append(Tranche.tr_id.label('tranche_id'))
        
        # Add all fields that calculations will need (for both raw and aggregated)
        fields_needed = set()
        for calc in calculations:
            # Get the source model value (handle enum)
            source_model_value = calc.source_model.value if hasattr(calc.source_model, 'value') else calc.source_model
            # Add the main source field
            fields_needed.add((source_model_value, calc.source_field))
            # Add weight field if needed
            if calc.weight_field:
                fields_needed.add((source_model_value, calc.weight_field))
        
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
        base_query = base_query.filter(TrancheBal.cycle_cde == cycle_code)
        
        # Build deal-specific tranche filters
        if deal_tranche_map and Tranche in required_models:
            # Create OR conditions for each deal and its specific tranches
            deal_tranche_conditions = []
            for dl_nbr, selected_tranches in deal_tranche_map.items():
                if selected_tranches:  # Only if there are selected tranches for this deal
                    deal_condition = and_(
                        Deal.dl_nbr == dl_nbr,
                        Tranche.tr_id.in_(selected_tranches)
                    )
                    deal_tranche_conditions.append(deal_condition)
            
            if deal_tranche_conditions:
                from sqlalchemy import or_
                base_query = base_query.filter(or_(*deal_tranche_conditions))
            else:
                # Fallback to simple filtering if no specific tranches
                base_query = base_query.filter(Deal.dl_nbr.in_(deal_numbers))
        else:
            # Simple filtering when no deal-tranche mapping provided (backward compatibility)
            base_query = base_query.filter(Deal.dl_nbr.in_(deal_numbers))
            if Tranche in required_models:
                base_query = base_query.filter(Tranche.tr_id.in_(tranche_ids))
        
        return base_query.cte('base_data')
    
    def _build_calculation_cte(self, base_cte, calc: "Calculation", aggregation_level: str):
        """Build a CTE for a single aggregated calculation"""
        
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
    
    def _build_raw_fields_query(self, base_cte, raw_calculations: List["Calculation"], aggregation_level: str):
        """Build query for raw fields only (no aggregation needed)"""
        
        # Start with base columns
        select_columns = [
            base_cte.c.deal_number,
            base_cte.c.cycle_code
        ]
        
        if aggregation_level == "tranche":
            select_columns.append(base_cte.c.tranche_id)
        
        # Add raw field columns
        for calc in raw_calculations:
            source_model_value = calc.source_model.value if hasattr(calc.source_model, 'value') else calc.source_model
            field_name = f"{source_model_value}_{calc.source_field}"
            
            if not hasattr(base_cte.c, field_name):
                available_fields = [col.name for col in base_cte.c]
                raise ValueError(f"Raw field '{field_name}' not found in base CTE. Available fields: {available_fields}")
            
            field = getattr(base_cte.c, field_name)
            select_columns.append(field.label(calc.name))
        
        return self.dw_db.query(*select_columns).select_from(base_cte).distinct()
    
    def _build_final_cte_query(
        self, 
        base_cte, 
        calculation_ctes: Dict[str, Any], 
        raw_calculations: List["Calculation"],
        aggregated_calculations: List["Calculation"], 
        aggregation_level: str
    ):
        """Build the final query that joins base CTE with calculation CTEs"""
        
        # Start with base columns
        select_columns = [
            base_cte.c.deal_number,
            base_cte.c.cycle_code
        ]
        
        if aggregation_level == "tranche":
            select_columns.append(base_cte.c.tranche_id)
        
        # Add raw field columns
        for calc in raw_calculations:
            source_model_value = calc.source_model.value if hasattr(calc.source_model, 'value') else calc.source_model
            field_name = f"{source_model_value}_{calc.source_field}"
            
            if not hasattr(base_cte.c, field_name):
                available_fields = [col.name for col in base_cte.c]
                raise ValueError(f"Raw field '{field_name}' not found in base CTE. Available fields: {available_fields}")
            
            field = getattr(base_cte.c, field_name)
            select_columns.append(field.label(calc.name))
        
        # Start with base query
        final_query = self.dw_db.query(*select_columns).select_from(base_cte)
        
        # Add calculation columns and joins
        for calc in aggregated_calculations:
            calc_cte = calculation_ctes[calc.name]
            
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
        
        return final_query.distinct()
    
    def _get_calc_column_name(self, calc: "Calculation") -> str:
        """Get normalized column name for calculation"""
        return calc.name.lower().replace(" ", "_").replace("-", "_")
    
    def _build_single_calculation_query(
        self,
        calculation: "Calculation",
        deal_numbers: List[int],
        tranche_ids: List[str],
        cycle_code: int,
        aggregation_level: str
    ):
        """Build a clean, direct query for single calculation preview (handles both raw and aggregated)"""
        
        # For raw fields, build a simple select query
        if calculation.is_raw_field():
            if aggregation_level == "tranche":
                query = self.dw_db.query(
                    Deal.dl_nbr.label('deal_number'),
                    Tranche.tr_id.label('tranche_id'),
                    TrancheBal.cycle_cde.label('cycle_code'),
                    calculation.get_sqlalchemy_function().label(calculation.name)
                )
            else:
                query = self.dw_db.query(
                    Deal.dl_nbr.label('deal_number'),
                    TrancheBal.cycle_cde.label('cycle_code'),
                    calculation.get_sqlalchemy_function().label(calculation.name)
                )
        else:
            # For aggregated fields, build aggregated query
            if aggregation_level == "tranche":
                query = self.dw_db.query(
                    Deal.dl_nbr.label('deal_number'),
                    Tranche.tr_id.label('tranche_id'),
                    TrancheBal.cycle_cde.label('cycle_code'),
                    calculation.get_sqlalchemy_function().label(calculation.name)
                )
            else:
                query = self.dw_db.query(
                    Deal.dl_nbr.label('deal_number'),
                    TrancheBal.cycle_cde.label('cycle_code'),
                    calculation.get_sqlalchemy_function().label(calculation.name)
                )
        
        # Add required joins based on calculation's source model
        query = query.select_from(Deal)
        required_models = calculation.get_required_models()
        
        if Tranche in required_models:
            query = query.join(Tranche, Deal.dl_nbr == Tranche.dl_nbr)
        
        if TrancheBal in required_models:
            query = query.join(TrancheBal, and_(
                Tranche.dl_nbr == TrancheBal.dl_nbr,
                Tranche.tr_id == TrancheBal.tr_id
            ))
        
        # Apply filters
        query = query.filter(Deal.dl_nbr.in_(deal_numbers))\
            .filter(Tranche.tr_id.in_(tranche_ids))\
            .filter(TrancheBal.cycle_cde == cycle_code)
        
        # Group by appropriate level only for aggregated calculations
        if not calculation.is_raw_field():
            if aggregation_level == "tranche":
                query = query.group_by(Deal.dl_nbr, Tranche.tr_id, TrancheBal.cycle_cde)
            else:
                query = query.group_by(Deal.dl_nbr, TrancheBal.cycle_cde)
        
        return query
    
    # Execution Methods (unchanged)
    def execute_report_query(
        self,
        deal_numbers: List[int],
        tranche_ids: List[str], 
        cycle_code: int,
        calculations: List["Calculation"],
        aggregation_level: str
    ) -> List[Any]:
        """Execute consolidated report query and return results"""
        query = self.build_consolidated_query(
            deal_numbers, tranche_ids, cycle_code, calculations, aggregation_level
        )
        return query.all()
    
    def execute_calculation_query(
        self,
        calculation: "Calculation",
        deal_numbers: List[int],
        tranche_ids: List[str],
        cycle_code: int,
        aggregation_level: str
    ) -> List[Any]:
        """Execute single calculation query and return results"""
        return self.execute_report_query(
            deal_numbers, tranche_ids, cycle_code, [calculation], aggregation_level
        )
    
    # Execution Methods with deal-tranche mapping support
    def execute_report_query_with_mapping(
        self,
        deal_tranche_map: Dict[int, List[str]],
        cycle_code: int,
        calculations: List["Calculation"],
        aggregation_level: str
    ) -> List[Any]:
        """Execute consolidated report query with proper deal-tranche mapping"""
        # Extract all deal numbers and tranche IDs for backward compatibility
        deal_numbers = list(deal_tranche_map.keys())
        all_tranche_ids = []
        for tranches in deal_tranche_map.values():
            all_tranche_ids.extend(tranches)
        
        # Build query with proper deal-tranche mapping
        query = self.build_consolidated_query_with_mapping(
            deal_tranche_map=deal_tranche_map,
            cycle_code=cycle_code,
            calculations=calculations,
            aggregation_level=aggregation_level
        )
        return query.all()

    def build_consolidated_query_with_mapping(
        self, 
        deal_tranche_map: Dict[int, List[str]],
        cycle_code: int, 
        calculations: List["Calculation"], 
        aggregation_level: str
    ):
        """Build the consolidated query using CTEs with deal-tranche mapping"""
        
        # Separate raw fields from aggregated calculations
        raw_calculations = [calc for calc in calculations if calc.is_raw_field()]
        aggregated_calculations = [calc for calc in calculations if not calc.is_raw_field()]
        
        # If we have no calculations, return empty result
        if not calculations:
            return self.dw_db.query().filter(False)  # Empty query
        
        # Extract for backward compatibility
        deal_numbers = list(deal_tranche_map.keys())
        all_tranche_ids = []
        for tranches in deal_tranche_map.values():
            all_tranche_ids.extend(tranches)
        
        # Build base CTE with deal-tranche mapping
        base_cte = self._build_base_cte(
            deal_numbers=deal_numbers,
            tranche_ids=all_tranche_ids, 
            cycle_code=cycle_code, 
            calculations=calculations, 
            aggregation_level=aggregation_level,
            deal_tranche_map=deal_tranche_map  # Pass the mapping
        )
        
        # If we only have raw fields, return the base CTE directly
        if not aggregated_calculations:
            return self._build_raw_fields_query(base_cte, raw_calculations, aggregation_level)
        
        # Build calculation CTEs for aggregated calculations
        calculation_ctes = {}
        for calc in aggregated_calculations:
            calc_cte = self._build_calculation_cte(base_cte, calc, aggregation_level)
            calculation_ctes[calc.name] = calc_cte
        
        # Build final query that joins base CTE with calculation CTEs
        return self._build_final_cte_query(
            base_cte, calculation_ctes, raw_calculations, aggregated_calculations, aggregation_level
        )

    # Preview Methods
    def preview_calculation_sql(
        self,
        calculation: "Calculation",
        aggregation_level: str = "deal",
        sample_deals: List[int] = None,
        sample_tranches: List[str] = None,
        sample_cycle: int = None
    ) -> Dict[str, Any]:
        """Generate raw SQL preview for a single calculation (handles both raw and aggregated)"""
        
        # Use defaults if not provided
        sample_deals = sample_deals or [101, 102, 103]
        sample_tranches = sample_tranches or ["A", "B"]
        sample_cycle = sample_cycle or 202404
        
        query = self._build_single_calculation_query(
            calculation, sample_deals, sample_tranches, sample_cycle, aggregation_level
        )
        
        return {
            "calculation_name": calculation.name,
            "aggregation_level": aggregation_level,
            "calculation_type": "Raw Field" if calculation.is_raw_field() else "Aggregated Calculation",
            "generated_sql": self._compile_query_to_sql(query),
            "sample_parameters": {
                "deals": sample_deals,
                "tranches": sample_tranches,
                "cycle": sample_cycle
            }
        }
    
    def preview_report_sql_with_mapping(
        self,
        report_name: str,
        deal_tranche_map: Dict[int, List[str]],
        cycle_code: int,
        calculations: List["Calculation"],
        aggregation_level: str
    ) -> Dict[str, Any]:
        """Generate raw SQL preview for a full report with proper deal-tranche mapping"""
        
        # Build and compile query using the mapping (identical to execution)
        query = self.build_consolidated_query_with_mapping(
            deal_tranche_map=deal_tranche_map,
            cycle_code=cycle_code,
            calculations=calculations,
            aggregation_level=aggregation_level
        )
        
        # Analyze the calculations
        raw_count = sum(1 for calc in calculations if calc.is_raw_field())
        aggregated_count = len(calculations) - raw_count
        
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
                "raw_fields": raw_count,
                "aggregated_calculations": aggregated_count
            },
            "deal_tranche_mapping": deal_tranche_map,  # Include the mapping in response
            "sql_query": self._compile_query_to_sql(query),
            "parameters": {
                "cycle_code": cycle_code,
                "deal_numbers": deal_numbers,
                "tranche_ids": all_tranche_ids
            }
        }

    # Utility Methods (unchanged)
    def _compile_query_to_sql(self, query) -> str:
        """Compile SQLAlchemy query to raw SQL string"""
        return str(query.statement.compile(
            dialect=self.dw_db.bind.dialect, 
            compile_kwargs={"literal_binds": True}
        ))
    
    # Data Warehouse Access Methods (unchanged)
    def get_calculations_by_names(self, names: List[str]) -> List["Calculation"]:
        """Get calculations by names from config database"""
        from app.calculations.models import Calculation
        return self.config_db.query(Calculation).filter(
            Calculation.name.in_(names),
            Calculation.is_active == True
        ).all()
    
    def get_calculation_by_id(self, calc_id: int) -> Optional["Calculation"]:
        """Get calculation by ID from config database"""
        from app.calculations.models import Calculation
        return self.config_db.query(Calculation).filter(
            Calculation.id == calc_id,
            Calculation.is_active == True
        ).first()

    # Result Processing (unchanged)
    def process_report_results(
        self, 
        results: List[Any], 
        calculations: List["Calculation"], 
        aggregation_level: str
    ) -> List[Dict[str, Any]]:
        """Process raw query results into structured report data"""
        
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
                calc_value = getattr(result, calc.name, None)
                row_data[calc.name] = calc_value
            
            data.append(row_data)
        
        return data