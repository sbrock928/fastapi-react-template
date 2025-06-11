# app/core/dependencies.py
"""Updated dependencies for the new base service architecture with datawarehouse services."""

from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db, get_dw_db

# Core database dependencies
SessionDep = Annotated[Session, Depends(get_db)]
DWSessionDep = Annotated[Session, Depends(get_dw_db)]

# ===== LOGGING DAO DEPENDENCIES (REFACTORED) =====

def get_log_dao(config_db: Session = Depends(get_db)):
    """Get refactored log DAO using BaseDAO"""
    from app.logging.dao import LogDAO
    return LogDAO(config_db)

# ===== CALCULATION DAO DEPENDENCIES =====

def get_user_calculation_dao(config_db: Session = Depends(get_db)):
    """Get user calculation DAO"""
    from app.calculations.dao import UserCalculationDAO
    return UserCalculationDAO(config_db)

def get_system_calculation_dao(config_db: Session = Depends(get_db)):
    """Get system calculation DAO"""
    from app.calculations.dao import SystemCalculationDAO
    return SystemCalculationDAO(config_db)

# ===== REPORTING DAO DEPENDENCIES (UPDATED) =====

def get_report_dao(config_db: Session = Depends(get_db)):
    """Get refactored report DAO"""
    from app.reporting.dao import ReportDAO
    return ReportDAO(config_db)

def get_report_execution_log_dao(config_db: Session = Depends(get_db)):
    """Get refactored report execution log DAO"""
    from app.reporting.execution_log_dao import ReportExecutionLogDAO
    return ReportExecutionLogDAO(config_db)

# ===== AUDIT DAO DEPENDENCIES =====

def get_calculation_audit_dao(config_db: Session = Depends(get_db)):
    """Get calculation audit DAO"""
    from app.calculations.audit_dao import CalculationAuditDAO
    return CalculationAuditDAO(config_db)

# ===== DATAWAREHOUSE DAO DEPENDENCIES (NEW) =====

def get_datawarehouse_dao(dw_db: Session = Depends(get_dw_db)):
    """Get composite datawarehouse DAO"""
    from app.datawarehouse.dao import DatawarehouseDAO
    return DatawarehouseDAO(dw_db)

def get_deal_dao(dw_db: Session = Depends(get_dw_db)):
    """Get deal DAO"""
    from app.datawarehouse.dao import DealDAO
    return DealDAO(dw_db)

def get_tranche_dao(dw_db: Session = Depends(get_dw_db)):
    """Get tranche DAO"""
    from app.datawarehouse.dao import TrancheDAO
    return TrancheDAO(dw_db)

def get_tranche_bal_dao(dw_db: Session = Depends(get_dw_db)):
    """Get tranche balance DAO"""
    from app.datawarehouse.dao import TrancheBalDAO
    return TrancheBalDAO(dw_db)

# ===== LOGGING SERVICE DEPENDENCIES (REFACTORED) =====

def get_log_service(log_dao = Depends(get_log_dao)):
    """Get refactored log service using BaseService"""
    from app.logging.service import LogService
    return LogService(log_dao)

# ===== CALCULATION SERVICE DEPENDENCIES =====

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

# ===== DATAWAREHOUSE SERVICE DEPENDENCIES (NEW) =====

def get_datawarehouse_service(datawarehouse_dao = Depends(get_datawarehouse_dao)):
    """Get composite datawarehouse service"""
    from app.datawarehouse.service import DatawarehouseService
    return DatawarehouseService(datawarehouse_dao)

def get_deal_service(deal_dao = Depends(get_deal_dao)):
    """Get deal service"""
    from app.datawarehouse.service import DealService
    return DealService(deal_dao)

def get_tranche_service(tranche_dao = Depends(get_tranche_dao)):
    """Get tranche service"""
    from app.datawarehouse.service import TrancheService
    return TrancheService(tranche_dao)

def get_tranche_bal_service(tranche_bal_dao = Depends(get_tranche_bal_dao)):
    """Get tranche balance service"""
    from app.datawarehouse.service import TrancheBalService
    return TrancheBalService(tranche_bal_dao)

# ===== REPORTING SERVICE DEPENDENCIES (UPDATED) =====

def get_report_execution_log_service(execution_log_dao = Depends(get_report_execution_log_dao)):
    """Get report execution log service"""
    from app.reporting.execution_log_service import ReportExecutionLogService
    return ReportExecutionLogService(execution_log_dao)

def get_report_service(
    report_dao = Depends(get_report_dao),
    dw_dao = Depends(get_datawarehouse_dao),  # Updated to use new datawarehouse DAO
    user_calc_service = Depends(get_user_calculation_service),
    system_calc_service = Depends(get_system_calculation_service),
    report_execution_service = Depends(get_report_execution_service),
    execution_log_service = Depends(get_report_execution_log_service)
):
    """Get comprehensive report service with all dependencies using refactored BaseService"""
    from app.reporting.service import ReportService
    # Create service with BaseService architecture
    service = ReportService(
        report_dao, 
        dw_dao, 
        user_calc_service, 
        system_calc_service, 
        report_execution_service
    )
    # Inject execution log service
    service.execution_log_service = execution_log_service
    return service

# ===== AUDIT SERVICE DEPENDENCIES =====

def get_calculation_audit_service(audit_dao = Depends(get_calculation_audit_dao)):
    """Get calculation audit service"""
    from app.calculations.audit_service import CalculationAuditService
    return CalculationAuditService(audit_dao)