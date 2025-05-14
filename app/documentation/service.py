from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from fastapi import HTTPException
from app.documentation.models import (
    Note,
    NoteBase,
    NoteUpdate,
    NoteRead,
    note_to_pydantic,
)
from app.documentation.dao import DocumentationDAO
from app.common.base_service import GenericService


class DocumentationService(GenericService[Note, NoteBase, NoteUpdate, NoteRead]):
    """Documentation service with custom methods"""

    def __init__(self, session: Session, dao: DocumentationDAO = None):
        super().__init__(session, Note, NoteBase, NoteUpdate, NoteRead)
        self.dao = dao if dao is not None else DocumentationDAO(session)

    async def get_all_notes(self) -> List[NoteRead]:
        """Get all user guide notes"""
        try:
            # Get SQLAlchemy models from DAO
            notes = await self.dao.get_all_notes()
            # Convert to Pydantic models
            return self.to_read_model_list(notes)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error fetching notes: {str(e)}"
            )

    async def get_note_by_id(self, note_id: int) -> Optional[NoteRead]:
        """Get a note by its ID"""
        note = await self.dao.get_by_id(note_id)
        if not note:
            return None
        return self.to_read_model(note)

    async def create_note(self, note: NoteBase) -> NoteRead:
        """Create a new note"""
        try:
            # Convert Pydantic model to dictionary for SQLAlchemy
            note_dict = self.to_db_model_dict(note)

            # Create DB model through DAO
            db_note = await self.dao.create(note_dict)

            # Convert back to Pydantic schema for response
            return self.to_read_model(db_note)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error creating note: {str(e)}"
            )

    async def update_note(
        self, note_id: int, note_data: NoteUpdate
    ) -> Optional[NoteRead]:
        """Update an existing note"""
        # Add updated timestamp
        note_dict = self.to_db_model_dict(note_data)
        note_dict["updated_at"] = datetime.now()

        # Update through DAO
        db_note = await self.dao.update(note_id, note_dict)

        if not db_note:
            return None

        # Convert to Pydantic model for response
        return self.to_read_model(db_note)

    async def delete_note(self, note_id: int) -> bool:
        """Delete a note by ID"""
        return await self.dao.delete(note_id)

    async def get_notes_by_category(self, category: str) -> List[NoteRead]:
        """Get notes filtered by category"""
        try:
            # Get SQLAlchemy models from DAO
            notes = await self.dao.get_by_category(category)
            # Convert to Pydantic models
            return self.to_read_model_list(notes)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error fetching notes by category: {str(e)}"
            )
