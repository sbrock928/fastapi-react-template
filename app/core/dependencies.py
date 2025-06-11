# app/core/dependencies.py
"""Clean dependencies for the new calculation system"""

from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db, get_dw_db

# Core database dependencies
SessionDep = Annotated[Session, Depends(get_db)]
DWSessionDep = Annotated[Session, Depends(get_dw_db)]

# DAO dependencies
def get_user_calculation_dao(config_db: Session = Depends(get_db)):
    """Get user calculation DAO"""
    from app.calculations.dao import UserCalculationDAO
    return UserCalculationDAO(config_db)

def get_system_calculation_dao(config_db: Session = Depends(get_db)):
    """Get system calculation DAO"""
    from app.calculations.dao import SystemCalculationDAO
    return SystemCalculationDAO(config_db)

# New calculation service dependencies using DAOs
def get_user_calculation_service(user_calc_dao = Depends(get_user_calculation_dao)):
    """Get user calculation service"""
    from app.calculations.service import UserCalculationService
    return UserCalculationService(user_calc_dao)

def get_system_calculation_service(system_calc_dao = Depends(get_system_calculation_dao)):
    """Get system calculation service"""
    from app.calculations.service import SystemCalculationService
    return SystemCalculationService(system_calc_dao)

def get_report_execution_service(
    config_db: Session = Depends(get_db),
    dw_db: Session = Depends(get_dw_db)
):
    """Get report execution service"""
    from app.calculations.service import ReportExecutionService
    return ReportExecutionService(dw_db, config_db)