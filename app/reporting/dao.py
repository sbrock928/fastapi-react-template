"""Refactored Data Access Objects for the reporting module using BaseDAO."""

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from typing import List, Optional
from app.core.base_dao import BaseDAO
from app.reporting.models import Report, ReportDeal, ReportTranche


class ReportDAO(BaseDAO[Report]):
    """Refactored DAO for Report operations using BaseDAO."""

    def __init__(self, db_session: Session):
        super().__init__(Report, db_session)

    def get_all_with_relationships(self) -> List[Report]:
        """Get all active reports with relationships loaded - custom method."""
        stmt = (
            select(Report)
            .options(
                selectinload(Report.selected_deals).selectinload(ReportDeal.selected_tranches),
                selectinload(Report.selected_calculations),
            )
            .where(Report.is_active == True)
            .order_by(Report.created_date.desc())
        )
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    def get_by_id_with_relationships(self, report_id: int) -> Optional[Report]:
        """Get a report by ID with relationships loaded - custom method."""
        stmt = (
            select(Report)
            .options(
                selectinload(Report.selected_deals).selectinload(ReportDeal.selected_tranches),
                selectinload(Report.selected_calculations),
            )
            .where(Report.id == report_id)
        )
        result = self.db.execute(stmt)
        return result.scalars().first()

    def create_with_relationships(self, report: Report) -> Report:
        """Create a new report with all relationships - custom method."""
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def update_with_relationships(self, report: Report) -> Report:
        """Update an existing report - custom method."""
        self.db.commit()
        self.db.refresh(report)
        return report

    def hard_delete(self, report_id: int) -> bool:
        """Hard delete a report by ID (for testing/cleanup) - custom method."""
        report = self.get_by_id(report_id)
        if report:
            self.db.delete(report)
            self.db.commit()
            return True
        return False

    # Override soft_delete to use custom logic
    def soft_delete(self, report_id: int) -> bool:
        """Soft delete a report by ID - override base method."""
        report = self.get_by_id(report_id)
        if report:
            report.is_active = False
            self.db.commit()
            return True
        return False