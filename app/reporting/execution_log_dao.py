# app/reporting/execution_log_dao.py
"""Data Access Object for Report Execution Logs."""

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.reporting.models import ReportExecutionLog


class ReportExecutionLogDAO:
    """DAO for report execution log operations."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def create(self, execution_log: ReportExecutionLog) -> ReportExecutionLog:
        """Create a new execution log entry."""
        self.db.add(execution_log)
        self.db.commit()
        self.db.refresh(execution_log)
        return execution_log

    def get_by_id(self, log_id: int) -> Optional[ReportExecutionLog]:
        """Get execution log by ID."""
        return self.db.query(ReportExecutionLog).filter(ReportExecutionLog.id == log_id).first()

    def get_by_report_id(self, report_id: int, limit: int = 50) -> List[ReportExecutionLog]:
        """Get execution logs for a specific report, most recent first."""
        return (
            self.db.query(ReportExecutionLog)
            .filter(ReportExecutionLog.report_id == report_id)
            .order_by(desc(ReportExecutionLog.executed_at))
            .limit(limit)
            .all()
        )

    def get_recent_executions(self, limit: int = 100) -> List[ReportExecutionLog]:
        """Get recent execution logs across all reports."""
        return (
            self.db.query(ReportExecutionLog)
            .order_by(desc(ReportExecutionLog.executed_at))
            .limit(limit)
            .all()
        )

    def get_executions_by_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime,
        report_id: Optional[int] = None
    ) -> List[ReportExecutionLog]:
        """Get execution logs within a date range."""
        query = self.db.query(ReportExecutionLog).filter(
            and_(
                ReportExecutionLog.executed_at >= start_date,
                ReportExecutionLog.executed_at <= end_date
            )
        )
        
        if report_id:
            query = query.filter(ReportExecutionLog.report_id == report_id)
            
        return query.order_by(desc(ReportExecutionLog.executed_at)).all()

    def get_failed_executions(self, limit: int = 50) -> List[ReportExecutionLog]:
        """Get recent failed execution logs."""
        return (
            self.db.query(ReportExecutionLog)
            .filter(ReportExecutionLog.success == False)
            .order_by(desc(ReportExecutionLog.executed_at))
            .limit(limit)
            .all()
        )

    def get_execution_stats_by_report(self, report_id: int) -> Dict[str, Any]:
        """Get execution statistics for a specific report."""
        logs = self.db.query(ReportExecutionLog).filter(
            ReportExecutionLog.report_id == report_id
        ).all()

        if not logs:
            return {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "success_rate": 0.0,
                "average_execution_time_ms": 0.0,
                "last_execution_date": None,
                "last_successful_execution": None
            }

        successful_logs = [log for log in logs if log.success]
        failed_logs = [log for log in logs if not log.success]
        
        # Calculate average execution time for successful runs
        execution_times = [
            log.execution_time_ms for log in successful_logs 
            if log.execution_time_ms is not None
        ]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0.0

        # Get most recent execution dates
        sorted_logs = sorted(logs, key=lambda x: x.executed_at, reverse=True)
        successful_sorted = sorted(successful_logs, key=lambda x: x.executed_at, reverse=True)

        return {
            "total_executions": len(logs),
            "successful_executions": len(successful_logs),
            "failed_executions": len(failed_logs),
            "success_rate": (len(successful_logs) / len(logs) * 100) if logs else 0.0,
            "average_execution_time_ms": avg_execution_time,
            "last_execution_date": sorted_logs[0].executed_at if sorted_logs else None,
            "last_successful_execution": successful_sorted[0].executed_at if successful_sorted else None
        }

    def get_performance_metrics(self, days_back: int = 30) -> Dict[str, Any]:
        """Get performance metrics for the last N days."""
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        recent_logs = self.db.query(ReportExecutionLog).filter(
            ReportExecutionLog.executed_at >= cutoff_date
        ).all()

        if not recent_logs:
            return {
                "period_days": days_back,
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "average_execution_time_ms": 0.0,
                "min_execution_time_ms": 0.0,
                "max_execution_time_ms": 0.0,
                "reports_executed": 0
            }

        successful_logs = [log for log in recent_logs if log.success]
        execution_times = [
            log.execution_time_ms for log in successful_logs 
            if log.execution_time_ms is not None
        ]
        
        unique_reports = set(log.report_id for log in recent_logs)

        return {
            "period_days": days_back,
            "total_executions": len(recent_logs),
            "successful_executions": len(successful_logs),
            "failed_executions": len(recent_logs) - len(successful_logs),
            "average_execution_time_ms": sum(execution_times) / len(execution_times) if execution_times else 0.0,
            "min_execution_time_ms": min(execution_times) if execution_times else 0.0,
            "max_execution_time_ms": max(execution_times) if execution_times else 0.0,
            "reports_executed": len(unique_reports)
        }

    def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        """Clean up execution logs older than specified days. Returns count of deleted records."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        deleted_count = self.db.query(ReportExecutionLog).filter(
            ReportExecutionLog.executed_at < cutoff_date
        ).delete()
        
        self.db.commit()
        return deleted_count

    def delete(self, log_id: int) -> bool:
        """Delete a specific execution log."""
        log = self.get_by_id(log_id)
        if log:
            self.db.delete(log)
            self.db.commit()
            return True
        return False