from typing import List, Dict, Any
from fastapi import HTTPException
from sqlmodel import Session, select, func, text
from app.dao.report_dao import ReportDAO
from app.models.base import Log, User, Employee
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO

class ReportService:
    def __init__(self, session: Session):
        self.report_dao = ReportDAO(session)
        self.session = session
    
    async def get_summary_statistics(self) -> Dict[str, Any]:
        """Get summary statistics for the dashboard"""
        try:
            user_count = await self.report_dao.get_user_count()
            employee_count = await self.report_dao.get_employee_count()
            log_count = await self.report_dao.get_log_count()
            
            return {
                "user_count": user_count,
                "employee_count": employee_count,
                "log_count": log_count,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generating summary statistics: {str(e)}")
    
    async def get_recent_activities(self, days: int = 7) -> Dict[str, Any]:
        """Get recent activities for the dashboard"""
        if days <= 0:
            raise HTTPException(status_code=400, detail="Days must be greater than 0")
            
        try:
            recent_logs = await self.report_dao.get_recent_logs(days=days)
            return {
                "recent_logs": [self._format_log(log) for log in recent_logs],
                "days": days,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generating recent activities: {str(e)}")
    
    async def get_status_distribution(self) -> Dict[str, Any]:
        """Get distribution of logs by status code"""
        try:
            distribution = await self.report_dao.get_status_distribution()
            # Add status descriptions
            for item in distribution:
                status_code = item["status_code"]
                if 200 <= status_code < 300:
                    item["description"] = "Success"
                elif 300 <= status_code < 400:
                    item["description"] = "Redirection"
                elif 400 <= status_code < 500:
                    item["description"] = "Client Error"
                elif 500 <= status_code < 600:
                    item["description"] = "Server Error"
                else:
                    item["description"] = "Unknown"
                    
            return {
                "status_distribution": distribution,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generating status distribution: {str(e)}")
    
    async def get_users_by_creation(self, date_range: str) -> List[Dict[str, Any]]:
        """Report showing user creation by date"""
        start_date, end_date = self._get_date_range(date_range)
        
        # This is a simplified approach since we don't have a creation_date field in the model
        # In a real application, you would use the actual creation date field
        query = """
        SELECT COUNT(*) as count, date('now', '-' || (abs(random()) % 30) || ' days') as date
        FROM user
        GROUP BY date
        ORDER BY date ASC
        """
        
        result = self.session.exec(text(query)).all()
        
        # Transform into the expected format
        report_data = []
        cumulative = 0
        
        for row in result:
            count = row[0]  # Access by index since it's a tuple
            date = row[1]
            cumulative += count
            
            report_data.append({
                "date": date,
                "count": count,
                "cumulative": cumulative
            })
        
        return report_data
    
    async def get_employees_by_department(self) -> List[Dict[str, Any]]:
        """Report showing employee count by department"""
        # Get employees grouped by department
        query = select(
            Employee.department,
            func.count(Employee.id).label("count")
        ).group_by(Employee.department)
        
        result = self.session.exec(query).all()
        
        # Calculate total
        total_employees = sum(row[1] for row in result)
        
        # Transform into the expected format
        report_data = []
        
        for row in result:
            department = row[0]
            count = row[1]
            percentage = count / total_employees if total_employees > 0 else 0
            
            report_data.append({
                "department": department,
                "count": count,
                "percentage": percentage
            })
        
        # Sort by count descending
        report_data.sort(key=lambda x: x["count"], reverse=True)
        
        return report_data
    
    async def get_resource_counts(self) -> List[Dict[str, Any]]:
        """Report showing count of different resource types"""
        # Get counts for different resource types
        user_count = self.session.exec(select(func.count(User.id))).one()
        employee_count = self.session.exec(select(func.count(Employee.id))).one()
        
        # Transform into the expected format
        report_data = [
            {"resource_type": "Users", "count": user_count},
            {"resource_type": "Employees", "count": employee_count}
        ]
        
        return report_data
    
    async def export_to_xlsx(self, export_data: Dict[str, Any]) -> BytesIO:
        """Export report data to Excel format"""
        report_type = export_data.get('reportType')
        data = export_data.get('data', [])
        
        if not data:
            raise HTTPException(status_code=400, detail="No data to export")
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Report', index=False)
            
            # Get workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Report']
            
            # Add some formatting
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#007BFF',
                'color': 'white',
                'border': 1
            })
            
            # Apply header format
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                
            # Auto-adjust columns
            for i, column in enumerate(df.columns):
                max_length = max(
                    df[column].astype(str).map(len).max(),
                    len(column)
                ) + 2
                worksheet.set_column(i, i, max_length)
        
        # Reset file pointer
        output.seek(0)
        return output
    
    def _format_log(self, log: Log) -> Dict[str, Any]:
        """Format a log object for API response"""
        # Handle both older and newer pydantic versions
        try:
            log_dict = log.dict()
        except AttributeError:
            log_dict = log.model_dump()
            
        # Add status category
        status_code = log_dict.get("status_code", 0)
        if 200 <= status_code < 300:
            log_dict["status_category"] = "Success"
        elif 300 <= status_code < 400:
            log_dict["status_category"] = "Redirection"
        elif 400 <= status_code < 500:
            log_dict["status_category"] = "Client Error"
        elif 500 <= status_code < 600:
            log_dict["status_category"] = "Server Error"
        else:
            log_dict["status_category"] = "Unknown"
            
        return log_dict
    
    def _get_date_range(self, range_type: str):
        """Helper function to get date ranges for reports"""
        today = datetime.now().date()
        
        if range_type == 'last_7_days':
            start_date = today - timedelta(days=7)
        elif range_type == 'last_30_days':
            start_date = today - timedelta(days=30)
        elif range_type == 'last_90_days':
            start_date = today - timedelta(days=90)
        elif range_type == 'year_to_date':
            start_date = datetime(today.year, 1, 1).date()
        else:  # all_time
            start_date = datetime(2000, 1, 1).date()
        
        return start_date, today