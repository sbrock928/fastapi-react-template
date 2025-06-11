# app/calculations/models.py
"""New separated calculation models - User calculations vs System calculations"""

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
from typing import Optional, List, Dict, Any


class AggregationFunction(str, enum.Enum):
    """Available aggregation functions for user-defined calculations."""
    SUM = "SUM"
    AVG = "AVG"
    COUNT = "COUNT"
    MIN = "MIN"
    MAX = "MAX"
    WEIGHTED_AVG = "WEIGHTED_AVG"


class SourceModel(str, enum.Enum):
    """Available source models for calculations."""
    DEAL = "Deal"
    TRANCHE = "Tranche"
    TRANCHE_BAL = "TrancheBal"


class GroupLevel(str, enum.Enum):
    """Aggregation levels."""
    DEAL = "deal"
    TRANCHE = "tranche"


class UserCalculation(Base):
    """
    User-defined calculations with 'training wheels' - expandable via JSON config.
    
    These are simple aggregations (SUM, AVG, etc.) that users can create through the UI.
    Future expansion happens through the advanced_config JSON field without schema migrations.
    """
    __tablename__ = "user_calculations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Core aggregation definition (current functionality)
    aggregation_function: Mapped[AggregationFunction] = mapped_column(
        SQLEnum(AggregationFunction), nullable=False
    )
    source_model: Mapped[SourceModel] = mapped_column(SQLEnum(SourceModel), nullable=False)
    source_field: Mapped[str] = mapped_column(String(100), nullable=False)
    weight_field: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # For WEIGHTED_AVG
    group_level: Mapped[GroupLevel] = mapped_column(SQLEnum(GroupLevel), nullable=False)

    # Future expansion without schema migrations
    advanced_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    # Example future configs:
    # {
    #   "filters": [{"field": "deal.issr_cde", "operator": "=", "value": "FHLMC"}],
    #   "conditions": [{"field": "tr_end_bal_amt", "operator": ">", "value": 1000000}],
    #   "custom_aggregation_window": {"type": "rolling", "periods": 3},
    #   "calculated_fields": [{"name": "ratio", "formula": "field_a / field_b"}]
    # }

    # Security and governance (added for consistency with system calculations)
    # TODO: Implement proper approval workflow - for now auto-approving
    approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    approval_date: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Metadata
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "name", "group_level", "is_active", name="uq_user_calc_name_group_level_active"
        ),
    )

    @validates("weight_field")
    def validate_weight_field_for_weighted_avg(self, key, value):
        """Validate weight field is provided for weighted averages."""
        if self.aggregation_function == AggregationFunction.WEIGHTED_AVG and not value:
            raise ValueError("weight_field is required for weighted average calculations")
        return value

    def get_required_models(self) -> List[str]:
        """Get the models required for this calculation."""
        if self.source_model == SourceModel.DEAL:
            return ["Deal"]
        elif self.source_model == SourceModel.TRANCHE:
            return ["Deal", "Tranche"]
        elif self.source_model == SourceModel.TRANCHE_BAL:
            return ["Deal", "Tranche", "TrancheBal"]
        return ["Deal"]

    def has_advanced_features(self) -> bool:
        """Check if this calculation uses advanced features."""
        return bool(self.advanced_config)

    def is_approved(self) -> bool:
        """Check if this calculation has been approved."""
        return self.approved_by is not None and self.approval_date is not None

    def get_display_name(self) -> str:
        """Get display name for UI."""
        return f"{self.aggregation_function.value}({self.source_model.value}.{self.source_field})"

    def __repr__(self):
        return f"<UserCalculation(id={self.id}, name='{self.name}', function='{self.aggregation_function}')>"


class SystemCalculation(Base):
    """
    System-defined calculations using raw SQL for advanced users.
    
    These are complex calculations that require custom SQL logic.
    They go through approval workflows and can reference other calculations.
    """
    __tablename__ = "system_calculations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # SQL definition
    raw_sql: Mapped[str] = mapped_column(Text, nullable=False)
    result_column_name: Mapped[str] = mapped_column(String(100), nullable=False)
    group_level: Mapped[GroupLevel] = mapped_column(SQLEnum(GroupLevel), nullable=False)

    # Metadata for dependency tracking and optimization
    metadata_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    # Example metadata:
    # {
    #   "required_models": ["Deal", "Tranche", "TrancheBal"],
    #   "performance_hints": {"estimated_rows": 1000, "complexity": "medium"},
    #   "dependencies": ["user_calc_1", "system_calc_2"],
    #   "validation_rules": ["must_include_dl_nbr", "must_include_tr_id_for_tranche_level"],
    #   "cache_settings": {"ttl_minutes": 60, "cache_key_fields": ["cycle_code"]}
    # }

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
            "name", "group_level", "is_active", name="uq_system_calc_name_group_level_active"
        ),
    )

    @validates("raw_sql")
    def validate_sql_not_empty(self, key, value):
        """Validate SQL is not empty."""
        if not value or not value.strip():
            raise ValueError("raw_sql cannot be empty")
        return value.strip()

    @validates("result_column_name")
    def validate_result_column_name(self, key, value):
        """Validate result column name format."""
        if not value or not value.strip():
            raise ValueError("result_column_name cannot be empty")
        
        import re
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", value.strip()):
            raise ValueError(
                "result_column_name must be a valid identifier (letters, numbers, underscores)"
            )
        return value.strip()

    def get_required_models(self) -> List[str]:
        """Get required models from metadata or default to all."""
        if self.metadata_config and "required_models" in self.metadata_config:
            return self.metadata_config["required_models"]
        # Default to all models for system calculations
        return ["Deal", "Tranche", "TrancheBal"]

    def is_approved(self) -> bool:
        """Check if this calculation has been approved."""
        return self.approved_by is not None and self.approval_date is not None

    def get_dependencies(self) -> List[str]:
        """Get list of calculation dependencies."""
        if self.metadata_config and "dependencies" in self.metadata_config:
            return self.metadata_config["dependencies"]
        return []

    def get_performance_complexity(self) -> str:
        """Get performance complexity hint."""
        if self.metadata_config and "performance_hints" in self.metadata_config:
            return self.metadata_config["performance_hints"].get("complexity", "unknown")
        return "unknown"

    def __repr__(self):
        return f"<SystemCalculation(id={self.id}, name='{self.name}', approved={self.is_approved()})>"


# Static field definitions (no database storage needed)
STATIC_FIELD_REGISTRY = {
    "deal.dl_nbr": {
        "name": "Deal Number",
        "description": "Unique identifier for the deal",
        "type": "number",
        "required_models": ["Deal"],
        "nullable": False
    },
    "deal.issr_cde": {
        "name": "Issuer Code", 
        "description": "Deal issuer code",
        "type": "string",
        "required_models": ["Deal"],
        "nullable": True
    },
    "deal.cdi_file_nme": {
        "name": "CDI File Name",
        "description": "CDI file name",
        "type": "string", 
        "required_models": ["Deal"],
        "nullable": True
    },
    "deal.CDB_cdi_file_nme": {
        "name": "CDB CDI File Name",
        "description": "CDB CDI file name",
        "type": "string",
        "required_models": ["Deal"], 
        "nullable": True
    },
    "tranche.tr_id": {
        "name": "Tranche ID",
        "description": "Tranche identifier within the deal",
        "type": "string",
        "required_models": ["Deal", "Tranche"],
        "nullable": False
    },
    "tranche.tr_cusip_id": {
        "name": "Tranche CUSIP ID",
        "description": "CUSIP identifier for the tranche",
        "type": "string",
        "required_models": ["Deal", "Tranche"],
        "nullable": True
    },
    "tranchebal.tr_end_bal_amt": {
        "name": "Ending Balance Amount",
        "description": "Outstanding principal balance at period end",
        "type": "currency",
        "required_models": ["Deal", "Tranche", "TrancheBal"],
        "nullable": True
    },
    "tranchebal.tr_pass_thru_rte": {
        "name": "Pass Through Rate",
        "description": "Interest rate passed through to investors",
        "type": "percentage",
        "required_models": ["Deal", "Tranche", "TrancheBal"],
        "nullable": True
    },
    "tranchebal.cycle_cde": {
        "name": "Cycle Code",
        "description": "Reporting cycle identifier (YYYYMM format)",
        "type": "number",
        "required_models": ["Deal", "Tranche", "TrancheBal"],
        "nullable": False
    },
    "tranchebal.tr_prin_rel_ls_amt": {
        "name": "Principal Released Amount",
        "description": "Principal released or lost during the period",
        "type": "currency",
        "required_models": ["Deal", "Tranche", "TrancheBal"],
        "nullable": True
    },
    "tranchebal.tr_accrl_days": {
        "name": "Accrual Days",
        "description": "Number of days in the accrual period",
        "type": "number",
        "required_models": ["Deal", "Tranche", "TrancheBal"],
        "nullable": True
    },
    "tranchebal.tr_int_dstrb_amt": {
        "name": "Interest Distribution Amount",
        "description": "Interest distributed to investors",
        "type": "currency",
        "required_models": ["Deal", "Tranche", "TrancheBal"],
        "nullable": True
    },
    "tranchebal.tr_prin_dstrb_amt": {
        "name": "Principal Distribution Amount", 
        "description": "Principal distributed to investors",
        "type": "currency",
        "required_models": ["Deal", "Tranche", "TrancheBal"],
        "nullable": True
    },
    "tranchebal.tr_int_accrl_amt": {
        "name": "Interest Accrual Amount",
        "description": "Interest accrued during the period",
        "type": "currency",
        "required_models": ["Deal", "Tranche", "TrancheBal"],
        "nullable": True
    },
    "tranchebal.tr_int_shtfl_amt": {
        "name": "Interest Shortfall Amount",
        "description": "Interest shortfall amount",
        "type": "currency",
        "required_models": ["Deal", "Tranche", "TrancheBal"],
        "nullable": True
    },
}

def get_static_field_info(field_path: str) -> Dict[str, Any]:
    """Get metadata about a static field."""
    return STATIC_FIELD_REGISTRY.get(field_path, {
        "name": field_path,
        "description": f"Field {field_path}",
        "type": "unknown",
        "required_models": [],
        "nullable": True
    })

def get_all_static_fields() -> Dict[str, Dict[str, Any]]:
    """Get all available static fields."""
    return STATIC_FIELD_REGISTRY.copy()