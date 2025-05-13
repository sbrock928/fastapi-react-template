from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime


class NoteBase(SQLModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)
    category: str = Field(min_length=1, max_length=50)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default=None)

    class Config:
        orm_mode = True
        extra = "forbid"


class Note(NoteBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
