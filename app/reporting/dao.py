"""Data Access Objects for the reporting module."""

import logging
from sqlalchemy.orm import Session
from sqlalchemy import select, func, text
from typing import List, Dict, Any, Optional
import json
import datetime
from app.resources.models import User, Employee, Subscriber
from app.logging.models import Log


class ReportingDAO:
    """Data access methods for reports and statistics."""

    def __init__(self, session: Session):
        self.session = session

    async def get_user_count(self) -> int:
        """Get the total number of users"""
        result = self.session.execute(select(func.count()).select_from(User))
        return int(result.scalar_one() or 0)

    async def get_employee_count(self) -> int:
        """Get the total number of employees"""
        result = self.session.execute(select(func.count()).select_from(Employee))
        return int(result.scalar_one() or 0)

    async def get_subscriber_count(self) -> int:
        """Get the total number of subscribers"""
        result = self.session.execute(select(func.count()).select_from(Subscriber))
        return int(result.scalar_one() or 0)

    async def get_log_count(self) -> int:
        """Get the total number of logs"""
        result = self.session.execute(select(func.count()).select_from(Log))
        return int(result.scalar_one() or 0)

    async def get_distinct_cycle_codes(self) -> List[Dict[str, str]]:
        """Get a list of all distinct cycle codes from the Cycles table"""
        # SQL query using text() for flexibility
        query = text(
            """
            SELECT DISTINCT code FROM cycles
            ORDER BY code
        """
        )

        try:
            result = self.session.execute(query)
            return [{"code": row[0]} for row in result]
        except Exception:  # pylint: disable=broad-except
            # If the table doesn't exist yet or there's another error
            return []

    async def get_employees_by_department(self) -> List[Dict[str, Any]]:
        """Get employee counts grouped by department"""
        query = (
            select(Employee.department, func.count().label("count"))
            .group_by(Employee.department)
            .order_by(Employee.department)
        )

        result = self.session.execute(query)
        departments = []
        for row in result:
            departments.append(
                {
                    "department": row[0],  # Access by index rather than attribute name
                    "count": row[1],
                }
            )
        return departments

    async def get_resource_counts(self, cycle_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get counts of different resource types

        Args:
            cycle_code: Optional filter, reserved for future implementation
                        when cycle filtering is implemented

        Returns:
            List of dictionaries with resource counts
        """
        # This is a simplified query that doesn't use cycle_code yet
        # Future implementation will use cycle_code for filtering

        user_count = await self.get_user_count()
        employee_count = await self.get_employee_count()
        subscriber_count = await self.get_subscriber_count()

        return [
            {"resource_type": "Users", "count": user_count},
            {"resource_type": "Employees", "count": employee_count},
            {"resource_type": "Subscribers", "count": subscriber_count},
        ]

    async def get_employee_details(self) -> List[Dict[str, Any]]:
        """Get detailed employee information for reporting"""
        # Import needed models/schemas
        from app.resources.models import Employee, Department
        from sqlalchemy import select
        
        try:
            # Query to get employee details with department name
            query = (
                select(Employee, Department.name.label("department_name"))
                .join(Department, Employee.department_id == Department.id)
            )
            
            # Execute query without awaiting
            result = self.session.execute(query)
            
            # Process results into dictionary format
            employee_data = []
            for row in result.all():
                employee = row[0]
                department_name = row[1]
                
                employee_dict = {
                    "id": employee.id,
                    "first_name": employee.first_name,
                    "last_name": employee.last_name,
                    "email": employee.email,
                    "hire_date": employee.hire_date.isoformat() if employee.hire_date else None,
                    "position": employee.position,
                    "department": department_name,
                    "salary": employee.salary,
                    "is_active": employee.is_active,
                }
                employee_data.append(employee_dict)
                
            return employee_data
        except Exception as e:
            logging.error(f"Error in get_employee_details: {str(e)}")
            raise

    async def get_user_details(
        self, 
        username: Optional[str] = None, 
        email: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_superuser: Optional[bool] = None,
        days: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get detailed user information for reporting with filtering options
        
        Args:
            username: Optional filter by username (partial match)
            email: Optional filter by email (partial match)
            is_active: Optional filter by active status (ignored - not in model)
            is_superuser: Optional filter by superuser status (ignored - not in model)
            days: Optional number of days filter (ignored - no date field in User model)
        """
        # Import needed models
        from app.resources.models import User
        from sqlalchemy import select
        
        try:
            # Start building the query
            query = select(User)
            
            # Apply filters if they are provided
            filters = []
            
            if username:
                filters.append(User.username.ilike(f"%{username}%"))
                
            if email:
                filters.append(User.email.ilike(f"%{email}%"))
            
            # Apply filters to query if any exist
            if filters:
                from sqlalchemy import and_
                query = query.where(and_(*filters))
                
            # Execute query - don't await the execution result
            result = self.session.execute(query)
            
            # Process results into dictionary format
            user_data = []
            for row in result.all():
                user = row[0]
                
                user_dict = {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name
                }
                user_data.append(user_dict)
                
            return user_data
        except Exception as e:
            logging.error(f"Error in get_user_details: {str(e)}")
            raise

    async def get_subscriber_details(self) -> List[Dict[str, Any]]:
        """Get detailed subscriber information for reporting"""
        # Import needed models
        from app.resources.models import Subscriber
        from sqlalchemy import select
        
        try:
            # Query to get all subscribers
            query = select(Subscriber)
            result = self.session.execute(query)
            
            # Process results into dictionary format
            subscriber_data = []
            for row in result.all():
                subscriber = row[0]
                
                subscriber_dict = {
                    "id": subscriber.id,
                    "email": subscriber.email,
                    "name": subscriber.name,
                    "subscription_date": subscriber.subscription_date.isoformat() if subscriber.subscription_date else None,
                    "subscription_tier": subscriber.subscription_tier,
                    "is_active": subscriber.is_active
                }
                subscriber_data.append(subscriber_dict)
                
            return subscriber_data
        except Exception as e:
            logging.error(f"Error in get_subscriber_details: {str(e)}")
            raise

    async def get_log_details(self) -> List[Dict[str, Any]]:
        """Get detailed log information for reporting"""
        # Import needed models
        from app.logging.models import Log
        from sqlalchemy import select, desc
        
        try:
            # Query to get all logs, ordered by most recent first
            query = select(Log).order_by(desc(Log.timestamp))
            result = self.session.execute(query)
            
            # Process results into dictionary format
            log_data = []
            for row in result.all():
                log = row[0]
                
                log_dict = {
                    "id": log.id,
                    "level": log.level,
                    "message": log.message,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    "user_id": log.user_id,
                    "username": log.username,
                    "source": log.source,
                    "request_id": log.request_id,
                    "method": log.method,
                    "path": log.path,
                    "status_code": log.status_code,
                    "host": log.host,
                    "app_id": log.app_id
                }
                log_data.append(log_dict)
                
            return log_data
        except Exception as e:
            logging.error(f"Error in get_log_details: {str(e)}")
            raise

    # New methods for task queue integration

    async def create_scheduled_report(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new scheduled report
        
        Args:
            report_data: Dictionary containing the scheduled report details
            
        Returns:
            The created scheduled report
        """
        try:
            # Convert parameters to JSON string if needed
            if isinstance(report_data.get("parameters"), dict):
                parameters = json.dumps(report_data["parameters"])
            else:
                parameters = report_data.get("parameters", "{}")
            
            # Create the SQL query
            query = text("""
                INSERT INTO scheduled_reports 
                (report_id, user_id, name, description, parameters, frequency, 
                day_of_week, day_of_month, time_of_day, is_active)
                VALUES (:report_id, :user_id, :name, :description, :parameters, :frequency,
                :day_of_week, :day_of_month, :time_of_day, :is_active)
                RETURNING id, created_at, updated_at
            """)
            
            # Execute the query with parameters
            result = self.session.execute(query, {
                "report_id": report_data.get("report_id"),
                "user_id": report_data.get("user_id"),
                "name": report_data.get("name"),
                "description": report_data.get("description"),
                "parameters": parameters,
                "frequency": report_data.get("frequency"),
                "day_of_week": report_data.get("day_of_week"),
                "day_of_month": report_data.get("day_of_month"),
                "time_of_day": report_data.get("time_of_day"),
                "is_active": report_data.get("is_active", True)
            })
            
            self.session.commit()
            
            row = result.fetchone()
            if row:
                # Return the created report with all fields
                report_data["id"] = row[0]
                report_data["created_at"] = row[1]
                report_data["updated_at"] = row[2]
                return report_data
            return None
        except Exception as e:
            self.session.rollback()
            logging.error(f"Error in create_scheduled_report: {str(e)}")
            raise

    async def get_scheduled_reports(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all scheduled reports, optionally filtered by user_id
        
        Args:
            user_id: Optional user ID to filter reports by
            
        Returns:
            List of scheduled reports
        """
        try:
            query_text = """
                SELECT sr.*, r.name as report_name 
                FROM scheduled_reports sr
                JOIN reports r ON sr.report_id = r.id
            """
            
            params = {}
            if user_id is not None:
                query_text += " WHERE sr.user_id = :user_id"
                params["user_id"] = user_id
                
            query_text += " ORDER BY sr.updated_at DESC"
            
            query = text(query_text)
            result = self.session.execute(query, params)
            
            scheduled_reports = []
            for row in result:
                # Convert row to a dictionary
                report = {
                    "id": row.id,
                    "report_id": row.report_id,
                    "report_name": row.report_name,
                    "user_id": row.user_id,
                    "name": row.name,
                    "description": row.description,
                    "parameters": json.loads(row.parameters) if row.parameters else {},
                    "frequency": row.frequency,
                    "day_of_week": row.day_of_week,
                    "day_of_month": row.day_of_month,
                    "time_of_day": str(row.time_of_day) if row.time_of_day else None,
                    "is_active": row.is_active,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None
                }
                scheduled_reports.append(report)
                
            return scheduled_reports
        except Exception as e:
            logging.error(f"Error in get_scheduled_reports: {str(e)}")
            raise

    async def update_scheduled_report(self, report_id: int, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a scheduled report
        
        Args:
            report_id: ID of the report to update
            report_data: Dictionary containing the updated report details
            
        Returns:
            The updated report
        """
        try:
            # Convert parameters to JSON string if needed
            if isinstance(report_data.get("parameters"), dict):
                parameters = json.dumps(report_data["parameters"])
            else:
                parameters = report_data.get("parameters")
            
            # Build update parts and parameters
            update_parts = []
            params = {"id": report_id}
            
            fields = [
                "report_id", "user_id", "name", "description", "parameters",
                "frequency", "day_of_week", "day_of_month", "time_of_day", "is_active"
            ]
            
            for field in fields:
                if field in report_data:
                    update_parts.append(f"{field} = :{field}")
                    params[field] = report_data[field] if field != "parameters" else parameters
            
            # Add updated_at
            update_parts.append("updated_at = :updated_at")
            params["updated_at"] = datetime.datetime.utcnow()
            
            # Create the SQL query
            query = text(f"""
                UPDATE scheduled_reports 
                SET {", ".join(update_parts)}
                WHERE id = :id
                RETURNING id, report_id, user_id, name, description, parameters,
                          frequency, day_of_week, day_of_month, time_of_day, 
                          is_active, created_at, updated_at
            """)
            
            # Execute the query with parameters
            result = self.session.execute(query, params)
            self.session.commit()
            
            row = result.fetchone()
            if row:
                # Convert row to a dictionary
                updated_report = {
                    "id": row.id,
                    "report_id": row.report_id,
                    "user_id": row.user_id,
                    "name": row.name,
                    "description": row.description,
                    "parameters": json.loads(row.parameters) if row.parameters else {},
                    "frequency": row.frequency,
                    "day_of_week": row.day_of_week,
                    "day_of_month": row.day_of_month,
                    "time_of_day": str(row.time_of_day) if row.time_of_day else None,
                    "is_active": row.is_active,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None
                }
                return updated_report
            return None
        except Exception as e:
            self.session.rollback()
            logging.error(f"Error in update_scheduled_report: {str(e)}")
            raise

    async def delete_scheduled_report(self, report_id: int) -> bool:
        """
        Delete a scheduled report
        
        Args:
            report_id: ID of the report to delete
            
        Returns:
            True if the report was deleted, False otherwise
        """
        try:
            query = text("DELETE FROM scheduled_reports WHERE id = :id")
            result = self.session.execute(query, {"id": report_id})
            self.session.commit()
            return result.rowcount > 0
        except Exception as e:
            self.session.rollback()
            logging.error(f"Error in delete_scheduled_report: {str(e)}")
            raise

    async def get_report_executions(
        self, 
        user_id: Optional[int] = None,
        report_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get report execution history with optional filters
        
        Args:
            user_id: Optional user ID to filter executions by
            report_id: Optional report ID to filter executions by
            status: Optional status to filter executions by
            limit: Maximum number of executions to return
            
        Returns:
            List of report executions
        """
        try:
            query_text = """
                SELECT re.*, r.name as report_name
                FROM report_executions re
                JOIN reports r ON re.report_id = r.id
                WHERE 1=1
            """
            
            params = {}
            
            if user_id is not None:
                query_text += " AND re.user_id = :user_id"
                params["user_id"] = user_id
                
            if report_id is not None:
                query_text += " AND re.report_id = :report_id"
                params["report_id"] = report_id
                
            if status is not None:
                query_text += " AND re.status = :status"
                params["status"] = status
                
            query_text += " ORDER BY re.started_at DESC LIMIT :limit"
            params["limit"] = limit
            
            query = text(query_text)
            result = self.session.execute(query, params)
            
            executions = []
            for row in result:
                # Convert row to a dictionary
                execution = {
                    "id": row.id,
                    "report_id": row.report_id,
                    "report_name": row.report_name,
                    "scheduled_report_id": row.scheduled_report_id,
                    "task_id": row.task_id,
                    "user_id": row.user_id,
                    "status": row.status,
                    "parameters": json.loads(row.parameters) if row.parameters else {},
                    "started_at": row.started_at.isoformat() if row.started_at else None,
                    "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                    "result_path": row.result_path,
                    "error": row.error
                }
                executions.append(execution)
                
            return executions
        except Exception as e:
            logging.error(f"Error in get_report_executions: {str(e)}")
            raise

    async def create_report_execution(self, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new report execution record
        
        Args:
            execution_data: Dictionary containing the execution details
            
        Returns:
            The created execution record
        """
        try:
            # Convert parameters to JSON string if needed
            if isinstance(execution_data.get("parameters"), dict):
                parameters = json.dumps(execution_data["parameters"])
            else:
                parameters = execution_data.get("parameters", "{}")
            
            # Create the SQL query
            query = text("""
                INSERT INTO report_executions 
                (report_id, scheduled_report_id, task_id, user_id, status, parameters, started_at)
                VALUES (:report_id, :scheduled_report_id, :task_id, :user_id, :status, :parameters, :started_at)
                RETURNING id
            """)
            
            # Default started_at to current time if not provided
            if "started_at" not in execution_data:
                execution_data["started_at"] = datetime.datetime.utcnow()
            
            # Execute the query with parameters
            result = self.session.execute(query, {
                "report_id": execution_data.get("report_id"),
                "scheduled_report_id": execution_data.get("scheduled_report_id"),
                "task_id": execution_data.get("task_id"),
                "user_id": execution_data.get("user_id"),
                "status": execution_data.get("status", "QUEUED"),
                "parameters": parameters,
                "started_at": execution_data.get("started_at")
            })
            
            self.session.commit()
            
            row = result.fetchone()
            if row:
                # Return the created execution with the ID
                execution_data["id"] = row[0]
                return execution_data
            return None
        except Exception as e:
            self.session.rollback()
            logging.error(f"Error in create_report_execution: {str(e)}")
            raise

    async def update_report_execution_status(
        self, 
        execution_id: Optional[int] = None,
        task_id: Optional[str] = None,
        status: str = "COMPLETED",
        result_path: Optional[str] = None,
        error: Optional[str] = None
    ) -> bool:
        """
        Update a report execution status
        
        Args:
            execution_id: ID of the execution to update (either this or task_id must be provided)
            task_id: Task ID of the execution to update (either this or execution_id must be provided)
            status: New status (default: COMPLETED)
            result_path: Path to the report result file (optional)
            error: Error message if the execution failed (optional)
            
        Returns:
            True if the execution was updated, False otherwise
        """
        try:
            if execution_id is None and task_id is None:
                raise ValueError("Either execution_id or task_id must be provided")
                
            params = {
                "status": status,
                "completed_at": datetime.datetime.utcnow()
            }
            
            if result_path is not None:
                params["result_path"] = result_path
                
            if error is not None:
                params["error"] = error
                
            # Build the query
            query_text = """
                UPDATE report_executions
                SET status = :status, completed_at = :completed_at
            """
            
            if result_path is not None:
                query_text += ", result_path = :result_path"
                
            if error is not None:
                query_text += ", error = :error"
                
            if execution_id is not None:
                query_text += " WHERE id = :id"
                params["id"] = execution_id
            else:
                query_text += " WHERE task_id = :task_id"
                params["task_id"] = task_id
                
            query = text(query_text)
            result = self.session.execute(query, params)
            self.session.commit()
            
            return result.rowcount > 0
        except Exception as e:
            self.session.rollback()
            logging.error(f"Error in update_report_execution_status: {str(e)}")
            raise
