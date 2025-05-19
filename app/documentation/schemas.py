from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# Pydantic models for API schemas
class NoteBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)
    category: str = Field(min_length=1, max_length=50)

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class NoteCreate(NoteBase):
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


# Make this a standalone class rather than inheriting from NoteBase
class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    content: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class NoteRead(NoteBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
