# app/reporting/execution_log_service.py
"""Service for managing report execution logs."""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.reporting.execution_log_dao import ReportExecutionLogDAO
from app.reporting.models import ReportExecutionLog


class ReportExecutionLogService:
    """Service for managing report execution logs with business logic."""

    def __init__(self, execution_log_dao: ReportExecutionLogDAO):
        self.execution_log_dao = execution_log_dao

    def log_execution(
        self,
        report_id: int,
        cycle_code: int,
        executed_by: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
        row_count: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> ReportExecutionLog:
        """Log a report execution with all relevant metrics."""
        
        # Validate inputs
        if execution_time_ms is not None and execution_time_ms < 0:
            execution_time_ms = 0.0
            
        if row_count is not None and row_count < 0:
            row_count = 0

        # Truncate error message if too long
        if error_message and len(error_message) > 1000:
            error_message = error_message[:997] + "..."

        execution_log = ReportExecutionLog(
            report_id=report_id,
            cycle_code=cycle_code,
            executed_by=executed_by,
            execution_time_ms=execution_time_ms,
            row_count=row_count,
            success=success,
            error_message=error_message,
            executed_at=datetime.now()
        )

        return self.execution_log_dao.create(execution_log)

    def get_execution_logs_for_report(
        self, 
        report_id: int, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get execution logs for a specific report formatted for API response."""
        logs = self.execution_log_dao.get_by_report_id(report_id, limit)
        
        return [
            {
                "id": log.id,
                "report_id": log.report_id,
                "cycle_code": log.cycle_code,
                "executed_by": log.executed_by,
                "execution_time_ms": log.execution_time_ms,
                "row_count": log.row_count,
                "success": log.success,
                "error_message": log.error_message,
                "executed_at": log.executed_at.isoformat() if log.executed_at else None
            }
            for log in logs
        ]

    def get_recent_executions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent execution logs across all reports."""
        logs = self.execution_log_dao.get_recent_executions(limit)
        
        return [
            {
                "id": log.id,
                "report_id": log.report_id,
                "cycle_code": log.cycle_code,
                "executed_by": log.executed_by,
                "execution_time_ms": log.execution_time_ms,
                "row_count": log.row_count,
                "success": log.success,
                "error_message": log.error_message,
                "executed_at": log.executed_at.isoformat() if log.executed_at else None
            }
            for log in logs
        ]

    def get_execution_stats_for_report(self, report_id: int) -> Dict[str, Any]:
        """Get comprehensive execution statistics for a report."""
        return self.execution_log_dao.get_execution_stats_by_report(report_id)

    def get_failed_executions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent failed executions for troubleshooting."""
        logs = self.execution_log_dao.get_failed_executions(limit)
        
        return [
            {
                "id": log.id,
                "report_id": log.report_id,
                "cycle_code": log.cycle_code,
                "executed_by": log.executed_by,
                "execution_time_ms": log.execution_time_ms,
                "error_message": log.error_message,
                "executed_at": log.executed_at.isoformat() if log.executed_at else None
            }
            for log in logs
        ]

    def get_performance_dashboard(self, days_back: int = 30) -> Dict[str, Any]:
        """Get performance metrics for dashboard display."""
        metrics = self.execution_log_dao.get_performance_metrics(days_back)
        
        # Add some calculated fields for better dashboard display
        if metrics["total_executions"] > 0:
            metrics["success_rate"] = (
                metrics["successful_executions"] / metrics["total_executions"] * 100
            )
            metrics["failure_rate"] = (
                (metrics["total_executions"] - metrics["successful_executions"]) / 
                metrics["total_executions"] * 100
            )
        else:
            metrics["success_rate"] = 0.0
            metrics["failure_rate"] = 0.0

        # Format execution times for display
        if metrics["average_execution_time_ms"] > 0:
            if metrics["average_execution_time_ms"] < 1000:
                metrics["average_execution_time_display"] = f"{metrics['average_execution_time_ms']:.1f} ms"
            else:
                metrics["average_execution_time_display"] = f"{metrics['average_execution_time_ms']/1000:.2f} sec"
        else:
            metrics["average_execution_time_display"] = "N/A"

        return metrics

    def get_executions_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        report_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get execution logs within a specific date range."""
        # Validate date range
        if start_date > end_date:
            raise ValueError("Start date cannot be after end date")
        
        # Limit date range to prevent excessive data retrieval
        max_days = 365
        if (end_date - start_date).days > max_days:
            raise ValueError(f"Date range cannot exceed {max_days} days")

        logs = self.execution_log_dao.get_executions_by_date_range(
            start_date, end_date, report_id
        )
        
        return [
            {
                "id": log.id,
                "report_id": log.report_id,
                "cycle_code": log.cycle_code,
                "executed_by": log.executed_by,
                "execution_time_ms": log.execution_time_ms,
                "row_count": log.row_count,
                "success": log.success,
                "error_message": log.error_message,
                "executed_at": log.executed_at.isoformat() if log.executed_at else None
            }
            for log in logs
        ]

    def cleanup_old_logs(self, days_to_keep: int = 90) -> Dict[str, Any]:
        """Clean up old execution logs with validation."""
        # Validate retention period
        if days_to_keep < 7:
            raise ValueError("Cannot retain logs for less than 7 days")
        
        if days_to_keep > 3650:  # 10 years
            raise ValueError("Retention period cannot exceed 10 years")

        deleted_count = self.execution_log_dao.cleanup_old_logs(days_to_keep)
        
        return {
            "deleted_count": deleted_count,
            "retention_days": days_to_keep,
            "cleanup_date": datetime.now().isoformat()
        }

    def get_execution_trends(self, days_back: int = 30) -> Dict[str, Any]:
        """Get execution trends for analytics."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        logs = self.execution_log_dao.get_executions_by_date_range(start_date, end_date)
        
        # Group by date
        daily_stats = {}
        for log in logs:
            date_key = log.executed_at.date().isoformat()
            if date_key not in daily_stats:
                daily_stats[date_key] = {
                    "date": date_key,
                    "total_executions": 0,
                    "successful_executions": 0,
                    "failed_executions": 0,
                    "total_execution_time_ms": 0.0,
                    "execution_count_with_time": 0
                }
            
            daily_stats[date_key]["total_executions"] += 1
            if log.success:
                daily_stats[date_key]["successful_executions"] += 1
            else:
                daily_stats[date_key]["failed_executions"] += 1
            
            if log.execution_time_ms is not None:
                daily_stats[date_key]["total_execution_time_ms"] += log.execution_time_ms
                daily_stats[date_key]["execution_count_with_time"] += 1

        # Calculate averages and format for charts
        trend_data = []
        for stats in daily_stats.values():
            avg_time = (
                stats["total_execution_time_ms"] / stats["execution_count_with_time"]
                if stats["execution_count_with_time"] > 0 else 0
            )
            
            trend_data.append({
                "date": stats["date"],
                "total_executions": stats["total_executions"],
                "successful_executions": stats["successful_executions"],
                "failed_executions": stats["failed_executions"],
                "success_rate": (
                    stats["successful_executions"] / stats["total_executions"] * 100
                    if stats["total_executions"] > 0 else 0
                ),
                "average_execution_time_ms": avg_time
            })

        # Sort by date
        trend_data.sort(key=lambda x: x["date"])
        
        return {
            "period_days": days_back,
            "start_date": start_date.date().isoformat(),
            "end_date": end_date.date().isoformat(),
            "daily_trends": trend_data,
            "summary": {
                "total_days_with_data": len(daily_stats),
                "total_executions": sum(log.total_executions for log in daily_stats.values()),
                "overall_success_rate": (
                    sum(log.successful_executions for log in daily_stats.values()) /
                    sum(log.total_executions for log in daily_stats.values()) * 100
                    if any(log.total_executions for log in daily_stats.values()) else 0
                )
            }
        }