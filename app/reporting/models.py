"""Database models for the reporting module (config database) - Updated for calculation-based reporting."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.core.database import Base


class Report(Base):
    """Report configuration model stored in config database."""

    __tablename__ = "reports"    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)  # Optional description field
    scope = Column(String, nullable=False)  # 'DEAL' or 'TRANCHE'
    created_by = Column(String, nullable=False, index=True)
    created_date = Column(DateTime, default=datetime.now)
    updated_date = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = Column(Boolean, default=True)

    # Relationships to selected deals, tranches, and calculations
    selected_deals = relationship("ReportDeal", back_populates="report", cascade="all, delete-orphan")
    selected_calculations = relationship("ReportCalculation", back_populates="report", cascade="all, delete-orphan")
    execution_logs = relationship("ReportExecutionLog", back_populates="report")


class ReportDeal(Base):
    """Report deal association model - stores which deals are selected for a report."""

    __tablename__ = "report_deals"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    dl_nbr = Column(Integer, nullable=False)  # References data warehouse deal dl_nbr
    
    # Relationships
    report = relationship("Report", back_populates="selected_deals")
    selected_tranches = relationship("ReportTranche", back_populates="report_deal", cascade="all, delete-orphan")


class ReportTranche(Base):
    """Report tranche association model - stores which tranches are selected for a report."""

    __tablename__ = "report_tranches"
    
    id = Column(Integer, primary_key=True, index=True)
    report_deal_id = Column(Integer, ForeignKey("report_deals.id"), nullable=False)
    dl_nbr = Column(Integer, nullable=False)  # References data warehouse tranche dl_nbr
    tr_id = Column(String, nullable=False)   # References data warehouse tranche tr_id
    
    # Relationship
    report_deal = relationship("ReportDeal", back_populates="selected_tranches")


class ReportCalculation(Base):
    """Report calculation association model - stores which calculations are selected for a report."""

    __tablename__ = "report_calculations"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    calculation_id = Column(Integer, ForeignKey("calculations.id"), nullable=False)
    display_order = Column(Integer, nullable=False, default=0)  # Order in report
    display_name = Column(String, nullable=True)  # Optional override for calculation name
    
    # Relationship
    report = relationship("Report", back_populates="selected_calculations")


class ReportExecutionLog(Base):
    """Log of report executions with cycle_code and performance metrics."""

    __tablename__ = "report_execution_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    cycle_code = Column(Integer, nullable=False)  # Cycle code used for execution
    executed_by = Column(String, nullable=True)
    execution_time_ms = Column(Float, nullable=True)
    row_count = Column(Integer, nullable=True)
    success = Column(Boolean, nullable=False)
    error_message = Column(String, nullable=True)
    executed_at = Column(DateTime, default=datetime.now)
    
    # Relationship
    report = relationship("Report", back_populates="execution_logs")