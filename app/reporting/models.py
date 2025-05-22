"""Database models for the reporting module (config database)."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship, ForeignKey
from app.core.database import Base


class Report(Base):
    """Report configuration model stored in config database."""
    
    __tablename__ = "report"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    scope = Column(String, nullable=False)  # 'DEAL' or 'TRANCHE'
    created_by = Column(String, nullable=False, index=True)
    created_date = Column(DateTime, default=datetime.now)
    updated_date = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = Column(Boolean, default=True)
    
    # JSON fields storing IDs that reference data warehouse
    # selected_deals: [1, 2, 3]
    # selected_tranches: {"1": [1, 2], "2": [3, 4, 5]}
    selected_deals = Column(JSON)
    selected_tranches = Column(JSON)
    selected_columns = Column(JSON) 

    overrides = relationship("ReportTrancheOverride", back_populates="report", cascade="all, delete-orphan")

    class ReportTrancheOverride(Base):
    """Model for storing manual overrides for tranche values in reports."""
    
    __tablename__ = "report_tranche_override"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("report.id"), nullable=False, index=True)
    tranche_id = Column(Integer, nullable=False, index=True)  # References datawarehouse tranche
    column_name = Column(String(255), nullable=False)
    override_value = Column(Text)  # JSON-serialized value
    override_type = Column(String(50), default="manual")  # 'manual', 'calculated', 'mapped'
    notes = Column(Text)  # User notes explaining the override
    created_by = Column(String(255), nullable=False)
    created_date = Column(DateTime, default=datetime.now)
    updated_date = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationship back to report
    report = relationship("Report", back_populates="overrides")

    # Composite unique constraint
    __table_args__ = (
        Index('idx_report_tranche_column', 'report_id', 'tranche_id', 'column_name', unique=True),