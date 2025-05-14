from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional, Union, cast
from app.resources.models import (
    User,
    UserCreate,
    Employee,
    EmployeeCreate,
    Subscriber,
    SubscriberCreate,
    SubscriptionTier,
)
from app.common.base_dao import GenericDAO


class UserDAO(GenericDAO[User, UserCreate]):
    """User-specific DAO with custom methods"""

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get a user by username"""
        user_query = select(self.model_class).where(
            self.model_class.username == username
        )
        result = self.session.execute(user_query)
        user = result.scalar_one_or_none()
        return user

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email"""
        user_query = select(self.model_class).where(self.model_class.email == email)
        result = self.session.execute(user_query)
        user = result.scalar_one_or_none()
        return user

    # Additional custom methods can be added here
    async def get_by_full_name(self, full_name: str) -> List[User]:
        """Get users by full name (might return multiple)"""
        user_query = select(self.model_class).where(
            self.model_class.full_name == full_name
        )
        result = self.session.execute(user_query)
        users = result.scalars().all()
        return users


class EmployeeDAO(GenericDAO[Employee, EmployeeCreate]):
    """Employee-specific DAO with custom methods"""

    async def get_by_employee_id(self, employee_id: str) -> Optional[Employee]:
        """Get an employee by employee_id field"""
        employee_query = select(self.model_class).where(
            self.model_class.employee_id == employee_id
        )
        result = self.session.execute(employee_query)
        employee = result.scalar_one_or_none()
        return employee

    async def get_by_email(self, email: str) -> Optional[Employee]:
        """Get an employee by email"""
        employee_query = select(self.model_class).where(self.model_class.email == email)
        result = self.session.execute(employee_query)
        employee = result.scalar_one_or_none()
        return employee

    async def get_by_department(self, department: str) -> List[Employee]:
        """Get all employees in a specific department"""
        employee_query = select(self.model_class).where(
            self.model_class.department == department
        )
        result = self.session.execute(employee_query)
        employees = result.scalars().all()
        return employees

    async def get_by_position(self, position: str) -> List[Employee]:
        """Get all employees with a specific position"""
        employee_query = select(self.model_class).where(
            self.model_class.position == position
        )
        result = self.session.execute(employee_query)
        employees = result.scalars().all()
        return employees


class SubscriberDAO(GenericDAO[Subscriber, SubscriberCreate]):
    """Subscriber-specific DAO with custom methods"""

    async def get_by_email(self, email: str) -> Optional[Subscriber]:
        """Get a subscriber by email"""
        query = select(self.model_class).where(self.model_class.email == email)
        result = self.session.execute(query)
        subscriber = result.scalar_one_or_none()
        return subscriber

    async def get_by_subscription_tier(
        self, tier: Union[SubscriptionTier, str]
    ) -> List[Subscriber]:
        """Get all subscribers with a specific subscription tier"""
        # Convert enum to string if it's an enum
        tier_value = tier.value if isinstance(tier, SubscriptionTier) else tier

        query = select(self.model_class).where(
            self.model_class.subscription_tier == tier_value
        )
        result = self.session.execute(query)
        subscribers = result.scalars().all()
        return subscribers

    async def get_active_subscribers(self) -> List[Subscriber]:
        """Get all active subscribers"""
        query = select(self.model_class).where(self.model_class.is_active == True)
        result = self.session.execute(query)
        subscribers = result.scalars().all()
        return subscribers
