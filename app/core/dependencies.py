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

def get_cdi_calculation_service(
    config_db: SessionDep, 
    dw_db: DWSessionDep,
    system_calc_service = Depends(get_system_calculation_service)
):
    """Get CDI Variable Calculation Service with proper dependency injection"""
    from app.calculations.cdi_service import CDIVariableCalculationService
    cdi_service = CDIVariableCalculationService(dw_db, config_db, system_calc_service)
    # Set up bidirectional relationship for integrated execution
    system_calc_service.set_cdi_service(cdi_service)
    return cdi_service

def get_report_execution_service_with_cdi(
    config_db: SessionDep,
    dw_db: DWSessionDep
):
    """Get Enhanced Report Execution Service (replaces the old one)"""
    from app.calculations.dao import SystemCalculationDAO
    from app.calculations.service import SystemCalculationService, ReportExecutionService
    from app.calculations.cdi_service import CDIVariableCalculationService
    
    # Create services manually since we need proper dependency chain
    system_calc_dao = SystemCalculationDAO(config_db)
    system_calc_service = SystemCalculationService(system_calc_dao)
    cdi_service = CDIVariableCalculationService(dw_db, config_db, system_calc_service)
    system_calc_service.set_cdi_service(cdi_service)
    
    return ReportExecutionService(dw_db, config_db, cdi_service)

# Backward compatible alias for enhanced report execution service
def get_report_execution_service(
    config_db: SessionDep,
    dw_db: DWSessionDep
):
    """Get report execution service with CDI integration"""
    return get_report_execution_service_with_cdi(config_db, dw_db)