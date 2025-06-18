# app/core/dependencies.py
"""Clean dependencies for the unified calculation system"""

from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db, get_dw_db

# Core database dependencies
SessionDep = Annotated[Session, Depends(get_db)]
DWSessionDep = Annotated[Session, Depends(get_dw_db)]

# Unified calculation service dependency
def get_unified_calculation_service(
    config_db: SessionDep,
    dw_db: DWSessionDep
):
    """Get unified calculation service with both databases"""
    from app.calculations.service import UnifiedCalculationService
    return UnifiedCalculationService(config_db, dw_db)

# Main service dependency for report execution
def get_report_execution_service(
    config_db: SessionDep,
    dw_db: DWSessionDep
):
    """Get unified calculation service for report execution"""
    return get_unified_calculation_service(config_db, dw_db)

# Backward compatibility aliases
get_user_calculation_service = get_unified_calculation_service
get_system_calculation_service = get_unified_calculation_service