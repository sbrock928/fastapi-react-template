"""Database models for the datawarehouse module (data warehouse database)."""

from datetime import datetime, date
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Date, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import DWBase


class Deal(DWBase):
    """Deal model for Mortgage-Backed Securities stored in data warehouse."""

    __tablename__ = "deal"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    originator = Column(String, nullable=False)
    deal_type = Column(String, nullable=False)  # RMBS, CMBS, Auto ABS, etc.
    closing_date = Column(Date, nullable=False)
    total_principal = Column(Numeric(15, 2), nullable=False)
    credit_rating = Column(String)  # AAA, AA+, AA, etc.
    yield_rate = Column(Numeric(5, 4))  # Decimal percentage (e.g., 0.0485 for 4.85%)
    duration = Column(Numeric(4, 2))  # Duration in years
    cycle_code = Column(String, nullable=False, index=True)  # Links to reporting cycles
    created_date = Column(DateTime, default=datetime.now)
    updated_date = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = Column(Boolean, default=True)

    # Relationship to tranches (works because both models are in same DB)
    tranches = relationship("Tranche", back_populates="deal", cascade="all, delete-orphan")


class Tranche(DWBase):
    """Tranche model - child securities of a Deal stored in data warehouse."""

    __tablename__ = "tranche"

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deal.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    class_name = Column(String, nullable=False)  # Class A, Class B, etc.
    subordination_level = Column(Integer, default=1)  # 1=Senior, 2=Mezzanine, 3=Subordinate
    principal_amount = Column(Numeric(15, 2), nullable=False)
    interest_rate = Column(Numeric(5, 4), nullable=False)  # Decimal percentage
    credit_rating = Column(String)
    payment_priority = Column(Integer, default=1)  # Payment waterfall order
    maturity_date = Column(Date, nullable=True)
    cycle_code = Column(String, nullable=False, index=True)
    created_date = Column(DateTime, default=datetime.now)
    updated_date = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = Column(Boolean, default=True)

    # Relationship back to deal (works because both models are in same DB)
    deal = relationship("Deal", back_populates="tranches")


class Cycle(DWBase):
    """Cycle model for reporting cycles stored in data warehouse."""

    __tablename__ = "cycles"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, nullable=False, unique=True, index=True)
    description = Column(String, nullable=True)
    start_date = Column(String, nullable=True)  # Using String to match SQL schema
    end_date = Column(String, nullable=True)    # Using String to match SQL schema
    created_at = Column(String, nullable=True)  # Using String to match SQL schema
