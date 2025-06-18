# app/calculations/__init__.py
"""Calculations feature - unified calculation system with dynamic SQL parameter injection"""

from .models import Calculation, CalculationType, AggregationFunction, SourceModel, GroupLevel
from .schemas import (
    UserAggregationCalculationCreate,
    SystemFieldCalculationCreate, 
    SystemSqlCalculationCreate,
    CDIVariableCalculationCreate,
    CalculationUpdate,
    CalculationResponse,
    CalculationPreviewRequest,
    CalculationPreviewResponse,
    SqlValidationRequest,
    SqlValidationResponse,
    ReportExecutionRequest,
    ReportExecutionResponse,
    LegacyCalculationCreate
)
from .service import UnifiedCalculationService
from .resolver import EnhancedCalculationResolver, CalculationRequest, QueryFilters

# Backward compatibility aliases for existing code
UserCalculation = Calculation  # For backward compatibility
SystemCalculation = Calculation  # For backward compatibility

# Schema aliases for backward compatibility
UserCalculationCreate = UserAggregationCalculationCreate
UserCalculationUpdate = CalculationUpdate
UserCalculationResponse = CalculationResponse
SystemCalculationCreate = SystemSqlCalculationCreate
SystemCalculationResponse = CalculationResponse
StaticFieldInfo = dict  # Simple dict for now
CalculationConfigResponse = dict  # Simple dict for now
CalculationRequestSchema = dict  # Simple dict for now

# Service aliases for backward compatibility
UserCalculationService = UnifiedCalculationService
SystemCalculationService = UnifiedCalculationService
StaticFieldService = UnifiedCalculationService
CalculationConfigService = UnifiedCalculationService
ReportExecutionService = UnifiedCalculationService

# DAO aliases - these may need to be updated when DAOs are refactored
try:
    from .dao import UserCalculationDAO, SystemCalculationDAO, CalculationStatsDAO
except ImportError:
    # Fallback if DAO files don't exist yet
    UserCalculationDAO = None
    SystemCalculationDAO = None
    CalculationStatsDAO = None

# Resolver alias
UnifiedCalculationResolver = EnhancedCalculationResolver

__all__ = [
    # Models - Unified
    "Calculation",
    "CalculationType",
    "AggregationFunction",
    "SourceModel", 
    "GroupLevel",
    # Backward compatibility
    "UserCalculation",
    "SystemCalculation",
    # Schemas - New unified
    "UserAggregationCalculationCreate",
    "SystemFieldCalculationCreate",
    "SystemSqlCalculationCreate",
    "CDIVariableCalculationCreate",
    "CalculationUpdate",
    "CalculationResponse",
    "CalculationPreviewRequest",
    "CalculationPreviewResponse",
    "SqlValidationRequest",
    "SqlValidationResponse",
    "ReportExecutionRequest",
    "ReportExecutionResponse",
    "LegacyCalculationCreate",
    # Backward compatibility schemas
    "UserCalculationCreate",
    "UserCalculationUpdate", 
    "UserCalculationResponse",
    "SystemCalculationCreate",
    "SystemCalculationResponse",
    "StaticFieldInfo",
    "CalculationConfigResponse",
    "CalculationRequestSchema",
    # Services
    "UnifiedCalculationService",
    "UserCalculationService",
    "SystemCalculationService",
    "StaticFieldService", 
    "CalculationConfigService",
    "ReportExecutionService",
    # DAOs
    "UserCalculationDAO",
    "SystemCalculationDAO",
    "CalculationStatsDAO",
    # Resolver
    "EnhancedCalculationResolver",
    "UnifiedCalculationResolver",
    "CalculationRequest", 
    "QueryFilters",
]