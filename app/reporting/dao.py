from sqlmodel import Session, select, func, text
from app.resources.models import User, Employee, Subscriber
from app.logging.models import Log


class ReportingDAO:
    def __init__(self, session: Session):
        self.session = session

    async def get_user_count(self) -> int:
        """Get the total number of users"""
        return self.session.exec(select(func.count(User.id))).one()

    async def get_employee_count(self) -> int:
        """Get the total number of employees"""
        return self.session.exec(select(func.count(Employee.id))).one()

    async def get_subscriber_count(self) -> int:
        """Get the total number of subscribers"""
        return self.session.exec(select(func.count(Subscriber.id))).one()

    async def get_log_count(self) -> int:
        """Get the total number of logs"""
        return self.session.exec(select(func.count(Log.id))).one()
        
    async def get_distinct_cycle_codes(self):
        """Get a list of all distinct cycle codes from the Cycles table"""
        # Using raw SQL since we don't have the Cycles model in the current context
        query = text("SELECT DISTINCT code FROM cycles ORDER BY code")
        result = self.session.exec(query).all()
        return [{"code": row[0]} for row in result]
