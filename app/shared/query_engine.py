# app/shared/query_engine.py
"""Unified query engine for calculations and reports - combines execution and preview"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, text
from typing import List, Dict, Any, Optional, Tuple, Union, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from app.calculations.models import Calculation

from app.datawarehouse.models import Deal, Tranche, TrancheBal


class QueryEngine:
    """Unified engine for all ORM query operations, execution, and SQL preview"""
    
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
        """Build the consolidated ORM query for both execution and preview"""
        
        # Start with base query structure
        if aggregation_level == "tranche":
            base_query = self.dw_db.query(
                Deal.dl_nbr.label('deal_number'),
                Tranche.tr_id.label('tranche_id'),
                TrancheBal.cycle_cde.label('cycle_code')
            )
        else:
            base_query = self.dw_db.query(
                Deal.dl_nbr.label('deal_number'),
                TrancheBal.cycle_cde.label('cycle_code')
            )
        
        base_query = base_query.select_from(Deal)\
            .join(Tranche, Deal.dl_nbr == Tranche.dl_nbr)\
            .join(TrancheBal, and_(
                Tranche.dl_nbr == TrancheBal.dl_nbr,
                Tranche.tr_id == TrancheBal.tr_id
            ))
        
        # Add each calculation as a column using subquery approach
        for calc in calculations:
            calc_subquery = self._build_calculation_subquery(
                calc, deal_numbers, tranche_ids, cycle_code, aggregation_level
            )
            
            # LEFT JOIN this calculation to the base query
            if aggregation_level == "tranche":
                base_query = base_query.outerjoin(
                    calc_subquery, 
                    and_(
                        Deal.dl_nbr == calc_subquery.c.calc_deal_nbr,
                        Tranche.tr_id == calc_subquery.c.calc_tranche_id
                    )
                )
            else:
                base_query = base_query.outerjoin(
                    calc_subquery, 
                    Deal.dl_nbr == calc_subquery.c.calc_deal_nbr
                )
            
            # Add the calculation column
            column_name = self._get_calc_column_name(calc)
            base_query = base_query.add_columns(calc_subquery.c[column_name].label(calc.name))
        
        # Apply filters and grouping
        final_query = base_query.filter(Deal.dl_nbr.in_(deal_numbers))\
            .filter(Tranche.tr_id.in_(tranche_ids))\
            .filter(TrancheBal.cycle_cde == cycle_code)
        
        if aggregation_level == "tranche":
            final_query = final_query.group_by(Deal.dl_nbr, Tranche.tr_id, TrancheBal.cycle_cde)
        else:
            final_query = final_query.group_by(Deal.dl_nbr, TrancheBal.cycle_cde)
        
        return final_query.distinct()
    
    def _build_calculation_subquery(
        self, 
        calc: "Calculation", 
        deal_numbers: List[int], 
        tranche_ids: List[str], 
        cycle_code: int, 
        aggregation_level: str
    ):
        """Build subquery for a single calculation"""
        
        if aggregation_level == "tranche":
            calc_subquery = self.dw_db.query(
                Deal.dl_nbr.label('calc_deal_nbr'),
                Tranche.tr_id.label('calc_tranche_id'),
                calc.get_sqlalchemy_function().label(self._get_calc_column_name(calc))
            )
        else:
            calc_subquery = self.dw_db.query(
                Deal.dl_nbr.label('calc_deal_nbr'),
                calc.get_sqlalchemy_function().label(self._get_calc_column_name(calc))
            )
        
        calc_subquery = calc_subquery.select_from(Deal)
        
        # Add required joins based on calculation's source model
        required_models = calc.get_required_models()
        
        if Tranche in required_models:
            calc_subquery = calc_subquery.join(Tranche, Deal.dl_nbr == Tranche.dl_nbr)
        
        if TrancheBal in required_models:
            calc_subquery = calc_subquery.join(TrancheBal, and_(
                Tranche.dl_nbr == TrancheBal.dl_nbr,
                Tranche.tr_id == TrancheBal.tr_id
            ))
        
        # Apply filters and group by
        calc_subquery = calc_subquery.filter(Deal.dl_nbr.in_(deal_numbers))\
            .filter(Tranche.tr_id.in_(tranche_ids))\
            .filter(TrancheBal.cycle_cde == cycle_code)
        
        if aggregation_level == "tranche":
            calc_subquery = calc_subquery.group_by(Deal.dl_nbr, Tranche.tr_id)
        else:
            calc_subquery = calc_subquery.group_by(Deal.dl_nbr)
        
        return calc_subquery.subquery()
    
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
        """Build a clean, direct query for single calculation preview (no duplication)"""
        
        # Build base query with calculation
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
                TrancheBal.cycle_cde.label('cycle_cde'),
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
        
        # Group by appropriate level
        if aggregation_level == "tranche":
            query = query.group_by(Deal.dl_nbr, Tranche.tr_id, TrancheBal.cycle_cde)
        else:
            query = query.group_by(Deal.dl_nbr, TrancheBal.cycle_cde)
        
        return query
    
    # Execution Methods
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
    
    # Preview Methods - Simplified to show raw execution SQL only
    def preview_calculation_sql(
        self,
        calculation: "Calculation",
        aggregation_level: str = "deal",
        sample_deals: List[int] = None,
        sample_tranches: List[str] = None,
        sample_cycle: int = None
    ) -> Dict[str, Any]:
        """Generate raw SQL preview for a single calculation using simplified query"""
        
        # Use defaults if not provided
        sample_deals = sample_deals or [101, 102, 103]
        sample_tranches = sample_tranches or ["A", "B"]
        sample_cycle = sample_cycle or 202404
        
        # For single calculation preview, use simplified direct query instead of consolidated approach
        query = self._build_single_calculation_query(
            calculation, sample_deals, sample_tranches, sample_cycle, aggregation_level
        )
        
        return {
            "calculation_name": calculation.name,
            "aggregation_level": aggregation_level,
            "generated_sql": self._compile_query_to_sql(query),
            "sample_parameters": {
                "deals": sample_deals,
                "tranches": sample_tranches,
                "cycle": sample_cycle
            }
        }
    
    def preview_report_sql(
        self,
        report_name: str,
        aggregation_level: str,
        deal_numbers: List[int],
        tranche_ids: List[str],
        cycle_code: int,
        calculations: List["Calculation"]
    ) -> Dict[str, Any]:
        """Generate raw SQL preview for a full report"""
        
        # Build and compile query (identical to execution)
        query = self.build_consolidated_query(
            deal_numbers, tranche_ids, cycle_code, calculations, aggregation_level
        )
        
        return {
            "template_name": report_name,
            "aggregation_level": aggregation_level,
            "sql_query": self._compile_query_to_sql(query),
            "parameters": {
                "cycle_code": cycle_code,
                "deal_numbers": deal_numbers,
                "tranche_ids": tranche_ids
            }
        }
    
    # Utility Methods
    def _compile_query_to_sql(self, query) -> str:
        """Compile SQLAlchemy query to raw SQL string"""
        return str(query.statement.compile(
            dialect=self.dw_db.bind.dialect, 
            compile_kwargs={"literal_binds": True}
        ))
    
    # Data Warehouse Access Methods
    def get_calculations_by_names(self, names: List[str]) -> List["Calculation"]:
        """Get calculations by names from config database"""
        # Import here to avoid circular imports
        from app.calculations.models import Calculation
        return self.config_db.query(Calculation).filter(
            Calculation.name.in_(names),
            Calculation.is_active == True
        ).all()
    
    def get_calculation_by_id(self, calc_id: int) -> Optional["Calculation"]:
        """Get calculation by ID from config database"""
        # Import here to avoid circular imports
        from app.calculations.models import Calculation
        return self.config_db.query(Calculation).filter(
            Calculation.id == calc_id,
            Calculation.is_active == True
        ).first()

    # Result Processing
    def process_report_results(
        self, 
        results: List[Any], 
        calculations: List["Calculation"], 
        aggregation_level: str
    ) -> List[Dict[str, Any]]:
        """Process raw query results into structured report data"""
        
        data = []
        for result in results:
            # Extract base fields
            deal_nbr = result.deal_number
            cycle = result.cycle_code
            
            # Extract calculation values
            values = {}
            for calc in calculations:
                calc_value = getattr(result, calc.name, None)
                values[calc.name] = calc_value
            
            row_data = {
                "dl_nbr": deal_nbr,
                "cycle_cde": cycle,
                "values": values
            }
            
            # Add tranche info for tranche-level reports
            if aggregation_level == "tranche":
                row_data["tr_id"] = result.tranche_id
            
            data.append(row_data)
        
        return data