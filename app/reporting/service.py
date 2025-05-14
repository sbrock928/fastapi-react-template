from typing import List, Dict, Any, Optional, BinaryIO
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func, text
from app.reporting.dao import ReportingDAO
from app.resources.models import User, Employee, Subscriber
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO


class ReportingService:
    def __init__(self, session: Session, dao: ReportingDAO = None):
        self.session = session
        self.report_dao = dao if dao is not None else ReportingDAO(session)

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
            )

    async def get_status_distribution(self, hours: int = 24) -> Dict[str, Any]:
        """Get distribution of logs by status code - delegates to LogService"""
        # This method redirects to the LogService method
        from app.logging.service import LogService

        try:
            log_service = LogService(self.session)
            return await log_service.get_status_distribution(hours=hours)
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Error getting status distribution: {str(e)}"
            )

    async def get_users_by_creation(self, date_range: str) -> List[Dict[str, Any]]:
        """Report showing user creation by date"""
        try:
            # Parse the date range into number of days
            days = self._parse_date_range(date_range)
            
            # Get raw data from DAO
            data = await self.report_dao.get_users_by_creation_date(days)
            
            # Format for API response
            result = []
            for date_str, count in data:
                result.append({
                    "date": date_str,
                    "count": count
                })
                
            return result
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Error generating users by creation report: {str(e)}"
            )

    async def get_employees_by_department(self) -> List[Dict[str, Any]]:
        """Report showing employee count by department"""
        try:
            # Get raw data from DAO
            data = await self.report_dao.get_employees_by_department()
            
            # Format for API response
            result = []
            for department, count in data:
                result.append({
                    "department": department or "Unassigned",
                    "count": count
                })
                
            return result
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Error generating employees by department report: {str(e)}"
            )

    async def get_resource_counts(
        self, cycle_code: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Report showing count of different resource types, optionally filtered by cycle code"""
        try:
            # Get data from DAO, potentially filtered by cycle_code
            return await self.report_dao.get_resource_counts(cycle_code)
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Error generating resource counts report: {str(e)}"
            )

    async def export_to_xlsx(self, export_data: Dict[str, Any]) -> BytesIO:
        """Export report data to Excel format"""
        try:
            # Create a Pandas Excel writer using BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # For each sheet in the export data
                for sheet_name, data in export_data.items():
                    # Convert data to DataFrame and write to Excel
                    df = pd.DataFrame(data)
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    # Adjust column widths
                    worksheet = writer.sheets[sheet_name]
                    for i, col in enumerate(df.columns):
                        max_width = max(
                            df[col].astype(str).map(len).max(),
                            len(col)
                        ) + 2
                        worksheet.set_column(i, i, max_width)
            
            # Important: seek to start of file for proper reading
            output.seek(0)
            return output
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Error exporting to Excel: {str(e)}"
            )

    async def get_distinct_cycle_codes(self) -> List[Dict[str, str]]:
        """Get list of distinct cycle codes for report filters"""
        try:
            return await self.report_dao.get_distinct_cycle_codes()
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Error fetching cycle codes: {str(e)}"
            )

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
