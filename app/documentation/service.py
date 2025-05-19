"""Service layer for the documentation module handling business logic for notes."""

from typing import List, Optional
from datetime import datetime
from fastapi import HTTPException
from app.documentation.schemas import (
    NoteCreate,
    NoteUpdate,
    NoteRead,
)
from app.documentation.dao import DocumentationDAO


class DocumentationService:
    """Documentation service with methods for handling notes"""

    def __init__(self, dao: DocumentationDAO):
        self.dao = dao

    async def get_all_notes(self) -> List[NoteRead]:
        """Get all user guide notes"""
        try:
            # Get SQLAlchemy models from DAO
            notes = await self.dao.get_all_notes()
            # Convert to Pydantic models
            return [NoteRead.model_validate(note) for note in notes]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching notes: {str(e)}") from e

    async def get_all(self) -> List[NoteRead]:
        """Get all notes"""
        try:
            notes = await self.dao.get_all()
            return [NoteRead.model_validate(note) for note in notes]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching notes: {str(e)}") from e

    async def get_note_by_id(self, note_id: int) -> Optional[NoteRead]:
        """Get a note by its ID"""
        try:
            note = await self.dao.get_by_id(note_id)
            if not note:
                return None
            return NoteRead.model_validate(note)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching note: {str(e)}") from e

    async def create_note(self, note: NoteCreate) -> NoteRead:
        """Create a new note"""
        try:
            # Convert Pydantic model to dictionary for SQLAlchemy
            note_dict = note.model_dump(exclude_unset=True)

            # Create DB model through DAO
            db_note = await self.dao.create(note_dict)

            # Convert back to Pydantic schema for response
            return NoteRead.model_validate(db_note)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error creating note: {str(e)}") from e

    async def update_note(self, note_id: int, note_data: NoteUpdate) -> Optional[NoteRead]:
        """Update an existing note"""
        try:
            # Add updated timestamp
            note_dict = note_data.model_dump(exclude_unset=True)
            note_dict["updated_at"] = datetime.now()

            # Update through DAO
            db_note = await self.dao.update(note_id, note_dict)

            if not db_note:
                return None

            # Convert to Pydantic model for response
            return NoteRead.model_validate(db_note)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error updating note: {str(e)}") from e

    async def delete_note(self, note_id: int) -> bool:
        """Delete a note by ID"""
        try:
            return await self.dao.delete(note_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error deleting note: {str(e)}") from e

    async def get_notes_by_category(self, category: str) -> List[NoteRead]:
        """Get notes filtered by category"""
        try:
            # Get SQLAlchemy models from DAO
            notes = await self.dao.get_by_category(category)
            # Convert to Pydantic models
            return [NoteRead.model_validate(note) for note in notes]
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error fetching notes by category: {str(e)}"
            ) from e
