# app/features/calculations/service.py
"""Refactored calculation service using unified query engine"""

from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from app.core.exceptions import CalculationNotFoundError, CalculationAlreadyExistsError, InvalidCalculationError

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from app.shared.query_engine import QueryEngine

from .repository import CalculationRepository
from .models import Calculation, AggregationFunction, SourceModel, GroupLevel
from .schemas import CalculationCreateRequest, CalculationResponse

class CalculationService:
    """Streamlined calculation service using unified query engine"""
    
    def __init__(self, config_db: Session, query_engine: "QueryEngine" = None):
        self.config_db = config_db
        self.query_engine = query_engine
        self.repository = CalculationRepository(config_db)
    
    async def get_available_calculations(self, group_level: Optional[str] = None) -> List[CalculationResponse]:
        """Get list of available calculations, optionally filtered by group level"""
        group_level_enum = GroupLevel(group_level) if group_level else None
        calculations = self.repository.get_all_calculations(group_level_enum)
        
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
        # Check if calculation name already exists
        existing = self.repository.get_by_name(request.name)
        if existing:
            raise CalculationAlreadyExistsError(f"Calculation with name '{request.name}' already exists")
        
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
        
        calculation = self.repository.create(calculation)
        return CalculationResponse.model_validate(calculation)
    
    async def update_calculation(self, calc_id: int, request: CalculationCreateRequest) -> CalculationResponse:
        """Update an existing calculation"""
        calculation = self.repository.get_by_id(calc_id)
        if not calculation:
            raise CalculationNotFoundError(f"Calculation with ID {calc_id} not found")
        
        # Validate weighted average has weight field
        if request.aggregation_function == AggregationFunction.WEIGHTED_AVG and not request.weight_field:
            raise InvalidCalculationError("Weighted average calculations require a weight_field")
        
        # Update fields
        calculation.description = request.description
        calculation.aggregation_function = request.aggregation_function
        calculation.source_model = request.source_model
        calculation.source_field = request.source_field
        calculation.group_level = request.group_level
        calculation.weight_field = request.weight_field
        
        calculation = self.repository.update(calculation)
        return CalculationResponse.model_validate(calculation)
    
    async def delete_calculation(self, calc_id: int) -> dict:
        """Delete a calculation (soft delete)"""
        calculation = self.repository.get_by_id(calc_id)
        if not calculation:
            raise CalculationNotFoundError(f"Calculation with ID {calc_id} not found")
        
        self.repository.soft_delete(calculation)
        return {"message": f"Calculation '{calculation.name}' deleted successfully"}