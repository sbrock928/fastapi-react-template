"""Data Access Objects for the reporting module - Updated with execution logging."""

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func
from typing import List, Optional
from app.reporting.models import Report, ReportDeal, ReportTranche, ReportCalculation


class ReportDAO:
    """DB functionality for interaction with `Report` objects in config database."""

    def __init__(self, db_session: Session):
        self.db = db_session

    async def get_all(self) -> List[Report]:
        """Get all reports with eager loading of relationships."""
        stmt = (
            select(Report)
            .options(
                selectinload(Report.selected_deals).selectinload(ReportDeal.selected_tranches),
                selectinload(Report.selected_calculations)
            )
            .where(Report.is_active == True)
        )
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, report_id: int) -> Optional[Report]:
        """Get a report by ID with eager loading of relationships."""
        stmt = (
            select(Report)
            .options(
                selectinload(Report.selected_deals).selectinload(ReportDeal.selected_tranches),
                selectinload(Report.selected_calculations)
            )
            .where(Report.id == report_id)
        )
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_created_by(self, created_by: str) -> List[Report]:
        """Get reports by creator with relationships loaded"""
        stmt = (
            select(Report)
            .where(Report.created_by == created_by, Report.is_active == True)
            .order_by(Report.created_date.desc())
            .options(
                selectinload(Report.selected_deals).selectinload(ReportDeal.selected_tranches),
                selectinload(Report.selected_calculations)
            )
        )
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_name_and_creator(self, name: str, created_by: str) -> Optional[Report]:
        """Get a report by name and creator"""
        stmt = select(Report).where(
            Report.name == name, 
            Report.created_by == created_by,
            Report.is_active == True
        )
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def create(self, report: Report) -> Report:
        """Create a new report with all relationships"""
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    async def update(self, report: Report) -> Report:
        """Update an existing report"""
        self.db.commit()
        self.db.refresh(report)
        return report

    async def delete(self, report_id: int) -> bool:
        """Soft delete a report by ID"""
        report = await self.get_by_id(report_id)
        if report:
            report.is_active = False
            await self.update(report)
            return True
        return False

    async def hard_delete(self, report_id: int) -> bool:
        """Hard delete a report by ID (cascade will handle deals, tranches, and calculations)"""
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
            .options(
                selectinload(Report.selected_deals).selectinload(ReportDeal.selected_tranches),
                selectinload(Report.selected_calculations)
            )
        )
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    # Helper methods for granular operations
    async def add_deal_to_report(self, report_id: int, deal_id: int) -> Optional[ReportDeal]:
        """Add a deal to a report"""
        report_deal = ReportDeal(report_id=report_id, dl_nbr=deal_id)
        self.db.add(report_deal)
        self.db.commit()
        self.db.refresh(report_deal)
        return report_deal

    async def remove_deal_from_report(self, report_id: int, deal_id: int) -> bool:
        """Remove a deal from a report (cascade will handle tranches)"""
        stmt = select(ReportDeal).where(
            ReportDeal.report_id == report_id,
            ReportDeal.dl_nbr == deal_id
        )
        result = self.db.execute(stmt)
        report_deal = result.scalars().first()
        
        if report_deal:
            self.db.delete(report_deal)
            self.db.commit()
            return True
        return False

    async def add_calculation_to_report(self, report_id: int, calculation_id: int, display_order: int = 0) -> Optional[ReportCalculation]:
        """Add a calculation to a report"""
        report_calculation = ReportCalculation(
            report_id=report_id, 
            calculation_id=calculation_id,
            display_order=display_order
        )
        self.db.add(report_calculation)
        self.db.commit()
        self.db.refresh(report_calculation)
        return report_calculation

    async def remove_calculation_from_report(self, report_id: int, calculation_id: int) -> bool:
        """Remove a calculation from a report"""
        stmt = select(ReportCalculation).where(
            ReportCalculation.report_id == report_id,
            ReportCalculation.calculation_id == calculation_id
        )
        result = self.db.execute(stmt)
        report_calculation = result.scalars().first()
        
        if report_calculation:
            self.db.delete(report_calculation)
            self.db.commit()
            return True
        return False

    def get_execution_logs(self, report_id: int, limit: int = 50):
        """Get recent execution logs for a report"""
        from app.reporting.models import ReportExecutionLog
        
        return self.db.query(ReportExecutionLog)\
            .filter(ReportExecutionLog.report_id == report_id)\
            .order_by(ReportExecutionLog.executed_at.desc())\
            .limit(limit).all()