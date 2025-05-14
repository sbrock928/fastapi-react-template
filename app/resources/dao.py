from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional, Union, cast
from app.resources.models import User, Employee, Subscriber
from app.resources.schemas import SubscriptionTier
from app.common.base_dao import GenericDAO


class UserDAO(GenericDAO[User]):
    """User-specific DAO with custom methods"""

    def __init__(self, session: Session, model_class: type[User]):
        super().__init__(session, model_class)

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get a user by username"""
        stmt = select(self.model_class).where(self.model_class.username == username)
        result = self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email"""
        stmt = select(self.model_class).where(self.model_class.email == email)
        result = self.session.execute(stmt)
        return result.scalars().first()


class EmployeeDAO(GenericDAO[Employee]):
    """Employee-specific DAO with custom methods"""

    def __init__(self, session: Session, model_class: type[Employee]):
        super().__init__(session, model_class)

    async def get_by_employee_id(self, employee_id: str) -> Optional[Employee]:
        """Get an employee by employee_id"""
        stmt = select(self.model_class).where(self.model_class.employee_id == employee_id)
        result = self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_email(self, email: str) -> Optional[Employee]:
        """Get an employee by email"""
        stmt = select(self.model_class).where(self.model_class.email == email)
        result = self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_department(self, department: str) -> List[Employee]:
        """Get employees by department"""
        stmt = select(self.model_class).where(self.model_class.department == department)
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_position(self, position: str) -> List[Employee]:
        """Get employees by position"""
        stmt = select(self.model_class).where(self.model_class.position == position)
        result = self.session.execute(stmt)
        return list(result.scalars().all())


class SubscriberDAO(GenericDAO[Subscriber]):
    """Subscriber-specific DAO with custom methods"""

    def __init__(self, session: Session, model_class: type[Subscriber]):
        super().__init__(session, model_class)

    async def get_by_email(self, email: str) -> Optional[Subscriber]:
        """Get a subscriber by email"""
        stmt = select(self.model_class).where(self.model_class.email == email)
        result = self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_subscription_tier(self, tier: SubscriptionTier) -> List[Subscriber]:
        """Get all subscribers with a specific subscription tier"""
        stmt = select(self.model_class).where(self.model_class.subscription_tier == tier)
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_subscribers(self) -> List[Subscriber]:
        """Get all active subscribers"""
        stmt = select(self.model_class).where(self.model_class.is_active == True)
        result = self.session.execute(stmt)
        return list(result.scalars().all())
