"""Service layer for the reporting module handling business logic for reports."""

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
