"""Pydantic schemas for the documentation module API."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# Pydantic models for API schemas
class NoteBase(BaseModel):
    """Base schema for note objects with common fields."""

    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)
    category: str = Field(min_length=1, max_length=50)

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class NoteCreate(NoteBase):
    """Schema for creating new notes."""

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


# Make this a standalone class rather than inheriting from NoteBase
class NoteUpdate(BaseModel):
    """Schema for updating existing notes."""

    title: Optional[str] = Field(None, min_length=1, max_length=100)
    content: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class NoteRead(NoteBase):
    """Schema for reading note objects with all fields."""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
