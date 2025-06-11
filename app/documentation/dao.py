"""Data Access Objects for the documentation module using BaseDAO."""

from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List
from app.core.base_dao import BaseDAO
from app.documentation.models import Note


class DocumentationDAO(BaseDAO[Note]):
    """Documentation-specific DAO extending BaseDAO with specialized methods for notes."""

    def __init__(self, session: Session):
        super().__init__(Note, session)

    def get_all_notes(self) -> List[Note]:
        """Get all user guide notes ordered by most recently updated."""
        query = select(Note).order_by(Note.updated_at.desc(), Note.created_at.desc())
        result = self.db.execute(query)
        return list(result.scalars().all())

    def get_by_category(self, category: str) -> List[Note]:
        """Get notes filtered by category ordered by most recently updated."""
        query = (
            select(Note)
            .where(Note.category == category)
            .order_by(Note.updated_at.desc(), Note.created_at.desc())
        )
        result = self.db.execute(query)
        return list(result.scalars().all())

    # All other CRUD operations (get_all, get_by_id, create, update, delete)
    # are inherited from BaseDAO and work automatically!