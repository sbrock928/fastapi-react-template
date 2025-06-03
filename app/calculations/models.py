# app/calculations/models.py
"""Refactored database models for calculations using ORM functions"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class AggregationFunction(str, enum.Enum):
    """Available aggregation functions"""
    SUM = "SUM"
    AVG = "AVG"
    COUNT = "COUNT"
    MIN = "MIN"
    MAX = "MAX"
    WEIGHTED_AVG = "WEIGHTED_AVG"

class SourceModel(str, enum.Enum):
    """Available source models for calculations"""
    DEAL = "Deal"
    TRANCHE = "Tranche"
    TRANCHE_BAL = "TrancheBal"

class GroupLevel(str, enum.Enum):
    """Aggregation levels"""
    DEAL = "deal"
    TRANCHE = "tranche"

class Calculation(Base):
    """ORM-based calculation definitions"""
    __tablename__ = "calculations"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    
    # ORM-based calculation definition
    aggregation_function: Mapped[AggregationFunction] = mapped_column(SQLEnum(AggregationFunction), nullable=False)
    source_model: Mapped[SourceModel] = mapped_column(SQLEnum(SourceModel), nullable=False)
    source_field: Mapped[str] = mapped_column(String(100), nullable=False)  # Field name like 'tr_end_bal_amt'
    group_level: Mapped[GroupLevel] = mapped_column(SQLEnum(GroupLevel), nullable=False)
    
    # For weighted averages, specify the weight field
    weight_field: Mapped[str] = mapped_column(String(100), nullable=True)  # e.g., 'tr_end_bal_amt' for weighted avg
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by: Mapped[str] = mapped_column(String(100), nullable=True)

    def get_sqlalchemy_function(self):
        """Get the appropriate SQLAlchemy function for this calculation"""
        from sqlalchemy import func
        from app.datawarehouse.models import Deal, Tranche, TrancheBal
        
        # Map source model to actual SQLAlchemy model
        model_map = {
            SourceModel.DEAL: Deal,
            SourceModel.TRANCHE: Tranche,
            SourceModel.TRANCHE_BAL: TrancheBal
        }
        
        source_model_class = model_map[self.source_model]
        field = getattr(source_model_class, self.source_field)
        
        # Map aggregation function to SQLAlchemy func
        if self.aggregation_function == AggregationFunction.SUM:
            return func.sum(field)
        elif self.aggregation_function == AggregationFunction.AVG:
            return func.avg(field)
        elif self.aggregation_function == AggregationFunction.COUNT:
            return func.count(field)
        elif self.aggregation_function == AggregationFunction.MIN:
            return func.min(field)
        elif self.aggregation_function == AggregationFunction.MAX:
            return func.max(field)
        elif self.aggregation_function == AggregationFunction.WEIGHTED_AVG:
            # Weighted average: SUM(field * weight) / SUM(weight)
            if not self.weight_field:
                raise ValueError(f"Weighted average calculation '{self.name}' requires weight_field")
            weight = getattr(source_model_class, self.weight_field)
            return func.sum(field * weight) / func.nullif(func.sum(weight), 0)
        else:
            raise ValueError(f"Unsupported aggregation function: {self.aggregation_function}")

    def get_required_models(self):
        """Get the models required for this calculation"""
        from app.datawarehouse.models import Deal, Tranche, TrancheBal
        
        models = [Deal]  # Always need Deal as the base
        
        if self.source_model in [SourceModel.TRANCHE, SourceModel.TRANCHE_BAL]:
            models.append(Tranche)
        
        if self.source_model == SourceModel.TRANCHE_BAL:
            models.append(TrancheBal)
        
        return models
