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

    async def create(self, report_data, column_prefs_json=None) -> Report:
        """Create a new report with all relationships and column preferences."""
        # Convert Pydantic schema to SQLAlchemy model
        report = Report(
            name=report_data.name,
            description=report_data.description,
            scope=report_data.scope.value,
            created_by=report_data.created_by,
            is_active=report_data.is_active,
            column_preferences=column_prefs_json  # Store as JSON
        )
        
        self.db.add(report)
        self.db.flush()  # Get the report ID
        
        # Add selected deals and their tranches
        for deal_data in report_data.selected_deals:
            report_deal = ReportDeal(
                report_id=report.id,
                dl_nbr=deal_data.dl_nbr
            )
            self.db.add(report_deal)
            self.db.flush()  # Get the deal ID
            
            # Add selected tranches for this deal
            for tranche_data in deal_data.selected_tranches:
                report_tranche = ReportTranche(
                    report_deal_id=report_deal.id,
                    dl_nbr=tranche_data.dl_nbr or deal_data.dl_nbr,
                    tr_id=tranche_data.tr_id
                )
                self.db.add(report_tranche)
        
        # Add selected calculations
        for calc_data in report_data.selected_calculations:
            report_calc = ReportCalculation(
                report_id=report.id,
                calculation_id=str(calc_data.calculation_id),
                calculation_type=calc_data.calculation_type,
                display_order=calc_data.display_order,
                display_name=calc_data.display_name
            )
            self.db.add(report_calc)
        
        self.db.commit()
        self.db.refresh(report)
        return report

    async def update(self, report_id: int, report_data, column_prefs_json=None) -> Optional[Report]:
        """Update an existing report with relationships and column preferences."""
        report = await self.get_by_id(report_id)
        if not report:
            return None
        
        # Update basic fields if provided
        if hasattr(report_data, 'name') and report_data.name is not None:
            report.name = report_data.name
        if hasattr(report_data, 'description') and report_data.description is not None:
            report.description = report_data.description
        if hasattr(report_data, 'scope') and report_data.scope is not None:
            report.scope = report_data.scope.value if hasattr(report_data.scope, 'value') else report_data.scope
        if hasattr(report_data, 'is_active') and report_data.is_active is not None:
            report.is_active = report_data.is_active
        
        # Update column preferences if provided
        if column_prefs_json is not None:
            report.column_preferences = column_prefs_json
        
        report.updated_date = datetime.now()
        
        # Update deals and calculations if provided
        if hasattr(report_data, 'selected_deals') and report_data.selected_deals is not None:
            # Clear existing deals and tranches
            for deal in report.selected_deals:
                self.db.delete(deal)
            self.db.flush()
            
            # Add new deals and tranches
            for deal_data in report_data.selected_deals:
                report_deal = ReportDeal(
                    report_id=report.id,
                    dl_nbr=deal_data.dl_nbr
                )
                self.db.add(report_deal)
                self.db.flush()
                
                for tranche_data in deal_data.selected_tranches:
                    report_tranche = ReportTranche(
                        report_deal_id=report_deal.id,
                        dl_nbr=tranche_data.dl_nbr or deal_data.dl_nbr,
                        tr_id=tranche_data.tr_id
                    )
                    self.db.add(report_tranche)
        
        if hasattr(report_data, 'selected_calculations') and report_data.selected_calculations is not None:
            # Clear existing calculations
            for calc in report.selected_calculations:
                self.db.delete(calc)
            self.db.flush()
            
            # Add new calculations
            for calc_data in report_data.selected_calculations:
                report_calc = ReportCalculation(
                    report_id=report.id,
                    calculation_id=str(calc_data.calculation_id),
                    calculation_type=calc_data.calculation_type,
                    display_order=calc_data.display_order,
                    display_name=calc_data.display_name
                )
                self.db.add(report_calc)
        
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
