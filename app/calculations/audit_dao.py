# app/calculations/audit_dao.py
"""Data Access Object for Calculation Audit Logs."""

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.calculations.audit_models import CalculationAuditLog


class CalculationAuditDAO:
    """DAO for calculation audit log operations."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def get_by_id(self, audit_id: int) -> Optional[CalculationAuditLog]:
        """Get audit log by ID."""
        return self.db.query(CalculationAuditLog).filter(CalculationAuditLog.id == audit_id).first()

    def get_audit_logs_for_calculation(
        self, 
        table_name: str, 
        record_id: int, 
        limit: int = 50
    ) -> List[CalculationAuditLog]:
        """Get audit logs for a specific calculation, most recent first."""
        return (
            self.db.query(CalculationAuditLog)
            .filter(
                CalculationAuditLog.table_name == table_name,
                CalculationAuditLog.record_id == record_id
            )
            .order_by(desc(CalculationAuditLog.changed_at))
            .limit(limit)
            .all()
        )

    def get_recent_audit_logs(self, limit: int = 100) -> List[CalculationAuditLog]:
        """Get recent audit logs across all calculations."""
        return (
            self.db.query(CalculationAuditLog)
            .order_by(desc(CalculationAuditLog.changed_at))
            .limit(limit)
            .all()
        )

    def get_audit_logs_by_user(
        self, 
        changed_by: str, 
        limit: int = 100
    ) -> List[CalculationAuditLog]:
        """Get audit logs for a specific user."""
        return (
            self.db.query(CalculationAuditLog)
            .filter(CalculationAuditLog.changed_by == changed_by)
            .order_by(desc(CalculationAuditLog.changed_at))
            .limit(limit)
            .all()
        )

    def get_audit_logs_by_operation(
        self, 
        operation: str, 
        limit: int = 100
    ) -> List[CalculationAuditLog]:
        """Get audit logs for a specific operation type (INSERT, UPDATE, DELETE)."""
        return (
            self.db.query(CalculationAuditLog)
            .filter(CalculationAuditLog.operation == operation)
            .order_by(desc(CalculationAuditLog.changed_at))
            .limit(limit)
            .all()
        )

    def get_audit_logs_by_table(
        self, 
        table_name: str, 
        limit: int = 100
    ) -> List[CalculationAuditLog]:
        """Get audit logs for a specific table (user_calculations or system_calculations)."""
        return (
            self.db.query(CalculationAuditLog)
            .filter(CalculationAuditLog.table_name == table_name)
            .order_by(desc(CalculationAuditLog.changed_at))
            .limit(limit)
            .all()
        )

    def get_audit_logs_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        table_name: Optional[str] = None,
        operation: Optional[str] = None,
        changed_by: Optional[str] = None
    ) -> List[CalculationAuditLog]:
        """Get audit logs within a date range with optional filters."""
        query = self.db.query(CalculationAuditLog).filter(
            and_(
                CalculationAuditLog.changed_at >= start_date,
                CalculationAuditLog.changed_at <= end_date
            )
        )
        
        if table_name:
            query = query.filter(CalculationAuditLog.table_name == table_name)
        
        if operation:
            query = query.filter(CalculationAuditLog.operation == operation)
        
        if changed_by:
            query = query.filter(CalculationAuditLog.changed_by == changed_by)
        
        return query.order_by(desc(CalculationAuditLog.changed_at)).all()

    def search_audit_logs(
        self,
        record_ids: Optional[List[int]] = None,
        table_names: Optional[List[str]] = None,
        operations: Optional[List[str]] = None,
        users: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[CalculationAuditLog]:
        """Advanced search for audit logs with multiple filters."""
        query = self.db.query(CalculationAuditLog)
        
        # Apply filters
        if record_ids:
            query = query.filter(CalculationAuditLog.record_id.in_(record_ids))
        
        if table_names:
            query = query.filter(CalculationAuditLog.table_name.in_(table_names))
        
        if operations:
            query = query.filter(CalculationAuditLog.operation.in_(operations))
        
        if users:
            query = query.filter(CalculationAuditLog.changed_by.in_(users))
        
        if start_date:
            query = query.filter(CalculationAuditLog.changed_at >= start_date)
        
        if end_date:
            query = query.filter(CalculationAuditLog.changed_at <= end_date)
        
        return query.order_by(desc(CalculationAuditLog.changed_at)).limit(limit).all()

    def get_audit_statistics(self, days_back: int = 30) -> Dict[str, Any]:
        """Get audit statistics for the last N days."""
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        logs = self.db.query(CalculationAuditLog).filter(
            CalculationAuditLog.changed_at >= cutoff_date
        ).all()

        if not logs:
            return {
                "period_days": days_back,
                "total_changes": 0,
                "by_operation": {},
                "by_table": {},
                "by_user": {},
                "unique_calculations_changed": 0,
                "most_active_users": [],
                "recent_activity_trend": []
            }

        # Group by operation
        by_operation = {}
        for log in logs:
            by_operation[log.operation] = by_operation.get(log.operation, 0) + 1

        # Group by table
        by_table = {}
        for log in logs:
            by_table[log.table_name] = by_table.get(log.table_name, 0) + 1

        # Group by user
        by_user = {}
        for log in logs:
            if log.changed_by:
                by_user[log.changed_by] = by_user.get(log.changed_by, 0) + 1

        # Count unique calculations changed
        unique_calcs = set()
        for log in logs:
            unique_calcs.add(f"{log.table_name}:{log.record_id}")

        # Most active users (top 10)
        most_active = sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "period_days": days_back,
            "total_changes": len(logs),
            "by_operation": by_operation,
            "by_table": by_table,
            "by_user": by_user,
            "unique_calculations_changed": len(unique_calcs),
            "most_active_users": [{"user": user, "changes": count} for user, count in most_active],
            "start_date": cutoff_date.isoformat(),
            "end_date": datetime.now().isoformat()
        }

    def get_calculation_change_history(
        self, 
        table_name: str, 
        record_id: int
    ) -> Dict[str, Any]:
        """Get detailed change history for a specific calculation."""
        logs = self.get_audit_logs_for_calculation(table_name, record_id, limit=1000)
        
        if not logs:
            return {
                "table_name": table_name,
                "record_id": record_id,
                "total_changes": 0,
                "created_at": None,
                "created_by": None,
                "last_modified_at": None,
                "last_modified_by": None,
                "change_summary": {},
                "detailed_history": []
            }

        # Find creation event
        creation_log = None
        for log in reversed(logs):  # Start from oldest
            if log.operation == 'INSERT':
                creation_log = log
                break

        # Find last modification
        last_modification = logs[0] if logs else None

        # Count changes by field
        field_changes = {}
        for log in logs:
            if log.operation == 'UPDATE' and log.changed_fields:
                for field in log.changed_fields:
                    field_changes[field] = field_changes.get(field, 0) + 1

        # Build detailed history
        detailed_history = []
        for log in logs:
            history_entry = {
                "id": log.id,
                "operation": log.operation,
                "changed_by": log.changed_by,
                "changed_at": log.changed_at.isoformat() if log.changed_at else None,
                "changed_fields": log.changed_fields or [],
                "old_values": log.old_values,
                "new_values": log.new_values
            }
            
            # Add summary for updates
            if log.operation == 'UPDATE' and log.old_values and log.new_values:
                changes_summary = []
                for field in (log.changed_fields or []):
                    old_val = log.old_values.get(field)
                    new_val = log.new_values.get(field)
                    changes_summary.append({
                        "field": field,
                        "old_value": old_val,
                        "new_value": new_val
                    })
                history_entry["changes_summary"] = changes_summary
            
            detailed_history.append(history_entry)

        return {
            "table_name": table_name,
            "record_id": record_id,
            "total_changes": len(logs),
            "created_at": creation_log.changed_at.isoformat() if creation_log and creation_log.changed_at else None,
            "created_by": creation_log.changed_by if creation_log else None,
            "last_modified_at": last_modification.changed_at.isoformat() if last_modification and last_modification.changed_at else None,
            "last_modified_by": last_modification.changed_by if last_modification else None,
            "field_change_counts": field_changes,
            "detailed_history": detailed_history
        }

    def cleanup_old_audit_logs(self, days_to_keep: int = 365) -> int:
        """Clean up audit logs older than specified days. Returns count of deleted records."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        deleted_count = self.db.query(CalculationAuditLog).filter(
            CalculationAuditLog.changed_at < cutoff_date
        ).delete()
        
        self.db.commit()
        return deleted_count

    def delete(self, audit_id: int) -> bool:
        """Delete a specific audit log (use with caution)."""
        audit_log = self.get_by_id(audit_id)
        if audit_log:
            self.db.delete(audit_log)
            self.db.commit()
            return True
        return False