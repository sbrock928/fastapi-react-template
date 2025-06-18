# app/calculations/models.py
"""Enhanced unified calculation models with dynamic SQL parameter injection"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    Enum as SQLEnum,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, validates
from sqlalchemy.sql import func
from app.core.database import Base
import enum
from typing import Optional, List, Dict, Any, Set
import re


class CalculationType(str, enum.Enum):
    """Types of calculations available in the unified system."""
    USER_AGGREGATION = "user_aggregation"    # Simple aggregations (SUM, AVG, etc.)
    SYSTEM_FIELD = "system_field"           # Raw field access
    SYSTEM_SQL = "system_sql"               # Custom SQL with placeholders


class AggregationFunction(str, enum.Enum):
    """Available aggregation functions for user-defined calculations."""
    SUM = "SUM"
    AVG = "AVG"
    COUNT = "COUNT"
    MIN = "MIN"
    MAX = "MAX"
    WEIGHTED_AVG = "WEIGHTED_AVG"
    RAW = "RAW"  # For system fields


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
    """
    Unified calculation model supporting all calculation types with dynamic SQL parameter injection.
    
    This model replaces both UserCalculation and SystemCalculation to provide a unified
    approach with support for SQL placeholders and dynamic parameter injection.
    """
    __tablename__ = "calculations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Calculation type and configuration
    calculation_type: Mapped[CalculationType] = mapped_column(SQLEnum(CalculationType), nullable=False)
    group_level: Mapped[GroupLevel] = mapped_column(SQLEnum(GroupLevel), nullable=False)
    
    # For USER_AGGREGATION type
    aggregation_function: Mapped[Optional[AggregationFunction]] = mapped_column(
        SQLEnum(AggregationFunction), nullable=True
    )
    source_model: Mapped[Optional[SourceModel]] = mapped_column(SQLEnum(SourceModel), nullable=True)
    source_field: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    weight_field: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # For SYSTEM_SQL - Enhanced SQL with placeholder support
    raw_sql: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_column_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Dynamic parameter configuration
    sql_parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    # Example sql_parameters:
    # {
    #   "placeholders_used": ["current_cycle", "previous_cycle", "deal_tranche_filter"],
    #   "custom_parameters": {
    #     "lookback_periods": 3,
    #     "threshold_amount": 1000000
    #   },
    #   "required_models": ["Deal", "Tranche", "TrancheBal"],
    #   "validation_rules": ["must_include_dl_nbr", "must_include_tr_id_for_tranche_level"]
    # }
    
    # Extended metadata for all calculation types
    metadata_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    # Example metadata for different types:
    # USER_AGGREGATION: {"performance_hints": {"estimated_rows": 1000}}
    # SYSTEM_FIELD: {"field_path": "deal.dl_nbr", "data_type": "integer"}
    # SYSTEM_SQL: {"complexity": "high", "cache_ttl": 300}

    # Security and governance
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    approval_date: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "name", "group_level", "is_active", name="uq_calc_name_group_level_active"
        ),
    )

    @validates("calculation_type", "aggregation_function", "source_model", "source_field")
    def validate_calculation_configuration(self, key, value):
        """Validate calculation configuration based on type."""
        if key == "calculation_type" and value:
            # Reset dependent fields when type changes
            return value
        
        # Skip validation if calculation_type is not set yet (during initial creation)
        if not hasattr(self, 'calculation_type') or not self.calculation_type:
            return value
            
        if self.calculation_type == CalculationType.USER_AGGREGATION:
            if key == "aggregation_function" and not value:
                raise ValueError("aggregation_function is required for USER_AGGREGATION calculations")
            if key == "source_model" and not value:
                raise ValueError("source_model is required for USER_AGGREGATION calculations")
            if key == "source_field" and not value:
                raise ValueError("source_field is required for USER_AGGREGATION calculations")
                
        elif self.calculation_type == CalculationType.SYSTEM_FIELD:
            if key == "source_field" and not value:
                raise ValueError("source_field is required for SYSTEM_FIELD calculations")
        
        return value

    @validates("raw_sql")
    def validate_sql_with_placeholders(self, key, value):
        """Enhanced SQL validation with placeholder support."""
        if not value or not value.strip():
            if hasattr(self, 'calculation_type') and self.calculation_type in [CalculationType.SYSTEM_SQL]:
                raise ValueError("raw_sql cannot be empty for SQL-based calculations")
            return value
        
        sql_trimmed = value.strip()
        
        # Check for dangerous operations
        dangerous_patterns = [
            r'\bDROP\b', r'\bDELETE\s+FROM\b', r'\bTRUNCATE\b',
            r'\bINSERT\s+INTO\b', r'\bUPDATE\s+.*\bSET\b', r'\bALTER\b',
            r'\bCREATE\b', r'\bEXEC\b', r'\bEXECUTE\b'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, sql_trimmed, re.IGNORECASE):
                raise ValueError("SQL contains dangerous operations that are not allowed")
        
        # Validate SQL structure (basic check)
        has_ctes = sql_trimmed.upper().strip().startswith('WITH')
        if not has_ctes and not sql_trimmed.lower().startswith('select'):
            raise ValueError("SQL must be a SELECT statement or start with WITH for CTEs")
        
        # Check for valid placeholders
        placeholder_pattern = r'\{([^}]+)\}'
        placeholders = re.findall(placeholder_pattern, sql_trimmed)
        valid_placeholders = self.get_available_placeholders()
        
        for placeholder in placeholders:
            if placeholder not in valid_placeholders:
                raise ValueError(f"Invalid placeholder '{{{placeholder}}}'. Valid placeholders: {list(valid_placeholders.keys())}")
        
        return sql_trimmed

    @validates("result_column_name")
    def validate_result_column_name(self, key, value):
        """Validate result column name format."""
        if not value:
            if self.calculation_type in [CalculationType.SYSTEM_SQL]:
                raise ValueError("result_column_name is required for SQL-based calculations")
            return value
        
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", value.strip()):
            raise ValueError(
                "result_column_name must be a valid identifier (letters, numbers, underscores)"
            )
        return value.strip()

    def get_available_placeholders(self) -> Dict[str, str]:
        """Get all available SQL placeholders with descriptions."""
        return {
            "current_cycle": "The selected reporting cycle code",
            "previous_cycle": "The previous reporting cycle (current_cycle - 1)",
            "cycle_minus_2": "Two cycles before current (current_cycle - 2)",
            "deal_filter": "WHERE clause for selected deal numbers",
            "tranche_filter": "WHERE clause for selected tranche IDs",
            "deal_tranche_filter": "Combined WHERE clause for deal and tranche selections",
            "deal_numbers": "Comma-separated list of selected deal numbers",
            "tranche_ids": "Comma-separated list of selected tranche IDs (quoted)",
        }

    def get_used_placeholders(self) -> Set[str]:
        """Extract placeholders used in the SQL."""
        if not self.raw_sql:
            return set()
        
        placeholder_pattern = r'\{([^}]+)\}'
        return set(re.findall(placeholder_pattern, self.raw_sql))

    def get_required_models(self) -> List[str]:
        """Get the models required for this calculation."""
        if self.calculation_type == CalculationType.USER_AGGREGATION:
            if self.source_model == SourceModel.DEAL:
                return ["Deal"]
            elif self.source_model == SourceModel.TRANCHE:
                return ["Deal", "Tranche"]
            elif self.source_model == SourceModel.TRANCHE_BAL:
                return ["Deal", "Tranche", "TrancheBal"]
        
        elif self.calculation_type == CalculationType.SYSTEM_FIELD:
            # Determine from field path
            if self.metadata_config and "field_path" in self.metadata_config:
                field_path = self.metadata_config["field_path"]
                if field_path.startswith("deal."):
                    return ["Deal"]
                elif field_path.startswith("tranche."):
                    return ["Deal", "Tranche"]
                elif field_path.startswith("tranchebal."):
                    return ["Deal", "Tranche", "TrancheBal"]
        
        elif self.calculation_type in [CalculationType.SYSTEM_SQL]:
            # Check sql_parameters or default to all models
            if self.sql_parameters and "required_models" in self.sql_parameters:
                return self.sql_parameters["required_models"]
            # Default to all models for SQL-based calculations
            return ["Deal", "Tranche", "TrancheBal"]
        
        return ["Deal"]

    def is_approved(self) -> bool:
        """Check if this calculation has been approved."""
        return self.approved_by is not None and self.approval_date is not None

    def get_complexity_score(self) -> int:
        """Get a complexity score for sorting/display purposes."""
        score = 0
        
        # Base complexity by type
        if self.calculation_type == CalculationType.SYSTEM_FIELD:
            score = 1
        elif self.calculation_type == CalculationType.USER_AGGREGATION:
            if self.aggregation_function in [AggregationFunction.SUM, AggregationFunction.COUNT]:
                score = 2
            elif self.aggregation_function == AggregationFunction.WEIGHTED_AVG:
                score = 4
            else:
                score = 3
        elif self.calculation_type in [CalculationType.SYSTEM_SQL]:
            score = 5
        
        # Add complexity for placeholders
        if self.raw_sql:
            placeholder_count = len(self.get_used_placeholders())
            score += placeholder_count
        
        # Add complexity for tranche level
        if self.group_level == GroupLevel.TRANCHE:
            score += 1
        
        return score

    def get_display_formula(self) -> str:
        """Get a display formula for the UI."""
        if self.calculation_type == CalculationType.USER_AGGREGATION:
            field = f"{self.source_model.value}.{self.source_field}" if self.source_model and self.source_field else ""
            if self.aggregation_function == AggregationFunction.WEIGHTED_AVG and self.weight_field:
                weight = f"{self.source_model.value}.{self.weight_field}"
                return f"SUM({field} * {weight}) / NULLIF(SUM({weight}), 0)"
            return f"{self.aggregation_function.value}({field})" if self.aggregation_function else ""
        
        elif self.calculation_type == CalculationType.SYSTEM_FIELD:
            field_path = self.metadata_config.get("field_path", "") if self.metadata_config else ""
            return field_path
        
        elif self.calculation_type in [CalculationType.SYSTEM_SQL]:
            return f"Custom SQL → {self.result_column_name}"
        
        return "Unknown calculation type"

    def __repr__(self):
        return f"<Calculation(id={self.id}, name='{self.name}', type='{self.calculation_type}')>"