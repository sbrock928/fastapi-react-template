# app/reporting/models.py - Updated Report model with column preferences

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Report(Base):
    """Report configuration with column management support."""

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    scope = Column(String, nullable=False)  # 'DEAL' or 'TRANCHE'
    created_by = Column(String, nullable=False, default="system")
    created_date = Column(DateTime, default=datetime.now)
    updated_date = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = Column(Boolean, default=True)
    
    # NEW: Column preferences for output customization
    column_preferences = Column(JSON, nullable=True)  # Stores column order, visibility, formatting
    
    # Relationships
    selected_deals = relationship("ReportDeal", back_populates="report", cascade="all, delete-orphan")
    selected_calculations = relationship("ReportCalculation", back_populates="report", cascade="all, delete-orphan")
    execution_logs = relationship("ReportExecutionLog", back_populates="report")


class ReportDeal(Base):
    """Report deal association - which deals are included in a report."""

    __tablename__ = "report_deals"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    dl_nbr = Column(Integer, nullable=False)  # References data warehouse deal

    # Relationship
    report = relationship("Report", back_populates="selected_deals")
    selected_tranches = relationship("ReportTranche", back_populates="report_deal", cascade="all, delete-orphan")


class ReportTranche(Base):
    """Report tranche association - which tranches are selected for a deal."""

    __tablename__ = "report_tranches"

    id = Column(Integer, primary_key=True, index=True)
    report_deal_id = Column(Integer, ForeignKey("report_deals.id"), nullable=False)
    dl_nbr = Column(Integer, nullable=False)  # References data warehouse tranche
    tr_id = Column(String, nullable=False)  # References data warehouse tranche

    # Relationship
    report_deal = relationship("ReportDeal", back_populates="selected_tranches")


class ReportCalculation(Base):
    """Report calculation association - which calculations are selected for a report."""

    __tablename__ = "report_calculations"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    
    # Flexible calculation reference - can be:
    # - Integer ID (user_calculations, system_calculations) 
    # - String ID (static fields like "static_deal.dl_nbr")
    calculation_id = Column(String, nullable=False)
    calculation_type = Column(String, nullable=True)  # 'user', 'system', 'static' for clarity
    display_order = Column(Integer, nullable=False, default=0)
    display_name = Column(String, nullable=True)  # Optional override

    # Relationship
    report = relationship("Report", back_populates="selected_calculations")


class ReportExecutionLog(Base):
    """Log of report executions with performance metrics."""

    __tablename__ = "report_execution_logs"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    cycle_code = Column(Integer, nullable=False)
    executed_by = Column(String, nullable=True)
    execution_time_ms = Column(Float, nullable=True)
    row_count = Column(Integer, nullable=True)
    success = Column(Boolean, nullable=False)
    error_message = Column(String, nullable=True)
    executed_at = Column(DateTime, default=datetime.now)

    # Relationship
    report = relationship("Report", back_populates="execution_logs")