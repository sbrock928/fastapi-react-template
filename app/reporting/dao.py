from sqlalchemy.orm import Session
from sqlalchemy import select, func, text
from typing import List, Dict, Any, Optional, Tuple
from app.resources.models import User, Employee, Subscriber
from app.logging.models import Log
from datetime import datetime, timedelta


class ReportingDAO:
    def __init__(self, session: Session):
        self.session = session

    async def get_user_count(self) -> int:
        """Get the total number of users"""
        result = self.session.execute(select(func.count(User.id)))
        return int(result.scalar_one() or 0)

    async def get_employee_count(self) -> int:
        """Get the total number of employees"""
        result = self.session.execute(select(func.count(Employee.id)))
        return int(result.scalar_one() or 0)

    async def get_subscriber_count(self) -> int:
        """Get the total number of subscribers"""
        result = self.session.execute(select(func.count(Subscriber.id)))
        return int(result.scalar_one() or 0)

    async def get_log_count(self) -> int:
        """Get the total number of logs"""
        result = self.session.execute(select(func.count(Log.id)))
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
        except Exception:
            # If the table doesn't exist yet or there's another error
            return []

    async def get_employees_by_department(self) -> List[Tuple[str, int]]:
        """Get employee counts grouped by department"""
        query = (
            select(Employee.department, func.count(Employee.id).label("count"))
            .group_by(Employee.department)
            .order_by(Employee.department)
        )

        result = self.session.execute(query)
        return [(row.department, row.count) for row in result]

    async def get_resource_counts(self, cycle_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get counts of different resource types, optionally filtered by cycle code"""
        # This is a simplified query since we're not actually filtering by cycle_code
        # In a real implementation, you would join with a cycles table

        user_count = await self.get_user_count()
        employee_count = await self.get_employee_count()
        subscriber_count = await self.get_subscriber_count()

        return [
            {"resource_type": "Users", "count": user_count},
            {"resource_type": "Employees", "count": employee_count},
            {"resource_type": "Subscribers", "count": subscriber_count},
        ]
