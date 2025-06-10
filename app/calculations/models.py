# app/calculations/models.py
"""Simplified database models for calculations."""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class AggregationFunction(str, enum.Enum):
    """Available aggregation functions."""
    SUM = "SUM"
    AVG = "AVG"
    COUNT = "COUNT"
    MIN = "MIN"
    MAX = "MAX"
    WEIGHTED_AVG = "WEIGHTED_AVG"
    RAW = "RAW"  # For non-aggregated fields

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
    """Simplified calculation definitions."""
    __tablename__ = "calculations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Core calculation definition
    aggregation_function: Mapped[AggregationFunction] = mapped_column(SQLEnum(AggregationFunction), nullable=False)
    source_model: Mapped[SourceModel] = mapped_column(SQLEnum(SourceModel), nullable=False)
    source_field: Mapped[str] = mapped_column(String(100), nullable=False)
    group_level: Mapped[GroupLevel] = mapped_column(SQLEnum(GroupLevel), nullable=False)
    
    # For weighted averages
    weight_field: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # Metadata
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by: Mapped[str] = mapped_column(String(100), nullable=True)

    # Unique constraint for name + group_level + active status
    __table_args__ = (
        UniqueConstraint('name', 'group_level', 'is_active', name='uq_calculation_name_group_level_active'),
    )

    def is_raw_field(self) -> bool:
        """Check if this is a raw (non-aggregated) field."""
        return self.aggregation_function == AggregationFunction.RAW

    def get_required_models(self):
        """Get the models required for this calculation."""
        from app.datawarehouse.models import Deal, Tranche, TrancheBal
        
        models = [Deal]  # Always need Deal as the base
        
        if self.source_model in [SourceModel.TRANCHE, SourceModel.TRANCHE_BAL]:
            models.append(Tranche)
        
        if self.source_model == SourceModel.TRANCHE_BAL:
            models.append(TrancheBal)
        
        return models

    def __repr__(self):
        return f"<Calculation(id={self.id}, name='{self.name}', function='{self.aggregation_function}', model='{self.source_model}')>"