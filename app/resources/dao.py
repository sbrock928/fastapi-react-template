from sqlmodel import Session, select
from typing import List, Optional
from app.resources.models import (
    User,
    Employee,
    UserBase,
    EmployeeBase,
    Subscriber,
    SubscriberBase,
    SubscriptionTier,
)
from app.common.base_dao import GenericDAO


class UserDAO(GenericDAO[User, UserBase]):
    """User-specific DAO with custom methods"""

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get a user by username"""
        user_query = select(self.model_class).where(
            self.model_class.username == username
        )
        user = self.session.exec(user_query).first()
        return user

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email"""
        user_query = select(self.model_class).where(self.model_class.email == email)
        user = self.session.exec(user_query).first()
        return user

    # Additional custom methods can be added here
    async def get_by_full_name(self, full_name: str) -> List[User]:
        """Get users by full name (might return multiple)"""
        user_query = select(self.model_class).where(
            self.model_class.full_name == full_name
        )
        users = self.session.exec(user_query).all()
        return users


class EmployeeDAO(GenericDAO[Employee, EmployeeBase]):
    """Employee-specific DAO with custom methods"""

    async def get_by_employee_id(self, employee_id: str) -> Optional[Employee]:
        """Get an employee by employee_id field"""
        employee_query = select(self.model_class).where(
            self.model_class.employee_id == employee_id
        )
        employee = self.session.exec(employee_query).first()
        return employee

    async def get_by_email(self, email: str) -> Optional[Employee]:
        """Get an employee by email"""
        employee_query = select(self.model_class).where(self.model_class.email == email)
        employee = self.session.exec(employee_query).first()
        return employee

    async def get_by_department(self, department: str) -> List[Employee]:
        """Get all employees in a specific department"""
        employee_query = select(self.model_class).where(
            self.model_class.department == department
        )
        employees = self.session.exec(employee_query).all()
        return employees

    async def get_by_position(self, position: str) -> List[Employee]:
        """Get all employees with a specific position"""
        employee_query = select(self.model_class).where(
            self.model_class.position == position
        )
        employees = self.session.exec(employee_query).all()
        return employees


class SubscriberDAO(GenericDAO[Subscriber, SubscriberBase]):
    """Subscriber-specific DAO with custom methods"""

    async def get_by_email(self, email: str) -> Optional[Subscriber]:
        """Get a subscriber by email"""
        query = select(self.model_class).where(self.model_class.email == email)
        subscriber = self.session.exec(query).first()
        return subscriber

    async def get_by_subscription_tier(
        self, tier: SubscriptionTier
    ) -> List[Subscriber]:
        """Get all subscribers with a specific subscription tier"""
        query = select(self.model_class).where(
            self.model_class.subscription_tier == tier
        )
        subscribers = self.session.exec(query).all()
        return subscribers

    async def get_active_subscribers(self) -> List[Subscriber]:
        """Get all active subscribers"""
        query = select(self.model_class).where(self.model_class.is_active == True)
        subscribers = self.session.exec(query).all()
        return subscribers
