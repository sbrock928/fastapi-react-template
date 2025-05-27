"""Data Access Objects for the reporting module."""

from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import List, Optional, Dict
from app.reporting.models import Report


class ReportDAO:
    """DB functionality for interaction with `Report` objects in config database."""

    def __init__(self, db_session: Session):
        self.db = db_session

    async def get_all(self) -> List[Report]:
        """Get all reports"""
        stmt = select(Report).where(Report.is_active == True)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, report_id: int) -> Optional[Report]:
        """Get a report by ID"""
        stmt = select(Report).where(Report.id == report_id)
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_created_by(self, created_by: str) -> List[Report]:
        """Get reports by creator"""
        stmt = (
            select(Report)
            .where(Report.created_by == created_by, Report.is_active == True)
            .order_by(Report.created_date.desc())
        )
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_name_and_creator(self, name: str, created_by: str) -> Optional[Report]:
        """Get a report by name and creator (for duplicate checking)"""
        stmt = select(Report).where(
            Report.name == name, Report.created_by == created_by, Report.is_active == True
        )
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def create(self, report_obj: Report) -> Report:
        """Create a new report"""
        self.db.add(report_obj)
        self.db.commit()
        self.db.refresh(report_obj)
        return report_obj

    async def update(self, report_obj: Report) -> Report:
        """Update an existing report"""
        self.db.add(report_obj)
        self.db.commit()
        self.db.refresh(report_obj)
        return report_obj

    async def delete(self, report_id: int) -> bool:
        """Soft delete a report by ID"""
        report = await self.get_by_id(report_id)
        if report:
            report.is_active = False
            await self.update(report)
            return True
        return False

    async def hard_delete(self, report_id: int) -> bool:
        """Hard delete a report by ID"""
        report = await self.get_by_id(report_id)
        if report:
            self.db.delete(report)
            self.db.commit()
            return True
        return False

    async def get_report_count(self) -> int:
        """Get total count of active reports"""
        result = self.db.execute(
            select(func.count()).select_from(Report).where(Report.is_active == True)
        )
        return int(result.scalar_one() or 0)

    async def get_reports_by_scope(self, scope: str) -> List[Report]:
        """Get reports by scope (DEAL or TRANCHE)"""
        stmt = (
            select(Report)
            .where(Report.scope == scope, Report.is_active == True)
            .order_by(Report.created_date.desc())
        )
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_available_cycles(self) -> List[Dict[str, str]]:
        """Get available cycle codes from the data warehouse.

        TODO: In the future, this should query the actual data warehouse
        to get real cycle codes from the deals/tranches tables.
        For now, returns dummy data for development/testing.
        """
        # Dummy cycle data - replace with real query later
        dummy_cycles = [
            {"code": "2024Q1", "label": "2024Q1 (Quarter 1 2024)"},
            {"code": "2024Q2", "label": "2024Q2 (Quarter 2 2024)"},
            {"code": "2024Q3", "label": "2024Q3 (Quarter 3 2024)"},
            {"code": "2024Q4", "label": "2024Q4 (Quarter 4 2024)"},
            {"code": "2025Q1", "label": "2025Q1 (Quarter 1 2025)"},
        ]
        return dummy_cycles
