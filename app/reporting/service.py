from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func, text
from app.reporting.dao import ReportingDAO
from app.resources.models import User, Employee, Subscriber
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO


class ReportingService:
    def __init__(self, session: Session):
        self.report_dao = ReportingDAO(session)
        self.session = session

    async def get_summary_statistics(self) -> Dict[str, Any]:
        """Get summary statistics for the dashboard"""
        try:
            user_count = await self.report_dao.get_user_count()
            employee_count = await self.report_dao.get_employee_count()
            subscriber_count = await self.report_dao.get_subscriber_count()
            log_count = await self.report_dao.get_log_count()

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
            )

    async def get_status_distribution(self, hours: int = 24) -> Dict[str, Any]:
        """Get distribution of logs by status code - delegates to LogService"""
        # This method now redirects to the LogService method
        from app.logging.service import LogService

        log_service = LogService(self.session)
        return await log_service.get_status_distribution(hours=hours)

    async def get_users_by_creation(self, date_range: str) -> List[Dict[str, Any]]:
        """Report showing user creation by date"""
        start_date, end_date = self._get_date_range(date_range)

        # This is a simplified approach since we don't have a creation_date field in the model
        # In a real application, you would use the actual creation date field
        query = text(
            """
        SELECT COUNT(*) as count, date('now', '-' || (abs(random()) % 30) || ' days') as date
        FROM user
        GROUP BY date
        ORDER BY date ASC
        """
        )

        result = self.session.execute(query).all()

        # Transform into the expected format
        report_data = []
        cumulative = 0

        for row in result:
            count = row[0]  # Access by index since it's a tuple
            date = row[1]
            cumulative += count

            report_data.append({"date": date, "count": count, "cumulative": cumulative})

        return report_data

    async def get_employees_by_department(self) -> List[Dict[str, Any]]:
        """Report showing employee count by department"""
        # Get employees grouped by department
        query = select(
            Employee.department, func.count(Employee.id).label("count")
        ).group_by(Employee.department)

        result = self.session.execute(query).all()

        # Calculate total
        total_employees = sum(row[1] for row in result)

        # Transform into the expected format
        report_data = []

        for row in result:
            department = row[0]
            count = row[1]
            percentage = count / total_employees if total_employees > 0 else 0

            report_data.append(
                {"department": department, "count": count, "percentage": percentage}
            )

        # Sort by count descending
        report_data.sort(key=lambda x: x["count"], reverse=True)

        return report_data

    async def get_resource_counts(
        self, cycle_code: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Report showing count of different resource types, optionally filtered by cycle code"""
        # Get counts for different resource types
        user_result = self.session.execute(select(func.count(User.id)))
        user_count = user_result.scalar_one()

        employee_result = self.session.execute(select(func.count(Employee.id)))
        employee_count = employee_result.scalar_one()

        subscriber_result = self.session.execute(select(func.count(Subscriber.id)))
        subscriber_count = subscriber_result.scalar_one()

        # Apply cycle code filter if provided
        if cycle_code:
            # Use raw SQL to filter by cycle code
            # You would typically join with the Cycles table in a real implementation
            cycle_query = text(
                """
                SELECT 
                    (SELECT COUNT(*) FROM user WHERE cycle_code = :cycle_code) as user_count,
                    (SELECT COUNT(*) FROM employee WHERE cycle_code = :cycle_code) as employee_count,
                    (SELECT COUNT(*) FROM subscriber WHERE cycle_code = :cycle_code) as subscriber_count
            """
            )
            cycle_result = self.session.execute(
                cycle_query, {"cycle_code": cycle_code}
            ).first()

            # Check if result exists before accessing indices
            if cycle_result:
                user_count = cycle_result[0] if cycle_result[0] is not None else 0
                employee_count = cycle_result[1] if cycle_result[1] is not None else 0
                subscriber_count = cycle_result[2] if cycle_result[2] is not None else 0

        # Transform into the expected format
        report_data = [
            {"resource_type": "Users", "count": user_count},
            {"resource_type": "Employees", "count": employee_count},
            {"resource_type": "Subscribers", "count": subscriber_count},
        ]

        return report_data

    async def export_to_xlsx(self, export_data: Dict[str, Any]) -> BytesIO:
        """Export report data to Excel format"""
        report_type = export_data.get("reportType")
        data = export_data.get("data", [])

        if not data:
            raise HTTPException(status_code=400, detail="No data to export")

        # Convert to DataFrame
        df = pd.DataFrame(data)

        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Report", index=False)

            # Get workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets["Report"]

            # Add some formatting
            header_format = workbook.add_format(
                {"bold": True, "bg_color": "#93186C", "color": "white", "border": 1}
            )

            # Apply header format
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)

            # Auto-adjust columns
            for i, column in enumerate(df.columns):
                max_length = max(df[column].astype(str).map(len).max(), len(column)) + 2
                worksheet.set_column(i, i, max_length)

        # Reset file pointer
        output.seek(0)
        return output

    async def get_distinct_cycle_codes(self) -> List[Dict[str, str]]:
        """Get list of distinct cycle codes for report filters"""
        try:
            # Explicitly cast the return type to match annotation
            result = await self.report_dao.get_distinct_cycle_codes()
            return [{"code": str(code_dict.get("code", ""))} for code_dict in result]
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error fetching cycle codes: {str(e)}"
            )

    def _get_date_range(self, range_type: str):
        """Helper function to get date ranges for reports"""
        today = datetime.now().date()

        if range_type == "last_7_days":
            start_date = today - timedelta(days=7)
        elif range_type == "last_30_days":
            start_date = today - timedelta(days=30)
        elif range_type == "last_90_days":
            start_date = today - timedelta(days=90)
        elif range_type == "year_to_date":
            start_date = datetime(today.year, 1, 1).date()
        else:  # all_time
            start_date = datetime(2000, 1, 1).date()

        return start_date, today
