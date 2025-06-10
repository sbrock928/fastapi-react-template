# app/calculations/models.py
"""Updated calculation models supporting User Defined and System Defined calculations."""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, validates
from sqlalchemy.sql import func
from app.core.database import Base
import enum
from typing import Optional

class CalculationType(str, enum.Enum):
    """Types of calculations supported by the system."""
    USER_DEFINED = "USER_DEFINED"      # User-created aggregated calculations
    SYSTEM_FIELD = "SYSTEM_FIELD"      # System-generated field selections
    SYSTEM_SQL = "SYSTEM_SQL"          # System-defined custom SQL calculations

class AggregationFunction(str, enum.Enum):
    """Available aggregation functions for USER_DEFINED calculations only."""
    SUM = "SUM"
    AVG = "AVG"
    COUNT = "COUNT"
    MIN = "MIN"
    MAX = "MAX"
    WEIGHTED_AVG = "WEIGHTED_AVG"
    # NOTE: Removed RAW - now handled by SYSTEM_FIELD type

class SourceModel(str, enum.Enum):
    """Available source models for calculations."""
    DEAL = "Deal"
    TRANCHE = "Tranche"
    TRANCHE_BAL = "TrancheBal"

class GroupLevel(str, enum.Enum):
    """Aggregation levels."""
    DEAL = "deal"
    TRANCHE = "tranche"

class Calculation(Base):
    """Enhanced calculation model supporting multiple calculation types."""
    __tablename__ = "calculations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Core calculation type and definition
    calculation_type: Mapped[CalculationType] = mapped_column(SQLEnum(CalculationType), nullable=False, index=True)
    group_level: Mapped[GroupLevel] = mapped_column(SQLEnum(GroupLevel), nullable=False)
    
    # For USER_DEFINED calculations
    aggregation_function: Mapped[Optional[AggregationFunction]] = mapped_column(SQLEnum(AggregationFunction), nullable=True)
    source_model: Mapped[Optional[SourceModel]] = mapped_column(SQLEnum(SourceModel), nullable=True)
    source_field: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    weight_field: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # For SYSTEM_FIELD calculations
    field_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    field_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 'string', 'number', 'currency', etc.
    
    # For SYSTEM_SQL calculations
    raw_sql: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_column_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # System management
    is_system_managed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by: Mapped[str] = mapped_column(String(100), nullable=True)

    # Unique constraints
    __table_args__ = (
        UniqueConstraint('name', 'group_level', 'is_active', name='uq_calculation_name_group_level_active'),
    )

    @validates('calculation_type', 'aggregation_function', 'source_model', 'source_field', 'field_name', 'raw_sql')
    def validate_calculation_fields(self, key, value):
        """Validate that required fields are present based on calculation type."""
        # This is a basic validation - more complex validation will be in the service layer
        if key == 'calculation_type' and value:
            # Validation will be handled in service layer for complex cross-field validation
            pass
        return value

    def is_user_defined(self) -> bool:
        """Check if this is a user-defined calculation."""
        return self.calculation_type == CalculationType.USER_DEFINED

    def is_system_field(self) -> bool:
        """Check if this is a system field calculation."""
        return self.calculation_type == CalculationType.SYSTEM_FIELD

    def is_system_sql(self) -> bool:
        """Check if this is a system SQL calculation."""
        return self.calculation_type == CalculationType.SYSTEM_SQL

    def is_editable(self) -> bool:
        """Check if this calculation can be edited by users."""
        return not self.is_system_managed

    def get_required_models(self):
        """Get the models required for this calculation."""
        from app.datawarehouse.models import Deal, Tranche, TrancheBal
        
        models = [Deal]  # Always need Deal as the base
        
        if self.is_user_defined():
            # For user-defined calculations, use source_model
            if self.source_model in [SourceModel.TRANCHE, SourceModel.TRANCHE_BAL]:
                models.append(Tranche)
            if self.source_model == SourceModel.TRANCHE_BAL:
                models.append(TrancheBal)
        
        elif self.is_system_field():
            # For system field calculations, determine based on source_model
            if self.source_model in [SourceModel.TRANCHE, SourceModel.TRANCHE_BAL]:
                models.append(Tranche)
            if self.source_model == SourceModel.TRANCHE_BAL:
                models.append(TrancheBal)
        
        elif self.is_system_sql():
            # For system SQL calculations, we need to determine from the SQL
            # This will be handled in the query engine based on SQL analysis
            # For now, include all models to be safe
            models.extend([Tranche, TrancheBal])
        
        return models

    def get_display_type(self) -> str:
        """Get human-readable display type."""
        if self.is_user_defined():
            return f"User Defined ({self.aggregation_function.value})"
        elif self.is_system_field():
            return f"System Field ({self.field_type or 'Unknown'})"
        elif self.is_system_sql():
            return "System SQL"
        return "Unknown"

    def get_source_description(self) -> str:
        """Get source description for display."""
        if self.is_user_defined():
            return f"{self.source_model.value}.{self.source_field}"
        elif self.is_system_field():
            return f"{self.source_model.value}.{self.field_name}"
        elif self.is_system_sql():
            return f"Custom SQL ({self.result_column_name})"
        return "Unknown"

    def __repr__(self):
        return f"<Calculation(id={self.id}, name='{self.name}', type='{self.calculation_type}', level='{self.group_level}')>"