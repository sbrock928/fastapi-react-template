"""Simplified Data Access Objects for the reporting module."""

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime
from app.reporting.models import Report, ReportDeal, ReportTranche, ReportCalculation, ReportExecutionLog


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

    # ===== EXECUTION LOG METHODS =====

    async def create_execution_log(self, execution_log: ReportExecutionLog) -> ReportExecutionLog:
        """Create a new execution log entry."""
        self.db.add(execution_log)
        self.db.commit()
        self.db.refresh(execution_log)
        return execution_log

    async def get_execution_logs(self, report_id: int, limit: int = 50) -> List[ReportExecutionLog]:
        """Get execution logs for a report, ordered by most recent first."""
        stmt = (
            select(ReportExecutionLog)
            .where(ReportExecutionLog.report_id == report_id)
            .order_by(ReportExecutionLog.executed_at.desc())
            .limit(limit)
        )
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_execution_log_stats(self, report_id: int) -> dict:
        """Get execution statistics for a report."""
        from sqlalchemy import func
        
        stmt = (
            select(
                func.count(ReportExecutionLog.id).label('total_executions'),
                func.max(ReportExecutionLog.executed_at).label('last_executed'),
                func.sum(func.case((ReportExecutionLog.success == True, 1), else_=0)).label('successful_executions')
            )
            .where(ReportExecutionLog.report_id == report_id)
        )
        result = self.db.execute(stmt).first()
        
        if result and result.total_executions:
            return {
                'total_executions': result.total_executions,
                'last_executed': result.last_executed,
                'last_execution_success': None if result.total_executions == 0 else (
                    # Get the success status of the most recent execution
                    self.db.execute(
                        select(ReportExecutionLog.success)
                        .where(ReportExecutionLog.report_id == report_id)
                        .order_by(ReportExecutionLog.executed_at.desc())
                        .limit(1)
                    ).scalar()
                )
            }
        
        return {
            'total_executions': 0,
            'last_executed': None,
            'last_execution_success': None
        }
