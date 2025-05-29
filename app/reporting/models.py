"""Database models for the reporting module (config database)."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Report(Base):
    """Report configuration model stored in config database."""

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    scope = Column(String, nullable=False)  # 'DEAL' or 'TRANCHE'
    created_by = Column(String, nullable=False, index=True)
    created_date = Column(DateTime, default=datetime.now)
    updated_date = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = Column(Boolean, default=True)

    # Relationships to selected deals and tranches
    selected_deals = relationship("ReportDeal", back_populates="report", cascade="all, delete-orphan")


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
