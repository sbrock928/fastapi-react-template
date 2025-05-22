"""Database models for the reporting module (config database)."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON
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