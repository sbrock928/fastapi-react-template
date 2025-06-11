# app/core/dependencies.py
"""Enhanced dependencies with new calculation services"""

from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db, get_dw_db

# Existing dependencies
SessionDep = Annotated[Session, Depends(get_db)]
DWSessionDep = Annotated[Session, Depends(get_dw_db)]

# New calculation service dependencies
def get_user_calculation_service(config_db: Session = Depends(get_db)):
    """Get user calculation service"""
    from app.calculations.service import UserCalculationService
    return UserCalculationService(config_db)

def get_system_calculation_service(config_db: Session = Depends(get_db)):
    """Get system calculation service"""
    from app.calculations.service import SystemCalculationService
    return SystemCalculationService(config_db)

def get_report_execution_service(
    config_db: Session = Depends(get_db),
    dw_db: Session = Depends(get_dw_db)
):
    """Get report execution service"""
    from app.calculations.service import ReportExecutionService
    return ReportExecutionService(dw_db, config_db)

# Legacy query engine (for backward compatibility during migration)
def get_legacy_query_engine(
    dw_db: Session = Depends(get_dw_db), 
    config_db: Session = Depends(get_db)
):
    """Get legacy query engine (deprecated - use ReportExecutionService instead)"""
    from app.query import QueryEngine
    return QueryEngine(dw_db, config_db)