"""Service layer for the reporting module handling business logic for reports."""

import json
import requests
import os
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from app.reporting.dao import ReportingDAO
from datetime import datetime
import pandas as pd
from io import BytesIO


class ReportingService:
    """Service for generating and managing reports and statistics."""

    def __init__(self, dao: ReportingDAO):
        self.report_dao = dao

    async def get_summary_statistics(self) -> Dict[str, Any]:
        """Get summary statistics for the dashboard"""
        try:
            # Get raw counts from DAO
            user_count = await self.report_dao.get_user_count()
            employee_count = await self.report_dao.get_employee_count()
            subscriber_count = await self.report_dao.get_subscriber_count()
            log_count = await self.report_dao.get_log_count()

            # Format for API response
            return {
                "user_count": user_count,
                "employee_count": employee_count,
                "subscriber_count": subscriber_count,
                "log_count": log_count,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error generating summary statistics: {str(e)}"
            ) from e

    async def get_employees_by_department(self) -> List[Dict[str, Any]]:
        """Report showing employee count by department"""
        try:
            # Get raw data from DAO
            data = await self.report_dao.get_employees_by_department()
            return data
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating employees by department report: {str(e)}",
            ) from e

    async def get_resource_counts(self, cycle_code: Optional[str] = None) -> List[Dict[str, Any]]: 
        """Report showing count of different resource types, optionally filtered by cycle code"""
        try:
            # Get data from DAO, potentially filtered by cycle_code
            return await self.report_dao.get_resource_counts(cycle_code)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating resource counts report: {str(e)}",
            ) from e

    async def export_to_xlsx(self, export_data: Dict[str, Any]) -> BytesIO:
        """Export report data to Excel format"""
        try:
            # Create a Pandas Excel writer using BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                # For each sheet in the export data
                for sheet_name, data in export_data.items():
                    # Convert data to DataFrame and write to Excel
                    df = pd.DataFrame(data)
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

                    # Adjust column widths
                    worksheet = writer.sheets[sheet_name]
                    for i, col in enumerate(df.columns):
                        max_width = max(df[col].astype(str).map(len).max(), len(col)) + 2
                        worksheet.set_column(i, i, max_width)

            # Important: seek to start of file for proper reading
            output.seek(0)
            return output
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error exporting to Excel: {str(e)}"
            ) from e

    async def get_distinct_cycle_codes(self) -> List[Dict[str, str]]:
        """Get list of distinct cycle codes for report filters"""
        try:
            return await self.report_dao.get_distinct_cycle_codes()
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error fetching cycle codes: {str(e)}"
            ) from e

    async def get_report_configurations(self) -> Dict[str, Dict[str, Any]]:
        """Get all report configurations with their schemas for dynamic reporting"""
        try:
            # Import schemas needed for building dynamic configurations
            from app.resources.schemas import EmployeeRead, UserRead, SubscriberRead
            from app.logging.schemas import LogRead
            
            # Define report configurations with their schemas based on database models
            configurations = {}
            
            # Helper method to generate columns from schema properties
            def generate_columns_from_schema(schema_properties: Dict[str, Any]) -> List[Dict[str, str]]:
                return [
                    {"field": field, "header": field.replace('_', ' ').title(), 
                     "type": "text" if prop.get('type') == 'string' else 
                            "number" if prop.get('type') in ['integer', 'number'] else
                            "date" if field.endswith('_date') or field == 'timestamp' else
                            "boolean" if prop.get('type') == 'boolean' else "text"}
                    for field, prop in schema_properties.items()
                ]
            
            # Employees by Department report
            # For aggregate data reports, we'll define the schema structure programmatically
            department_report_schema = {
                "department": {"type": "string"},
                "count": {"type": "integer"},
                "percentage": {"type": "number"}
            }
            configurations["employees_by_department"] = {
                "apiEndpoint": "/reports/employees-by-department",
                "title": "Employees by Department",
                "columns": generate_columns_from_schema(department_report_schema)
            }
            
            # Resource Counts report
            resource_counts_schema = {
                "resource_type": {"type": "string"},
                "count": {"type": "integer"}
            }
            configurations["resource_counts"] = {
                "apiEndpoint": "/reports/resource-counts",
                "title": "Resource Counts Summary",
                "columns": generate_columns_from_schema(resource_counts_schema)
            }
            
            # Employee Details report using full schema
            employee_schema = EmployeeRead.model_json_schema()
            configurations["employee_details"] = {
                "apiEndpoint": "/reports/employee-details",
                "title": "Employee Details",
                "columns": generate_columns_from_schema(employee_schema.get('properties', {}))
            }
            
            # Add more reports dynamically using schemas
            # User details report
            user_schema = UserRead.model_json_schema()
            configurations["user_details"] = {
                "apiEndpoint": "/reports/user-details",
                "title": "User Details",
                "columns": generate_columns_from_schema(user_schema.get('properties', {}))
            }
            
            # Subscriber details report
            subscriber_schema = SubscriberRead.model_json_schema()
            configurations["subscriber_details"] = {
                "apiEndpoint": "/reports/subscriber-details",
                "title": "Subscriber Details",
                "columns": generate_columns_from_schema(subscriber_schema.get('properties', {}))
            }
            
            # Log details report
            log_schema = LogRead.model_json_schema()
            configurations["log_details"] = {
                "apiEndpoint": "/reports/log-details",
                "title": "Log Details",
                "columns": generate_columns_from_schema(log_schema.get('properties', {}))
            }
            
            return configurations
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching report configurations: {str(e)}"
            ) from e

    async def get_employee_details(self) -> List[Dict[str, Any]]:
        """Get detailed employee information for reports"""
        try:
            return await self.report_dao.get_employee_details()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating employee details report: {str(e)}",
            ) from e

    async def get_user_details(
        self, 
        username: Optional[str] = None, 
        email: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_superuser: Optional[bool] = None,
        date_range: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get detailed user information for reports with filtering options
        
        Args:
            username: Optional filter by username (partial match)
            email: Optional filter by email (partial match)
            is_active: Optional filter by active status (ignored - not in model)
            is_superuser: Optional filter by superuser status (ignored - not in model)
            date_range: Optional filter for date range (ignored - no date field in User model)
        """
        try:
            # The User model doesn't have created_at, is_active, or is_superuser fields
            # So we'll just pass the filters that are applicable
            return await self.report_dao.get_user_details(
                username=username,
                email=email,
                # Ignoring filters for fields that don't exist
                is_active=None,
                is_superuser=None,
                days=None
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating user details report: {str(e)}",
            ) from e

    async def get_subscriber_details(self) -> List[Dict[str, Any]]:
        """Get detailed subscriber information for reports"""
        try:
            return await self.report_dao.get_subscriber_details()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating subscriber details report: {str(e)}",
            ) from e

    async def get_log_details(self) -> List[Dict[str, Any]]:
        """Get detailed log information for reports"""
        try:
            return await self.report_dao.get_log_details()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error generating log details report: {str(e)}",
            ) from e

    def _parse_date_range(self, date_range: str) -> int:
        """Helper to parse a date range string into number of days"""
        if date_range == "7days":
            return 7
        elif date_range == "30days":
            return 30
        elif date_range == "90days":
            return 90
        elif date_range == "1year":
            return 365
        else:
            # Default to 30 days
            return 30
            
    # New methods for task queue integration
    
    async def execute_report_async(
        self, 
        report_id: int, 
        parameters: Dict[str, Any],
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a report asynchronously by submitting a task to the Celery queue
        
        Args:
            report_id: ID of the report to execute
            parameters: Report parameters
            user_id: ID of the user requesting the report
            
        Returns:
            Dict with task information
        """
        try:
            # Create an execution record in the database with QUEUED status
            execution_data = {
                "report_id": report_id,
                "user_id": user_id,
                "parameters": parameters,
                "status": "QUEUED",
                "started_at": datetime.utcnow()
            }
            
            execution = await self.report_dao.create_report_execution(execution_data)
            
            # Submit task to Celery
            task_response = self._submit_task_to_celery(
                "task_queue.tasks.reports.execute_report",
                [report_id, parameters, user_id]
            )
            
            if "task_id" in task_response:
                # Update the execution record with the task ID
                await self.report_dao.update_report_execution_status(
                    execution_id=execution["id"],
                    task_id=task_response["task_id"],
                    status="RUNNING"
                )
                
                return {
                    "execution_id": execution["id"],
                    "task_id": task_response["task_id"],
                    "status": "RUNNING",
                    "message": "Report execution submitted successfully"
                }
            else:
                # Something went wrong with task submission
                await self.report_dao.update_report_execution_status(
                    execution_id=execution["id"],
                    status="FAILED",
                    error="Failed to submit task to Celery"
                )
                
                raise HTTPException(
                    status_code=500,
                    detail="Failed to submit report execution task"
                )
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error executing report asynchronously: {str(e)}"
            ) from e
    
    async def create_scheduled_report(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new scheduled report
        
        Args:
            report_data: Report scheduling data
            
        Returns:
            The created scheduled report
        """
        try:
            # Validate the report data before creating
            self._validate_scheduled_report_data(report_data)
            
            # Create the scheduled report
            return await self.report_dao.create_scheduled_report(report_data)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error creating scheduled report: {str(e)}"
            ) from e
    
    async def get_scheduled_reports(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all scheduled reports for a user
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            List of scheduled reports
        """
        try:
            return await self.report_dao.get_scheduled_reports(user_id)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching scheduled reports: {str(e)}"
            ) from e
    
    async def update_scheduled_report(self, report_id: int, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a scheduled report
        
        Args:
            report_id: ID of the report to update
            report_data: Updated report data
            
        Returns:
            The updated report
        """
        try:
            # Validate the report data before updating
            self._validate_scheduled_report_data(report_data)
            
            # Update the scheduled report
            updated_report = await self.report_dao.update_scheduled_report(report_id, report_data)
            
            if not updated_report:
                raise HTTPException(
                    status_code=404,
                    detail=f"Scheduled report with ID {report_id} not found"
                )
                
            return updated_report
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error updating scheduled report: {str(e)}"
            ) from e
    
    async def delete_scheduled_report(self, report_id: int) -> Dict[str, Any]:
        """
        Delete a scheduled report
        
        Args:
            report_id: ID of the report to delete
            
        Returns:
            Success message
        """
        try:
            deleted = await self.report_dao.delete_scheduled_report(report_id)
            
            if not deleted:
                raise HTTPException(
                    status_code=404,
                    detail=f"Scheduled report with ID {report_id} not found"
                )
                
            return {"message": f"Scheduled report {report_id} deleted successfully"}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error deleting scheduled report: {str(e)}"
            ) from e
    
    async def get_report_executions(
        self, 
        user_id: Optional[int] = None,
        report_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get report execution history
        
        Args:
            user_id: Optional user ID to filter by
            report_id: Optional report ID to filter by
            status: Optional status to filter by
            limit: Maximum number of executions to return
            
        Returns:
            List of report executions
        """
        try:
            return await self.report_dao.get_report_executions(
                user_id=user_id,
                report_id=report_id,
                status=status,
                limit=limit
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching report executions: {str(e)}"
            ) from e
    
    def _validate_scheduled_report_data(self, report_data: Dict[str, Any]) -> None:
        """
        Validate scheduled report data
        
        Args:
            report_data: Report data to validate
            
        Raises:
            ValueError: If the report data is invalid
        """
        # Check required fields
        required_fields = ["report_id", "user_id", "name", "frequency", "time_of_day"]
        for field in required_fields:
            if field not in report_data or not report_data[field]:
                raise ValueError(f"Missing required field: {field}")
        
        # Check that frequency is valid
        valid_frequencies = ["DAILY", "WEEKLY", "MONTHLY"]
        if report_data.get("frequency") not in valid_frequencies:
            raise ValueError(f"Invalid frequency. Must be one of: {', '.join(valid_frequencies)}")
        
        # Check that day_of_week is provided for weekly reports
        if report_data.get("frequency") == "WEEKLY" and not report_data.get("day_of_week"):
            raise ValueError("day_of_week is required for weekly reports")
        
        # Check that day_of_month is provided for monthly reports
        if report_data.get("frequency") == "MONTHLY" and not report_data.get("day_of_month"):
            raise ValueError("day_of_month is required for monthly reports")
        
        # Validate day_of_week for weekly reports
        if report_data.get("day_of_week"):
            valid_days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
            if report_data.get("day_of_week") not in valid_days:
                raise ValueError(f"Invalid day_of_week. Must be one of: {', '.join(valid_days)}")
        
        # Validate day_of_month for monthly reports
        if report_data.get("day_of_month"):
            day = report_data.get("day_of_month")
            if not isinstance(day, int) or day < 1 or day > 31:
                raise ValueError("day_of_month must be between 1 and 31")
        
    def _submit_task_to_celery(self, task_name: str, args=None, kwargs=None) -> Dict[str, Any]:
        """
        Submit a task to Celery
        
        Args:
            task_name: Name of the task to execute
            args: Positional arguments for the task
            kwargs: Keyword arguments for the task
            
        Returns:
            Response from Celery with task ID
        """
        # In a real implementation, you would use the Celery API directly
        # For now, we'll simulate the Celery response
        
        try:
            # Get Celery API URL from environment or use default
            celery_api_url = os.environ.get("CELERY_API_URL", "http://localhost:5555/api")
            
            # Prepare request payload
            payload = {
                "task": task_name,
                "args": args or [],
                "kwargs": kwargs or {}
            }
            
            # Make API request to Celery (simulated for now)
            # In a real implementation, you'd make an HTTP request to the Celery API
            # response = requests.post(f"{celery_api_url}/task/async-apply/", json=payload)
            # response.raise_for_status()
            # return response.json()
            
            # For now, return a simulated response
            import uuid
            return {
                "task_id": str(uuid.uuid4()),
                "state": "PENDING"
            }
            
        except Exception as e:
            # Log the error but don't expose it directly
            import logging
            logging.error(f"Error submitting task to Celery: {str(e)}")
            return {
                "error": "Failed to submit task to Celery",
                "details": str(e)
            }
