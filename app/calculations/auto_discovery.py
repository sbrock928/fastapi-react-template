# app/calculations/models.py
"""New separated calculation models with smart auto-discovery - User calculations vs System calculations"""

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
    inspect,
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


# ===== SMART FIELD DISCOVERY SYSTEM =====

class SmartFieldDiscovery:
    """Smart field discovery with minimal manual configuration"""
    
    def __init__(self):
        # Import here to avoid circular imports
        try:
            from app.datawarehouse.models import Deal, Tranche, TrancheBal
            self.models = {"Deal": Deal, "Tranche": Tranche, "TrancheBal": TrancheBal}
        except ImportError:
            # Fallback if datawarehouse models aren't available yet
            self.models = {}
        
        # Only specify overrides for fields that need special handling
        self.field_overrides = {
            # Critical business fields that need perfect descriptions
            "deal.dl_nbr": {
                "name": "Deal Number",
                "description": "Unique identifier for the deal",
                "type": "number"
            },
            "deal.issr_cde": {
                "name": "Issuer Code", 
                "description": "Deal issuer code",
                "type": "string"
            },
            "deal.cdi_file_nme": {
                "name": "CDI File Name",
                "description": "CDI file name",
                "type": "string"
            },
            "deal.CDB_cdi_file_nme": {
                "name": "CDB CDI File Name",
                "description": "CDB CDI file name",
                "type": "string"
            },
            "tranche.tr_id": {
                "name": "Tranche ID", 
                "description": "Tranche identifier within the deal",
                "type": "string"
            },
            "tranche.tr_cusip_id": {
                "name": "Tranche CUSIP ID",
                "description": "CUSIP identifier for the tranche",
                "type": "string"
            },
            "tranchebal.tr_end_bal_amt": {
                "name": "Ending Balance Amount",
                "description": "Outstanding principal balance at period end",
                "type": "currency"
            },
            "tranchebal.tr_pass_thru_rte": {
                "name": "Pass Through Rate",
                "description": "Interest rate passed through to investors", 
                "type": "percentage"
            },
            "tranchebal.cycle_cde": {
                "name": "Cycle Code",
                "description": "Reporting cycle identifier (YYYYMM format)",
                "type": "number"
            },
            "tranchebal.tr_prin_rel_ls_amt": {
                "name": "Principal Released Amount",
                "description": "Principal released or lost during the period",
                "type": "currency"
            },
            "tranchebal.tr_accrl_days": {
                "name": "Accrual Days",
                "description": "Number of days in the accrual period",
                "type": "number"
            },
            "tranchebal.tr_int_dstrb_amt": {
                "name": "Interest Distribution Amount",
                "description": "Interest distributed to investors",
                "type": "currency"
            },
            "tranchebal.tr_prin_dstrb_amt": {
                "name": "Principal Distribution Amount", 
                "description": "Principal distributed to investors",
                "type": "currency"
            },
            "tranchebal.tr_int_accrl_amt": {
                "name": "Interest Accrual Amount",
                "description": "Interest accrued during the period",
                "type": "currency"
            },
            "tranchebal.tr_int_shtfl_amt": {
                "name": "Interest Shortfall Amount",
                "description": "Interest shortfall amount",
                "type": "currency"
            }
            # Add more only as needed - most fields will be auto-discovered
        }
        
        # Fields to exclude from auto-discovery
        self.excluded_fields = {
            "created_at", "updated_at", "deleted_at", "version", 
            "internal_notes", "temp_field", "password", "secret", "key", "token"
        }
    
    def get_all_fields(self) -> Dict[str, Dict[str, Any]]:
        """Get all fields using smart discovery"""
        all_fields = {}
        
        for model_name, model_class in self.models.items():
            try:
                inspector = inspect(model_class)
                
                for column_name, column in inspector.columns.items():
                    if column_name in self.excluded_fields:
                        continue
                        
                    field_path = f"{model_name.lower()}.{column_name}"
                    
                    # Use override if available, otherwise auto-generate
                    if field_path in self.field_overrides:
                        field_info = self.field_overrides[field_path].copy()
                        field_info.setdefault("required_models", self._get_required_models(model_name))
                        field_info.setdefault("nullable", column.nullable)
                    else:
                        field_info = self._auto_generate_field_info(column_name, column, model_name)
                    
                    all_fields[field_path] = field_info
            except Exception as e:
                print(f"Warning: Could not inspect model {model_name}: {e}")
                continue
        
        return all_fields
    
    def _auto_generate_field_info(self, column_name: str, column, model_name: str) -> Dict[str, Any]:
        """Auto-generate field info using smart patterns"""
        return {
            "name": self._smart_display_name(column_name),
            "description": self._smart_description(column_name, model_name),
            "type": self._smart_field_type(column_name, column),
            "required_models": self._get_required_models(model_name),
            "nullable": column.nullable
        }
    
    def _smart_display_name(self, column_name: str) -> str:
        """Generate smart display names"""
        # Common abbreviations in your domain
        replacements = {
            "_nbr": " Number", "_cde": " Code", "_nme": " Name", "_amt": " Amount",
            "_rte": " Rate", "_bal": " Balance", "_dstrb": " Distribution",
            "_accrl": " Accrual", "_prin": " Principal", "_int": " Interest",
            "_shtfl": " Shortfall", "_id": " ID", "tr_": "Tranche ", "dl_": "Deal ",
            "_pct": " Percent", "_dt": " Date", "_tm": " Time"
        }
        
        display_name = column_name
        for abbrev, full in replacements.items():
            display_name = display_name.replace(abbrev, full)
        
        return " ".join(word.capitalize() for word in display_name.replace("_", " ").split())
    
    def _smart_description(self, column_name: str, model_name: str) -> str:
        """Generate smart descriptions based on patterns"""
        base_name = self._smart_display_name(column_name).lower()
        
        if "_amt" in column_name:
            return f"Monetary amount for {base_name}"
        elif "_rte" in column_name:
            return f"Rate value for {base_name}"
        elif "_cde" in column_name:
            return f"Code identifier for {base_name}"
        elif "_nbr" in column_name or "_id" in column_name:
            return f"Unique identifier for {base_name}"
        elif "_bal" in column_name:
            return f"Balance amount for {base_name}"
        elif "date" in column_name.lower() or "_dt" in column_name:
            return f"Date of {base_name}"
        elif "_dstrb" in column_name:
            return f"Distribution amount for {base_name}"
        elif "_accrl" in column_name:
            return f"Accrual amount for {base_name}"
        else:
            return f"{self._smart_display_name(column_name)} from {model_name}"
    
    def _smart_field_type(self, column_name: str, column) -> str:
        """Determine field type using smart patterns"""
        # Pattern-based detection (most specific first)
        if "_amt" in column_name or "_bal" in column_name:
            return "currency"
        elif "_rte" in column_name or "_pct" in column_name:
            return "percentage"
        elif "date" in column_name.lower() or "_dt" in column_name:
            return "date"
        elif "time" in column_name.lower() or "_tm" in column_name:
            return "time"
        elif "_nbr" in column_name or "_id" in column_name or column_name == "cycle_cde":
            return "number"
        
        # SQLAlchemy type fallback
        sqlalchemy_type = column.type.__class__.__name__
        type_mapping = {
            "Integer": "number", "BigInteger": "number", "SmallInteger": "number",
            "String": "string", "CHAR": "string", "Text": "string",
            "Float": "number", "Numeric": "currency", "DECIMAL": "currency",
            "Boolean": "boolean", "DateTime": "datetime", "Date": "date", "Time": "time"
        }
        return type_mapping.get(sqlalchemy_type, "string")
    
    def _get_required_models(self, model_name: str) -> List[str]:
        """Get required models for joins"""
        if model_name == "Deal":
            return ["Deal"]
        elif model_name == "Tranche":
            return ["Deal", "Tranche"]
        elif model_name == "TrancheBal":
            return ["Deal", "Tranche", "TrancheBal"]
        return [model_name]


# Create global instance
_field_discovery = SmartFieldDiscovery()


# ===== PUBLIC API FUNCTIONS =====

def get_static_field_info(field_path: str) -> Dict[str, Any]:
    """Get metadata about a static field using smart discovery."""
    all_fields = _field_discovery.get_all_fields()
    return all_fields.get(field_path, {
        "name": field_path,
        "description": f"Field {field_path}",
        "type": "unknown",
        "required_models": [],
        "nullable": True
    })


def get_all_static_fields() -> Dict[str, Dict[str, Any]]:
    """Get all available static fields using smart discovery."""
    return _field_discovery.get_all_fields()


# ===== CONVENIENCE FUNCTIONS =====

def add_field_override(field_path: str, field_info: Dict[str, Any]):
    """Add custom field information for specific fields"""
    _field_discovery.field_overrides[field_path] = field_info


def exclude_field(field_name: str):
    """Exclude a field from auto-discovery"""
    _field_discovery.excluded_fields.add(field_name)


def get_fields_for_model(model_name: str) -> Dict[str, Dict[str, Any]]:
    """Get all fields for a specific model"""
    all_fields = get_all_static_fields()
    prefix = f"{model_name.lower()}."
    return {path: info for path, info in all_fields.items() if path.startswith(prefix)}


def refresh_field_discovery():
    """Refresh the field discovery (call after model changes)"""
    global _field_discovery
    _field_discovery = SmartFieldDiscovery()


# ===== MIGRATION HELPER FUNCTION =====

def compare_with_old_registry():
    """Helper to compare auto-discovered fields with old manual registry (for testing)"""
    auto_fields = get_all_static_fields()
    
    print("=== AUTO-DISCOVERED FIELDS ===")
    for path, info in sorted(auto_fields.items()):
        print(f"{path}: {info['name']} ({info['type']})")
    
    print(f"\nTotal auto-discovered fields: {len(auto_fields)}")
    
    # Show fields by model
    for model_name in ["Deal", "Tranche", "TrancheBal"]:
        model_fields = get_fields_for_model(model_name)
        print(f"\n{model_name} fields: {len(model_fields)}")
        for path, info in sorted(model_fields.items()):
            print(f"  {path}: {info['name']}")


# Note: The old STATIC_FIELD_REGISTRY has been completely replaced by the smart auto-discovery system above!
# You can delete any remaining references to the old manual registry.