"""Database models for the logging module."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float
from app.core.database import Base


# SQLAlchemy model for database operations
class Log(Base):
    """SQLAlchemy model for API request and response logs."""

    __tablename__ = "log"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.now)
    method = Column(String, nullable=False)
    path = Column(String, nullable=False)
    status_code = Column(Integer, nullable=False)
    client_ip = Column(String, nullable=True)
    request_headers = Column(String, nullable=True)
    request_body = Column(String, nullable=True)
    response_body = Column(String, nullable=True)
    processing_time = Column(Float, nullable=True)
    user_agent = Column(String, nullable=True)
    username = Column(String, nullable=True)
    hostname = Column(String, nullable=True)
    application_id = Column(String, nullable=True)
