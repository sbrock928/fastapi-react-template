"""Database models for the resources module."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.core.database import Base


# SQLAlchemy models
class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)


class Employee(Base):
    __tablename__ = "employee"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    department = Column(String)
    position = Column(String)


class Subscriber(Base):
    __tablename__ = "subscriber"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    subscription_tier = Column(String, default="free")
    signup_date = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)
    last_billing_date = Column(DateTime, nullable=True)
