"""Service layer for the documentation module using BaseService."""

from typing import List, Optional
from datetime import datetime
from fastapi import HTTPException
from app.core.base_service import BaseService
from app.documentation.models import Note
from app.documentation.schemas import (
    NoteCreate,
    NoteUpdate,
    NoteRead,
)
from app.documentation.dao import DocumentationDAO


class DocumentationService(BaseService[Note, NoteCreate, NoteUpdate, NoteRead]):
    """Documentation service extending BaseService with specialized methods for notes."""

    def __init__(self, dao: DocumentationDAO):
        super().__init__(dao)
        # Type hint the DAO for access to specialized methods
        self.documentation_dao = dao

    def _to_response(self, record: Note) -> NoteRead:
        """Convert Note model to NoteRead schema."""
        try:
            return NoteRead.model_validate(record)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error converting note to response: {str(e)}") from e

    async def get_all_notes(self) -> List[NoteRead]:
        """Get all user guide notes ordered by most recently updated."""
        try:
            notes = self.documentation_dao.get_all_notes()
            return [self._to_response(note) for note in notes]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching notes: {str(e)}") from e

    async def get_notes_by_category(self, category: str) -> List[NoteRead]:
        """Get notes filtered by category."""
        try:
            notes = self.documentation_dao.get_by_category(category)
            return [self._to_response(note) for note in notes]
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error fetching notes by category: {str(e)}"
            ) from e

    # Wrapper methods for async compatibility with existing router
    async def get_note_by_id(self, note_id: int) -> Optional[NoteRead]:
        """Get a note by its ID (async wrapper)."""
        try:
            return self.get_by_id(note_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching note: {str(e)}") from e

    async def create_note(self, note: NoteCreate) -> NoteRead:
        """Create a new note (async wrapper)."""
        try:
            return self.create(note)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error creating note: {str(e)}") from e

    async def update_note(self, note_id: int, note_data: NoteUpdate) -> Optional[NoteRead]:
        """Update an existing note (async wrapper with updated timestamp)."""
        try:
            # Add updated timestamp to the update data
            return self.update(note_id, note_data, updated_at=datetime.now())
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error updating note: {str(e)}") from e

    async def delete_note(self, note_id: int) -> bool:
        """Delete a note by ID (async wrapper)."""
        try:
            return self.delete(note_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error deleting note: {str(e)}") from e

    # Override validation hooks for business logic
    def _validate_create(self, create_data: NoteCreate) -> None:
        """Validate note creation data."""
        # Add any business validation rules here
        if len(create_data.title.strip()) == 0:
            raise HTTPException(status_code=400, detail="Note title cannot be empty")
        if len(create_data.content.strip()) == 0:
            raise HTTPException(status_code=400, detail="Note content cannot be empty")

    def _validate_update(self, record: Note, update_data: NoteUpdate) -> None:
        """Validate note update data."""
        # Add any business validation rules here
        if update_data.title is not None and len(update_data.title.strip()) == 0:
            raise HTTPException(status_code=400, detail="Note title cannot be empty")
        if update_data.content is not None and len(update_data.content.strip()) == 0:
            raise HTTPException(status_code=400, detail="Note content cannot be empty")

    def _post_create(self, record: Note, create_data: NoteCreate) -> None:
        """Business logic after note creation."""
        # Add any post-creation logic here (logging, notifications, etc.)
        pass

    def _post_update(self, record: Note, update_data: NoteUpdate) -> None:
        """Business logic after note update.""" 
        # Add any post-update logic here (logging, notifications, etc.)
        pass