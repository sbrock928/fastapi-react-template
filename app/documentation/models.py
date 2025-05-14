from typing import Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from pydantic import BaseModel, Field, ConfigDict

# SQLAlchemy Base
from app.database import Base


# SQLAlchemy model
class Note(Base):
    __tablename__ = "note"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    content = Column(String, nullable=False)
    category = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, nullable=True)


# Pydantic models for API schemas
class NoteBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)
    category: str = Field(min_length=1, max_length=50)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class NoteCreate(NoteBase):
    pass


class NoteRead(NoteBase):
    id: int


# Helper function to convert between SQLAlchemy and Pydantic models
def note_to_pydantic(note: Note) -> NoteRead:
    return NoteRead.model_validate(note)
