"""
Query building schemas and types for the reporting system.

This module defines the core types and schemas used by the QueryBuilder
to construct SQL queries in a type-safe, extensible way.
"""

from typing import Dict, List, Optional, Union, Any, Literal
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column


class AggregationFunction(str, Enum):
    """Available aggregation functions for calculations."""

    SUM = "SUM"
    AVG = "AVG"
    COUNT = "COUNT"
    MIN = "MIN"
    MAX = "MAX"
    WEIGHTED_AVG = "WEIGHTED_AVG"


class FieldType(str, Enum):
    """Types of fields available in the query system."""

    SYSTEM = "SYSTEM"  # Raw fields defined in code, not user-modifiable
    USER_DEFINED = "USER_DEFINED"  # User-created aggregated calculations


class AggregationLevel(str, Enum):
    """Available aggregation levels for queries."""

    DEAL = "deal"
    TRANCHE = "tranche"


@dataclass(frozen=True)
class TableRelationship:
    """Defines how tables relate to each other in the query system."""

    parent_table: str
    child_table: str
    join_conditions: List[tuple[str, str]]  # (parent_field, child_field) pairs


@dataclass(frozen=True)
class FieldDefinition:
    """Defines a field that can be used in queries."""

    name: str
    table_name: str
    column_name: str
    field_type: FieldType
    data_type: str  # 'currency', 'percentage', 'number', 'string', etc.
    description: str
    is_required_for_aggregation: bool = False


@dataclass(frozen=True)
class CalculationDefinition:
    """Defines a calculation (either system field or user-defined aggregation)."""

    id: int
    name: str
    field_type: FieldType
    description: Optional[str] = None

    # For system fields (raw fields)
    source_field: Optional[FieldDefinition] = None

    # For user-defined calculations
    aggregation_function: Optional[AggregationFunction] = None
    source_table: Optional[str] = None
    source_column: Optional[str] = None
    weight_field: Optional[FieldDefinition] = None
    aggregation_level: Optional[AggregationLevel] = None

    # Future: For super-user raw SQL calculations
    raw_sql: Optional[str] = None

    def is_system_field(self) -> bool:
        """Check if this is a system field (raw field)."""
        return self.field_type == FieldType.SYSTEM

    def is_user_defined(self) -> bool:
        """Check if this is a user-defined calculation."""
        return self.field_type == FieldType.USER_DEFINED

    def requires_aggregation(self) -> bool:
        """Check if this calculation requires aggregation."""
        return self.field_type == FieldType.USER_DEFINED


@dataclass(frozen=True)
class DealTrancheFilter:
    """Defines which deals and tranches to include in a query."""

    deal_number: int
    tranche_ids: Optional[List[str]] = None  # None means all tranches for this deal

    def includes_all_tranches(self) -> bool:
        """Check if this filter includes all tranches for the deal."""
        return self.tranche_ids is None or len(self.tranche_ids) == 0


@dataclass(frozen=True)
class QueryParameters:
    """Parameters for building a query."""

    deal_tranche_filters: List[DealTrancheFilter]
    cycle_code: int
    calculations: List[CalculationDefinition]
    aggregation_level: AggregationLevel

    def get_all_deal_numbers(self) -> List[int]:
        """Get all deal numbers from the filters."""
        return [f.deal_number for f in self.deal_tranche_filters]

    def get_all_tranche_ids(self) -> List[str]:
        """Get all unique tranche IDs from the filters."""
        tranche_ids = []
        for f in self.deal_tranche_filters:
            if f.tranche_ids:
                tranche_ids.extend(f.tranche_ids)
        return list(set(tranche_ids))

    def get_deal_tranche_mapping(self) -> Dict[int, List[str]]:
        """Convert to deal-tranche mapping format."""
        return {f.deal_number: f.tranche_ids or [] for f in self.deal_tranche_filters}


@dataclass
class QueryResult:
    """Result of a query operation."""

    sql: str
    parameters: Dict[str, Any]
    columns: List[str]
    execution_metadata: Optional[Dict[str, Any]] = None


@dataclass
class PreviewResult:
    """Result of a query preview operation."""

    query_result: QueryResult
    calculation_summary: Dict[str, Any]
    performance_estimates: Optional[Dict[str, Any]] = None
