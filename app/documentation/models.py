from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime

# SQLAlchemy Base
from app.core.database import Base


# SQLAlchemy model
class Note(Base):
    __tablename__ = "note"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    content = Column(String, nullable=False)
    category = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, nullable=True)
