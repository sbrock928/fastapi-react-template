from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
from app.user_guide.models import Note, NoteBase

class UserGuideService:
    def __init__(self, session: Session):
        self.session = session

    async def get_all_notes(self) -> List[Note]:
        """Get all user guide notes"""
        notes = self.session.exec(select(Note).order_by(Note.updated_at.desc(), Note.created_at.desc())).all()
        return notes

    async def get_note_by_id(self, note_id: int) -> Optional[Note]:
        """Get a note by its ID"""
        note = self.session.exec(select(Note).where(Note.id == note_id)).first()
        return note

    async def create_note(self, note: NoteBase) -> Note:
        """Create a new note"""
        db_note = Note.from_orm(note)
        self.session.add(db_note)
        self.session.commit()
        self.session.refresh(db_note)
        return db_note

    async def update_note(self, note_id: int, note_data: NoteBase) -> Optional[Note]:
        """Update an existing note"""
        db_note = await self.get_note_by_id(note_id)
        if not db_note:
            return None

        note_dict = note_data.dict(exclude_unset=True)
        note_dict["updated_at"] = datetime.now()
        
        for key, value in note_dict.items():
            setattr(db_note, key, value)
        
        self.session.add(db_note)
        self.session.commit()
        self.session.refresh(db_note)
        return db_note

    async def delete_note(self, note_id: int) -> bool:
        """Delete a note by ID"""
        db_note = await self.get_note_by_id(note_id)
        if not db_note:
            return False
        
        self.session.delete(db_note)
        self.session.commit()
        return True

    async def get_notes_by_category(self, category: str) -> List[Note]:
        """Get notes filtered by category"""
        notes = self.session.exec(
            select(Note)
            .where(Note.category == category)
            .order_by(Note.updated_at.desc(), Note.created_at.desc())
        ).all()
        return notes
