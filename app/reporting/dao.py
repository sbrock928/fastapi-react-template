"""Simplified Data Access Objects for the reporting module."""

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from typing import List, Optional
from app.reporting.models import Report, ReportDeal, ReportTranche, ReportCalculation


class ReportDAO:
    """Simplified DAO for Report operations."""

    def __init__(self, db_session: Session):
        self.db = db_session

    async def get_all(self) -> List[Report]:
        """Get all active reports with relationships loaded."""
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

    async def get_by_id(self, report_id: int) -> Optional[Report]:
        """Get a report by ID with relationships loaded."""
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

    async def create(self, report: Report) -> Report:
        """Create a new report with all relationships."""
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    async def update(self, report: Report) -> Report:
        """Update an existing report."""
        self.db.commit()
        self.db.refresh(report)
        return report

    async def delete(self, report_id: int) -> bool:
        """Soft delete a report by ID."""
        report = await self.get_by_id(report_id)
        if report:
            report.is_active = False
            self.db.commit()
            return True
        return False

    async def hard_delete(self, report_id: int) -> bool:
        """Hard delete a report by ID (for testing/cleanup)."""
        report = await self.get_by_id(report_id)
        if report:
            self.db.delete(report)
            self.db.commit()
            return True
        return False
