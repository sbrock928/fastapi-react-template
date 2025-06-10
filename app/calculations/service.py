# app/calculations/service.py
"""Enhanced calculation service supporting multiple calculation types."""

from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from app.core.exceptions import CalculationNotFoundError, CalculationAlreadyExistsError, InvalidCalculationError

if TYPE_CHECKING:
    from app.query import QueryEngine

from .dao import CalculationDAO
from .models import Calculation, CalculationType, AggregationFunction, SourceModel, GroupLevel
from .schemas import (
    CalculationResponse, UserDefinedCalculationCreate, SystemSQLCalculationCreate, AvailableCalculation
)
from .sql_validator import CustomSQLValidator, SQLValidationError

class CalculationService:
    """Enhanced calculation service supporting User Defined and System Defined calculations."""
    
    def __init__(self, config_db: Session, query_engine: "QueryEngine" = None):
        self.config_db = config_db
        self.query_engine = query_engine
        self.dao = CalculationDAO(config_db)
        self.sql_validator = CustomSQLValidator()
    
    # ===== UNIFIED RETRIEVAL METHODS =====
    
    def get_available_calculations(self, group_level: Optional[str] = None, calculation_type: Optional[str] = None) -> List[AvailableCalculation]:
        """Get list of available calculations, optionally filtered by group level and/or type."""
        group_level_enum = GroupLevel(group_level) if group_level else None
        calc_type_enum = CalculationType(calculation_type) if calculation_type else None
        
        calculations = self.dao.get_all_calculations(group_level_enum, calc_type_enum)
        
        return [self._convert_to_available_calculation(calc) for calc in calculations]
    
    def get_calculation_by_id(self, calc_id: int) -> Optional[CalculationResponse]:
        """Get a single calculation by ID."""
        calculation = self.dao.get_by_id(calc_id)
        if not calculation:
            return None
        return CalculationResponse.model_validate(calculation)
    
    def get_user_defined_calculations(self, group_level: Optional[str] = None) -> List[CalculationResponse]:
        """Get only user-defined calculations."""
        return [calc for calc in self.get_available_calculations(group_level, "USER_DEFINED")]
    
    def get_system_calculations(self, group_level: Optional[str] = None) -> List[AvailableCalculation]:
        """Get only system-defined calculations (both field and SQL types)."""
        # Only return system SQL calculations since field calculations are now auto-generated
        calculations = self.dao.get_all_calculations(group_level, CalculationType.SYSTEM_SQL)
        return [self._convert_to_available_calculation(calc) for calc in calculations]
    
    # ===== USER DEFINED CALCULATION METHODS =====
    
    def create_user_defined_calculation(self, request: UserDefinedCalculationCreate, user_id: str = "api_user") -> CalculationResponse:
        """Create a new user-defined calculation."""
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
            calculation_type=CalculationType.USER_DEFINED,
            aggregation_function=request.aggregation_function,
            source_model=request.source_model,
            source_field=request.source_field,
            group_level=request.group_level,
            weight_field=request.weight_field,
            is_system_managed=False,
            created_by=user_id
        )
        
        calculation = self.dao.create(calculation)
        return CalculationResponse.model_validate(calculation)
    
    def update_user_defined_calculation(self, calc_id: int, request: UserDefinedCalculationCreate) -> CalculationResponse:
        """Update an existing user-defined calculation."""
        calculation = self.dao.get_by_id(calc_id)
        if not calculation:
            raise CalculationNotFoundError(f"Calculation with ID {calc_id} not found")
        
        if calculation.calculation_type != CalculationType.USER_DEFINED:
            raise InvalidCalculationError("Only user-defined calculations can be updated via this method")
        
        if calculation.is_system_managed:
            raise InvalidCalculationError("System-managed calculations cannot be updated by users")
        
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
    
    # ===== SYSTEM SQL CALCULATION METHODS =====
    
    def create_system_sql_calculation(self, request: SystemSQLCalculationCreate, user_id: str = "system") -> CalculationResponse:
        """Create a new system SQL calculation with validation."""
        # Check if calculation name already exists at this group level
        existing = self.dao.get_by_name_and_group_level(request.name, request.group_level)
        if existing:
            raise CalculationAlreadyExistsError(f"Calculation with name '{request.name}' already exists at {request.group_level} level")
        
        # Validate the SQL
        validation_result = self.sql_validator.validate_custom_sql(
            request.raw_sql, 
            request.group_level.value, 
            request.result_column_name
        )
        
        if not validation_result.is_valid:
            error_details = "; ".join(validation_result.errors)
            raise InvalidCalculationError(f"SQL validation failed: {error_details}")
        
        # Create new system SQL calculation
        calculation = Calculation(
            name=request.name,
            description=request.description,
            calculation_type=CalculationType.SYSTEM_SQL,
            raw_sql=request.raw_sql,
            result_column_name=request.result_column_name,
            group_level=request.group_level,
            is_system_managed=True,
            created_by=user_id
        )
        
        calculation = self.dao.create(calculation)
        return CalculationResponse.model_validate(calculation)
    
    def validate_system_sql(self, sql_text: str, group_level: str, result_column_name: str) -> Dict[str, Any]:
        """Validate system SQL without saving."""
        validation_result = self.sql_validator.validate_custom_sql(sql_text, group_level, result_column_name)
        
        return {
            "is_valid": validation_result.is_valid,
            "errors": validation_result.errors,
            "warnings": validation_result.warnings,
            "extracted_columns": validation_result.extracted_columns,
            "detected_tables": list(validation_result.detected_tables),
            "result_column_name": validation_result.result_column_name
        }
    
    # ===== COMMON METHODS =====
    
    def preview_calculation_sql(
        self,
        calc_id: int,
        aggregation_level: str = "deal",
        sample_deals: List[int] = None,
        sample_tranches: List[str] = None,
        sample_cycle: int = None
    ) -> Dict[str, Any]:
        """Generate SQL preview using query engine."""
        if not self.query_engine:
            raise ValueError("Query engine required for SQL preview operations")
        
        calculation = self.dao.get_by_id(calc_id)
        if not calculation:
            raise CalculationNotFoundError(f"Calculation with ID {calc_id} not found")
        
        # Use simplified preview method
        return self.query_engine.preview_calculation_sql(
            calculation=calculation,
            aggregation_level=aggregation_level,
            sample_deals=sample_deals or [1001, 1002, 1003],
            sample_tranches=sample_tranches or ["A", "B"],
            sample_cycle=sample_cycle or 202404
        )
    
    def get_calculation_usage_in_reports(self, calc_id: int) -> List[Dict[str, Any]]:
        """Get list of reports that are using this calculation."""
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
    
    def delete_calculation(self, calc_id: int) -> dict:
        """Delete a calculation (soft delete) - only if not used in any reports and not system-managed."""
        calculation = self.dao.get_by_id(calc_id)
        if not calculation:
            raise CalculationNotFoundError(f"Calculation with ID {calc_id} not found")
        
        # Prevent deletion of system-managed calculations
        if calculation.is_system_managed:
            raise InvalidCalculationError(f"Cannot delete system-managed calculation '{calculation.name}'. System calculations are read-only.")
        
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
    
    # ===== HELPER METHODS =====
    
    def _convert_to_available_calculation(self, calc: Calculation) -> AvailableCalculation:
        """Convert a Calculation model to AvailableCalculation schema."""
        return AvailableCalculation(
            id=calc.id,
            name=calc.name,
            description=calc.description,
            calculation_type=calc.calculation_type,
            group_level=calc.group_level,
            category=self._categorize_calculation(calc),
            is_default=calc.name in ["Deal Number", "Total Ending Balance", "Tranche ID", "Ending Balance Amount"],
            is_system_managed=calc.is_system_managed,
            display_type=calc.get_display_type(),
            source_description=calc.get_source_description()
        )
    
    def _categorize_calculation(self, calc: Calculation) -> str:
        """Categorize calculation for UI grouping."""
        if calc.is_user_defined():
            if calc.source_model == SourceModel.DEAL:
                return "Deal Information"
            elif calc.source_model == SourceModel.TRANCHE:
                return "Tranche Structure"
            elif calc.source_model == SourceModel.TRANCHE_BAL:
                if "bal" in calc.source_field.lower() or "amt" in calc.source_field.lower():
                    return "Balance & Amount Calculations"
                elif "rte" in calc.source_field.lower():
                    return "Rate Calculations"
                elif "dstrb" in calc.source_field.lower():
                    return "Distribution Calculations"
                else:
                    return "Performance Calculations"
        elif calc.is_system_field():
            if calc.source_model == SourceModel.DEAL:
                return "Deal Fields"
            elif calc.source_model == SourceModel.TRANCHE:
                return "Tranche Fields"
            elif calc.source_model == SourceModel.TRANCHE_BAL:
                return "Tranche Balance Fields"
        elif calc.is_system_sql():
            return "Custom SQL Calculations"
        
        return "Other"