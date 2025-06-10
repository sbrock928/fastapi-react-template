"""
Query module for the reporting system.

This module provides the core query building functionality with a focus on:
- Type safety and clear interfaces
- Guaranteed identical code paths for preview and execution
- Extensibility for future table relationships and calculation types
- Clean separation of concerns

Main Components:
- QueryBuilder: Core class for building SQL queries
- QueryEngine: Unified interface for query operations
- Schemas: Type definitions and data structures
- Field definitions and table relationships
"""

from .builder import QueryBuilder
from .engine import QueryEngine
from .schemas import (
    # Core types
    QueryParameters,
    QueryResult,
    PreviewResult,
    # Field and calculation definitions
    FieldDefinition,
    CalculationDefinition,
    DealTrancheFilter,
    TableRelationship,
    # Enums
    AggregationFunction,
    FieldType,
    AggregationLevel,
)

__all__ = [
    # Main classes
    "QueryBuilder",
    "QueryEngine",
    # Core parameter and result types
    "QueryParameters",
    "QueryResult",
    "PreviewResult",
    # Definition types
    "FieldDefinition",
    "CalculationDefinition",
    "DealTrancheFilter",
    "TableRelationship",
    # Enums
    "AggregationFunction",
    "FieldType",
    "AggregationLevel",
]
