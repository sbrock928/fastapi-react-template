from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional, Dict, Any
from app.documentation.models import Note


class DocumentationDAO:
    """Documentation-specific DAO with methods for working with notes"""

    def __init__(self, session: Session):
        self.session = session

    async def get_all_notes(self) -> List[Note]:
        """Get all user guide notes"""
        query = select(Note).order_by(Note.updated_at.desc(), Note.created_at.desc())
        result = self.session.execute(query)
        return list(result.scalars().all())

    async def get_all(self) -> List[Note]:
        """Get all records"""
        result = self.session.execute(select(Note))
        items = result.scalars().all()
        return list(items)

    async def get_by_id(self, note_id: int) -> Optional[Note]:
        """Get a note by ID"""
        note = self.session.get(Note, note_id)
        return note

    async def create(self, note_dict: Dict[str, Any]) -> Note:
        """Create a new note"""
        note = Note(**note_dict)
        self.session.add(note)
        self.session.commit()
        self.session.refresh(note)
        return note

    async def update(self, note_id: int, update_dict: Dict[str, Any]) -> Optional[Note]:
        """Update an existing note"""
        note = await self.get_by_id(note_id)
        if not note:
            return None

        # Update only the provided fields
        for key, value in update_dict.items():
            if value is not None:  # Only update fields that are provided
                setattr(note, key, value)

        self.session.add(note)
        self.session.commit()
        self.session.refresh(note)
        return note

    async def delete(self, note_id: int) -> bool:
        """Delete a note"""
        note = await self.get_by_id(note_id)
        if not note:
            return False

        self.session.delete(note)
        self.session.commit()
        return True

    async def get_by_category(self, category: str) -> List[Note]:
        """Get notes filtered by category"""
        query = (
            select(Note)
            .where(Note.category == category)
            .order_by(Note.updated_at.desc(), Note.created_at.desc())
        )
        result = self.session.execute(query)
        return list(result.scalars().all())
