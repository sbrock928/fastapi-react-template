from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from app.documentation.models import Note
from app.common.base_dao import GenericDAO


class DocumentationDAO(GenericDAO[Note]):
    """Documentation-specific DAO with custom methods"""

    def __init__(self, session: Session):
        super().__init__(session, Note)

    async def get_all_notes(self) -> List[Note]:
        """Get all user guide notes"""
        query = select(self.model_class).order_by(
            self.model_class.updated_at.desc(), self.model_class.created_at.desc()
        )
        result = self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_category(self, category: str) -> List[Note]:
        """Get notes filtered by category"""
        query = (
            select(self.model_class)
            .where(self.model_class.category == category)
            .order_by(
                self.model_class.updated_at.desc(), self.model_class.created_at.desc()
            )
        )
        result = self.session.execute(query)
        return list(result.scalars().all())
