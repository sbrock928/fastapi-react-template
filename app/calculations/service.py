# app/features/calculations/service.py
"""Refactored calculation service using unified query engine"""

from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from app.core.exceptions import CalculationNotFoundError, CalculationAlreadyExistsError, InvalidCalculationError

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from app.shared.query_engine import QueryEngine

from .dao import CalculationDAO
from .models import Calculation, AggregationFunction, SourceModel, GroupLevel
from .schemas import CalculationCreateRequest, CalculationResponse

class CalculationService:
    """Streamlined calculation service using unified query engine"""
    
    def __init__(self, config_db: Session, query_engine: "QueryEngine" = None):
        self.config_db = config_db
        self.query_engine = query_engine
        self.dao = CalculationDAO(config_db)
    
    async def get_available_calculations(self, group_level: Optional[str] = None) -> List[CalculationResponse]:
        """Get list of available calculations, optionally filtered by group level"""
        group_level_enum = GroupLevel(group_level) if group_level else None
        calculations = self.dao.get_all_calculations(group_level_enum)
        
        return [CalculationResponse.model_validate(calc) for calc in calculations]
    
    async def preview_calculation_sql(
        self,
        calc_id: int,
        aggregation_level: str = "deal",
        sample_deals: List[int] = None,
        sample_tranches: List[str] = None,
        sample_cycle: int = None
    ) -> Dict[str, Any]:
        """Generate SQL preview using unified query engine"""
        if not self.query_engine:
            raise ValueError("Query engine required for SQL preview operations")
        
        calculation = self.query_engine.get_calculation_by_id(calc_id)
        if not calculation:
            raise CalculationNotFoundError(f"Calculation with ID {calc_id} not found")
        
        return self.query_engine.preview_calculation_sql(
            calculation=calculation,
            aggregation_level=calculation.group_level,
            sample_deals=sample_deals,
            sample_tranches=sample_tranches,
            sample_cycle=sample_cycle
        )

    async def create_calculation(self, request: CalculationCreateRequest, user_id: str = "api_user") -> CalculationResponse:
        """Create a new calculation"""
        # Check if calculation name already exists at this group level
        existing = self.dao.get_by_name_and_group_level(request.name, request.group_level)
        if existing:
            raise CalculationAlreadyExistsError(f"Calculation with name '{request.name}' already exists at {request.group_level} level")
        
        # Validate weighted average has weight field
        if request.aggregation_function == AggregationFunction.WEIGHTED_AVG and not request.weight_field:
            raise InvalidCalculationError("Weighted average calculations require a weight_field")
        
        # Create new calculation
        calculation = Calculation(
            name=request.name,
            description=request.description,
            aggregation_function=request.aggregation_function,
            source_model=request.source_model,
            source_field=request.source_field,
            group_level=request.group_level,
            weight_field=request.weight_field,
            created_by=user_id
        )
        
        calculation = self.dao.create(calculation)
        return CalculationResponse.model_validate(calculation)
    
    async def update_calculation(self, calc_id: int, request: CalculationCreateRequest) -> CalculationResponse:
        """Update an existing calculation"""
        calculation = self.dao.get_by_id(calc_id)
        if not calculation:
            raise CalculationNotFoundError(f"Calculation with ID {calc_id} not found")
        
        # Check if another calculation with the same name exists at this group level (excluding current one)
        existing = self.dao.get_by_name_and_group_level(request.name, request.group_level)
        if existing and existing.id != calc_id:
            raise CalculationAlreadyExistsError(f"Another calculation with name '{request.name}' already exists at {request.group_level} level")
        
        # Validate weighted average has weight field
        if request.aggregation_function == AggregationFunction.WEIGHTED_AVG and not request.weight_field:
            raise InvalidCalculationError("Weighted average calculations require a weight_field")
        
        # Update fields
        calculation.name = request.name
        calculation.description = request.description
        calculation.aggregation_function = request.aggregation_function
        calculation.source_model = request.source_model
        calculation.source_field = request.source_field
        calculation.group_level = request.group_level
        calculation.weight_field = request.weight_field
        
        calculation = self.dao.update(calculation)
        return CalculationResponse.model_validate(calculation)
    
    def get_calculation_usage_in_reports(self, calc_id: int) -> List[Dict[str, Any]]:
        """Get list of reports that are using this calculation"""
        from app.reporting.models import Report, ReportCalculation
        
        # Query for reports using this calculation
        reports_using_calc = (
            self.config_db.query(Report, ReportCalculation)
            .join(ReportCalculation, Report.id == ReportCalculation.report_id)
            .filter(ReportCalculation.calculation_id == calc_id)
            .filter(Report.is_active == True)
            .all()
        )
        
        return [
            {
                "report_id": report.id,
                "report_name": report.name,
                "report_description": report.description,
                "scope": report.scope,
                "created_by": report.created_by,
                "created_date": report.created_date.isoformat() if report.created_date else None,
                "display_order": report_calc.display_order,
                "display_name": report_calc.display_name
            }
            for report, report_calc in reports_using_calc
        ]
    
    async def delete_calculation(self, calc_id: int) -> dict:
        """Delete a calculation (soft delete) - only if not used in any reports"""
        calculation = self.dao.get_by_id(calc_id)
        if not calculation:
            raise CalculationNotFoundError(f"Calculation with ID {calc_id} not found")
        
        # Check if calculation is being used in any reports
        reports_using_calc = self.get_calculation_usage_in_reports(calc_id)
        if reports_using_calc:
            report_names = [report["report_name"] for report in reports_using_calc]
            raise InvalidCalculationError(
                f"Cannot delete calculation '{calculation.name}' because it is currently being used in the following report templates: {', '.join(report_names)}. "
                f"Please remove the calculation from these reports before deleting it."
            )
        
        self.dao.soft_delete(calculation)
        return {"message": f"Calculation '{calculation.name}' deleted successfully"}