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
    description = Column(String, nullable=True)  # Optional description field
    scope = Column(String, nullable=False)  # 'DEAL' or 'TRANCHE'
    created_by = Column(String, nullable=False, index=True)
    created_date = Column(DateTime, default=datetime.now)
    updated_date = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = Column(Boolean, default=True)

    # Relationships to selected deals, tranches, fields, and filter conditions
    selected_deals = relationship("ReportDeal", back_populates="report", cascade="all, delete-orphan")
    selected_fields = relationship("ReportField", back_populates="report", cascade="all, delete-orphan")
    filter_conditions = relationship("FilterCondition", back_populates="report", cascade="all, delete-orphan")


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


class ReportField(Base):
    """Report field configuration model - stores which fields are selected for a report."""

    __tablename__ = "report_fields"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    field_name = Column(String, nullable=False)  # e.g., "dl_nbr", "issr_cde"
    display_name = Column(String, nullable=False)  # e.g., "Deal Number", "Issuer Code"
    field_type = Column(String, nullable=False)  # e.g., "text", "number", "date"
    is_required = Column(Boolean, default=False)
    
    # Relationship
    report = relationship("Report", back_populates="selected_fields")


class FilterCondition(Base):
    """Filter condition model - stores filter conditions for reports."""

    __tablename__ = "filter_conditions"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    field_name = Column(String, nullable=False)  # e.g., "dl_nbr", "issr_cde"
    operator = Column(String, nullable=False)    # e.g., "=", ">", "<", "LIKE"
    value = Column(String, nullable=True)        # Value to compare against (NULL for IS_NULL/IS_NOT_NULL operators)
    
    # Relationship
    report = relationship("Report", back_populates="filter_conditions")
