# app/calculations/audit_service.py
"""Service for managing calculation audit logs."""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.calculations.audit_dao import CalculationAuditDAO
from app.calculations.audit_models import CalculationAuditLog


class CalculationAuditService:
    """Service for managing calculation audit logs with business logic."""

    def __init__(self, audit_dao: CalculationAuditDAO):
        self.audit_dao = audit_dao

    def get_audit_history_for_calculation(
        self, 
        calculation_type: str, 
        calculation_id: int, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get audit history for a specific calculation."""
        
        # Validate calculation type
        if calculation_type not in ['user', 'system']:
            raise ValueError("calculation_type must be 'user' or 'system'")
        
        table_name = f"{calculation_type}_calculations"
        logs = self.audit_dao.get_audit_logs_for_calculation(table_name, calculation_id, limit)
        
        return [self._format_audit_log(log) for log in logs]

    def get_recent_audit_activity(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit activity across all calculations."""
        logs = self.audit_dao.get_recent_audit_logs(limit)
        return [self._format_audit_log(log) for log in logs]

    def get_audit_activity_by_user(
        self, 
        username: str, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit activity for a specific user."""
        if not username or not username.strip():
            raise ValueError("Username cannot be empty")
        
        logs = self.audit_dao.get_audit_logs_by_user(username.strip(), limit)
        return [self._format_audit_log(log) for log in logs]

    def get_audit_activity_by_operation(
        self, 
        operation: str, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit activity for a specific operation type."""
        
        # Validate operation
        valid_operations = ['INSERT', 'UPDATE', 'DELETE']
        if operation.upper() not in valid_operations:
            raise ValueError(f"Operation must be one of: {', '.join(valid_operations)}")
        
        logs = self.audit_dao.get_audit_logs_by_operation(operation.upper(), limit)
        return [self._format_audit_log(log) for log in logs]

    def get_audit_activity_by_calculation_type(
        self, 
        calculation_type: str, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit activity for a specific calculation type (user or system)."""
        
        if calculation_type not in ['user', 'system']:
            raise ValueError("calculation_type must be 'user' or 'system'")
        
        table_name = f"{calculation_type}_calculations"
        logs = self.audit_dao.get_audit_logs_by_table(table_name, limit)
        return [self._format_audit_log(log) for log in logs]

    def search_audit_logs(
        self,
        calculation_ids: Optional[List[int]] = None,
        calculation_types: Optional[List[str]] = None,
        operations: Optional[List[str]] = None,
        users: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Advanced search for audit logs."""
        
        # Validate calculation types
        if calculation_types:
            valid_types = ['user', 'system']
            invalid_types = [t for t in calculation_types if t not in valid_types]
            if invalid_types:
                raise ValueError(f"Invalid calculation types: {', '.join(invalid_types)}")
        
        # Validate operations
        if operations:
            valid_operations = ['INSERT', 'UPDATE', 'DELETE']
            invalid_ops = [op for op in operations if op.upper() not in valid_operations]
            if invalid_ops:
                raise ValueError(f"Invalid operations: {', '.join(invalid_ops)}")
            operations = [op.upper() for op in operations]
        
        # Validate date range
        if start_date and end_date and start_date > end_date:
            raise ValueError("Start date cannot be after end date")
        
        # Convert calculation types to table names
        table_names = None
        if calculation_types:
            table_names = [f"{calc_type}_calculations" for calc_type in calculation_types]
        
        logs = self.audit_dao.search_audit_logs(
            record_ids=calculation_ids,
            table_names=table_names,
            operations=operations,
            users=users,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        return [self._format_audit_log(log) for log in logs]

    def get_audit_statistics(self, days_back: int = 30) -> Dict[str, Any]:
        """Get audit statistics for dashboard display."""
        
        if days_back < 1 or days_back > 365:
            raise ValueError("days_back must be between 1 and 365")
        
        stats = self.audit_dao.get_audit_statistics(days_back)
        
        # Add calculated fields for better display
        if stats["total_changes"] > 0:
            # Calculate percentage breakdowns
            stats["operation_percentages"] = {
                op: round(count / stats["total_changes"] * 100, 1)
                for op, count in stats["by_operation"].items()
            }
            
            stats["table_percentages"] = {
                table: round(count / stats["total_changes"] * 100, 1)
                for table, count in stats["by_table"].items()
            }
            
            # Format table names for display
            stats["by_table_display"] = {}
            for table, count in stats["by_table"].items():
                display_name = "User Calculations" if table == "user_calculations" else "System Calculations"
                stats["by_table_display"][display_name] = count
        
        # Add trends and insights
        stats["daily_average"] = round(stats["total_changes"] / days_back, 1)
        stats["insights"] = self._generate_audit_insights(stats)
        
        return stats

    def get_calculation_change_timeline(
        self, 
        calculation_type: str, 
        calculation_id: int
    ) -> Dict[str, Any]:
        """Get detailed change timeline for a specific calculation."""
        
        if calculation_type not in ['user', 'system']:
            raise ValueError("calculation_type must be 'user' or 'system'")
        
        table_name = f"{calculation_type}_calculations"
        timeline = self.audit_dao.get_calculation_change_history(table_name, calculation_id)
        
        # Add formatted timeline for UI display
        if timeline["detailed_history"]:
            timeline["formatted_timeline"] = self._format_change_timeline(timeline["detailed_history"])
        
        return timeline

    def get_audit_trends(self, days_back: int = 30) -> Dict[str, Any]:
        """Get audit activity trends for analytics."""
        
        if days_back < 7 or days_back > 365:
            raise ValueError("days_back must be between 7 and 365")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        logs = self.audit_dao.get_audit_logs_by_date_range(start_date, end_date)
        
        # Group by date
        daily_activity = {}
        for log in logs:
            date_key = log.changed_at.date().isoformat()
            if date_key not in daily_activity:
                daily_activity[date_key] = {
                    "date": date_key,
                    "total_changes": 0,
                    "inserts": 0,
                    "updates": 0,
                    "deletes": 0,
                    "user_calc_changes": 0,
                    "system_calc_changes": 0,
                    "unique_users": set()
                }
            
            daily_activity[date_key]["total_changes"] += 1
            daily_activity[date_key][log.operation.lower() + "s"] += 1
            
            if log.table_name == "user_calculations":
                daily_activity[date_key]["user_calc_changes"] += 1
            else:
                daily_activity[date_key]["system_calc_changes"] += 1
            
            if log.changed_by:
                daily_activity[date_key]["unique_users"].add(log.changed_by)

        # Convert to list and format
        trend_data = []
        for stats in daily_activity.values():
            # Convert set to count
            stats["unique_users"] = len(stats["unique_users"])
            trend_data.append(stats)

        # Sort by date
        trend_data.sort(key=lambda x: x["date"])
        
        return {
            "period_days": days_back,
            "start_date": start_date.date().isoformat(),
            "end_date": end_date.date().isoformat(),
            "daily_trends": trend_data,
            "summary": {
                "total_days_with_activity": len(daily_activity),
                "total_changes": sum(day["total_changes"] for day in daily_activity.values()),
                "busiest_day": max(daily_activity.values(), key=lambda x: x["total_changes"]) if daily_activity else None,
                "average_daily_changes": (
                    sum(day["total_changes"] for day in daily_activity.values()) / len(daily_activity)
                    if daily_activity else 0
                )
            }
        }

    def cleanup_old_audit_logs(self, days_to_keep: int = 365) -> Dict[str, Any]:
        """Clean up old audit logs with validation."""
        
        if days_to_keep < 30:
            raise ValueError("Cannot retain audit logs for less than 30 days")
        
        if days_to_keep > 3650:  # 10 years
            raise ValueError("Retention period cannot exceed 10 years")

        deleted_count = self.audit_dao.cleanup_old_audit_logs(days_to_keep)
        
        return {
            "deleted_count": deleted_count,
            "retention_days": days_to_keep,
            "cleanup_date": datetime.now().isoformat()
        }

    def _format_audit_log(self, log: CalculationAuditLog) -> Dict[str, Any]:
        """Format audit log for API response."""
        
        # Determine calculation type from table name
        calc_type = "user" if log.table_name == "user_calculations" else "system"
        
        formatted = {
            "id": log.id,
            "calculation_type": calc_type,
            "calculation_id": log.record_id,
            "operation": log.operation,
            "changed_by": log.changed_by,
            "changed_at": log.changed_at.isoformat() if log.changed_at else None,
            "changed_fields": log.changed_fields or [],
            "old_values": log.old_values,
            "new_values": log.new_values
        }
        
        # Add human-readable summary
        if log.operation == 'INSERT':
            formatted["summary"] = f"Created {calc_type} calculation"
        elif log.operation == 'UPDATE':
            field_count = len(log.changed_fields) if log.changed_fields else 0
            formatted["summary"] = f"Updated {field_count} field(s) in {calc_type} calculation"
        elif log.operation == 'DELETE':
            formatted["summary"] = f"Deleted {calc_type} calculation"
        
        # Add change details for updates
        if log.operation == 'UPDATE' and log.old_values and log.new_values and log.changed_fields:
            formatted["change_details"] = []
            for field in log.changed_fields:
                old_val = log.old_values.get(field)
                new_val = log.new_values.get(field)
                formatted["change_details"].append({
                    "field": field,
                    "old_value": old_val,
                    "new_value": new_val
                })
        
        return formatted

    def _format_change_timeline(self, detailed_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format change history for timeline display."""
        timeline = []
        
        for entry in detailed_history:
            timeline_entry = {
                "timestamp": entry["changed_at"],
                "user": entry["changed_by"] or "Unknown",
                "operation": entry["operation"],
                "description": self._get_operation_description(entry)
            }
            
            if entry["operation"] == "UPDATE" and entry.get("changes_summary"):
                timeline_entry["changes"] = entry["changes_summary"]
            
            timeline.append(timeline_entry)
        
        return timeline

    def _get_operation_description(self, entry: Dict[str, Any]) -> str:
        """Generate human-readable description for an operation."""
        operation = entry["operation"]
        
        if operation == "INSERT":
            return "Calculation created"
        elif operation == "DELETE":
            return "Calculation deleted"
        elif operation == "UPDATE":
            changed_fields = entry.get("changed_fields", [])
            if len(changed_fields) == 1:
                return f"Updated {changed_fields[0]}"
            elif len(changed_fields) > 1:
                return f"Updated {len(changed_fields)} fields: {', '.join(changed_fields[:3])}" + (
                    f" and {len(changed_fields) - 3} more" if len(changed_fields) > 3 else ""
                )
            else:
                return "Updated calculation"
        
        return f"Performed {operation.lower()} operation"

    def _generate_audit_insights(self, stats: Dict[str, Any]) -> List[str]:
        """Generate insights from audit statistics."""
        insights = []
        
        if stats["total_changes"] == 0:
            insights.append("No calculation changes recorded in this period")
            return insights
        
        # Most active operation
        if stats["by_operation"]:
            most_common_op = max(stats["by_operation"].items(), key=lambda x: x[1])
            insights.append(f"Most common operation: {most_common_op[0]} ({most_common_op[1]} times)")
        
        # User activity
        if stats["by_user"]:
            user_count = len(stats["by_user"])
            insights.append(f"Activity from {user_count} user(s)")
            
            if user_count == 1:
                insights.append("All changes made by a single user")
            elif user_count > 5:
                insights.append("High user activity - many people making changes")
        
        # Calculation type preference
        if stats["by_table"]:
            user_changes = stats["by_table"].get("user_calculations", 0)
            system_changes = stats["by_table"].get("system_calculations", 0)
            
            if user_changes > system_changes * 2:
                insights.append("Primarily user calculation changes")
            elif system_changes > user_changes * 2:
                insights.append("Primarily system calculation changes")
            else:
                insights.append("Balanced activity between user and system calculations")
        
        # Activity level
        daily_avg = stats["total_changes"] / stats["period_days"]
        if daily_avg < 1:
            insights.append("Low activity period")
        elif daily_avg > 10:
            insights.append("High activity period")
        
        return insights