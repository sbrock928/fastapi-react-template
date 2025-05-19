from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from app.resources.models import User, Employee, Subscriber
from app.resources.schemas import SubscriptionTier


class UserDAO:
    """DB functionality for interaction with `User` objects."""

    def __init__(self, db_session: Session):
        self.db = db_session

    async def get_all(self) -> List[User]:
        """Get all users"""
        stmt = select(User)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get a user by ID"""
        stmt = select(User).where(User.id == user_id)
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get a user by username"""
        stmt = select(User).where(User.username == username)
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email"""
        stmt = select(User).where(User.email == email)
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def create(self, user_obj: User) -> User:
        """Create a new user"""
        self.db.add(user_obj)
        self.db.flush()
        self.db.refresh(user_obj)
        return user_obj

    async def update(self, user_obj: User) -> User:
        """Update an existing user"""
        self.db.add(user_obj)
        self.db.flush()
        self.db.refresh(user_obj)
        return user_obj

    async def delete(self, user_id: int) -> bool:
        """Delete a user by ID"""
        user = await self.get_by_id(user_id)
        if user:
            self.db.delete(user)
            self.db.flush()
            return True
        return False


class EmployeeDAO:
    """DB functionality for interaction with `Employee` objects."""

    def __init__(self, db_session: Session):
        self.db = db_session

    async def get_all(self) -> List[Employee]:
        """Get all employees"""
        stmt = select(Employee)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, employee_id: int) -> Optional[Employee]:
        """Get an employee by ID"""
        stmt = select(Employee).where(Employee.id == employee_id)
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_employee_id(self, employee_id: str) -> Optional[Employee]:
        """Get an employee by employee_id"""
        stmt = select(Employee).where(Employee.employee_id == employee_id)
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_email(self, email: str) -> Optional[Employee]:
        """Get an employee by email"""
        stmt = select(Employee).where(Employee.email == email)
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_department(self, department: str) -> List[Employee]:
        """Get employees by department"""
        stmt = select(Employee).where(Employee.department == department)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_position(self, position: str) -> List[Employee]:
        """Get employees by position"""
        stmt = select(Employee).where(Employee.position == position)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, employee_obj: Employee) -> Employee:
        """Create a new employee"""
        self.db.add(employee_obj)
        self.db.flush()
        self.db.refresh(employee_obj)
        return employee_obj

    async def update(self, employee_obj: Employee) -> Employee:
        """Update an existing employee"""
        self.db.add(employee_obj)
        self.db.flush()
        self.db.refresh(employee_obj)
        return employee_obj

    async def delete(self, employee_id: int) -> bool:
        """Delete an employee by ID"""
        employee = await self.get_by_id(employee_id)
        if employee:
            self.db.delete(employee)
            self.db.flush()
            return True
        return False


class SubscriberDAO:
    """DB functionality for interaction with `Subscriber` objects."""

    def __init__(self, db_session: Session):
        self.db = db_session

    async def get_all(self) -> List[Subscriber]:
        """Get all subscribers"""
        stmt = select(Subscriber)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, subscriber_id: int) -> Optional[Subscriber]:
        """Get a subscriber by ID"""
        stmt = select(Subscriber).where(Subscriber.id == subscriber_id)
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_email(self, email: str) -> Optional[Subscriber]:
        """Get a subscriber by email"""
        stmt = select(Subscriber).where(Subscriber.email == email)
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_subscription_tier(self, tier: SubscriptionTier) -> List[Subscriber]:
        """Get all subscribers with a specific subscription tier"""
        stmt = select(Subscriber).where(Subscriber.subscription_tier == tier)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_active_subscribers(self) -> List[Subscriber]:
        """Get all active subscribers"""
        stmt = select(Subscriber).where(Subscriber.is_active == True)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, subscriber_obj: Subscriber) -> Subscriber:
        """Create a new subscriber"""
        self.db.add(subscriber_obj)
        self.db.flush()
        self.db.refresh(subscriber_obj)
        return subscriber_obj

    async def update(self, subscriber_obj: Subscriber) -> Subscriber:
        """Update an existing subscriber"""
        self.db.add(subscriber_obj)
        self.db.flush()
        self.db.refresh(subscriber_obj)
        return subscriber_obj

    async def delete(self, subscriber_id: int) -> bool:
        """Delete a subscriber by ID"""
        subscriber = await self.get_by_id(subscriber_id)
        if subscriber:
            self.db.delete(subscriber)
            self.db.flush()
            return True
        return False
