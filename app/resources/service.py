from sqlalchemy.orm import Session
from typing import List, Optional, Any, Dict, Union
from fastapi import HTTPException
from app.resources.models import User, Employee, Subscriber
from app.resources.schemas import (
    UserCreate,
    UserUpdate,
    UserRead,
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeRead,
    SubscriberCreate,
    SubscriberUpdate,
    SubscriberRead,
    SubscriptionTier,
)
from app.resources.dao import UserDAO, EmployeeDAO, SubscriberDAO
from app.common.base_service import GenericService


def collect_validation_errors() -> Dict:
    """
    Helper function to collect multiple validation errors.

    Returns:
        A dictionary with methods to add errors and generate the final HTTPException
    """
    errors = []

    def add_error(field: str, msg: str, error_type: str = "value_error"):
        """Add an error to the collection"""
        errors.append({"loc": ["body", field], "msg": msg, "type": error_type})

    def has_errors() -> bool:
        """Check if any errors have been collected"""
        return len(errors) > 0

    def raise_if_errors():
        """Raise an HTTPException with all collected errors if any exist"""
        if errors:
            raise HTTPException(status_code=422, detail=errors)

    return {
        "add": add_error,
        "has_errors": has_errors,
        "raise_if_errors": raise_if_errors,
    }


def validation_error(field: str, msg: str, error_type: str = "value_error") -> HTTPException:
    """
    Creates a standardized validation error in Pydantic format for consistent frontend handling

    Args:
        field: The field name that has the error
        msg: The error message to display
        error_type: The type of error (defaults to "value_error")

    Returns:
        HTTPException with a structured error response matching Pydantic's format
    """
    detail = [{"loc": ["body", field], "msg": msg, "type": error_type}]
    return HTTPException(status_code=422, detail=detail)


class UserService(GenericService[User, UserCreate, UserUpdate, UserRead]):
    """User-specific service with custom validations"""

    def __init__(self, session: Session, dao: UserDAO = None):
        super().__init__(session, User, UserCreate, UserUpdate, UserRead)
        self.dao = dao if dao is not None else UserDAO(session, User)

    async def before_create(self, user_data: UserCreate) -> UserCreate:
        """Custom validation before user creation"""
        # Initialize error collector
        errors = collect_validation_errors()

        # Check if username already exists
        existing_user = await self.dao.get_by_username(user_data.username)
        if existing_user:
            errors["add"]("username", "Username already taken", "value_error.already_exists")

        # Check if email already exists
        existing_email = await self.dao.get_by_email(user_data.email)
        if existing_email:
            errors["add"]("email", "Email already registered", "value_error.already_exists")

        # Raise exception with all collected errors if any exist
        errors["raise_if_errors"]()

        return user_data

    async def before_update(self, user_id: int, user_data: UserUpdate) -> UserUpdate:
        """Custom validation before user update"""
        # Get fields that were provided for update
        update_data = user_data.model_dump(exclude_unset=True)

        # Initialize error collector
        errors = collect_validation_errors()

        # If username was provided, check if it's unique
        if "username" in update_data:
            existing_user = await self.dao.get_by_username(update_data["username"])
            if existing_user and existing_user.id != user_id:
                errors["add"]("username", "Username already taken", "value_error.already_exists")

        # If email was provided, check if it's unique
        if "email" in update_data:
            existing_email = await self.dao.get_by_email(update_data["email"])
            if existing_email and existing_email.id != user_id:
                errors["add"]("email", "Email already registered", "value_error.already_exists")

        # Raise exception with all collected errors if any exist
        errors["raise_if_errors"]()

        return user_data

    # Custom methods that don't fit the CRUD pattern
    async def get_by_username(self, username: str) -> UserRead:
        """Get a user by username with proper error handling"""
        user = await self.dao.get_by_username(username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return self.to_read_model(user)


class EmployeeService(GenericService[Employee, EmployeeCreate, EmployeeUpdate, EmployeeRead]):
    """Employee-specific service with custom validations"""

    def __init__(self, session: Session, dao: EmployeeDAO = None):
        super().__init__(session, Employee, EmployeeCreate, EmployeeUpdate, EmployeeRead)
        self.dao = dao if dao is not None else EmployeeDAO(session, Employee)

    async def before_create(self, employee_data: EmployeeCreate) -> EmployeeCreate:
        """Custom validation before employee creation"""
        # Initialize error collector
        errors = collect_validation_errors()

        # Check if employee_id already exists
        existing_emp = await self.dao.get_by_employee_id(employee_data.employee_id)
        if existing_emp:
            errors["add"](
                "employee_id",
                "Employee ID already exists",
                "value_error.already_exists",
            )

        # Check if email already exists
        existing_email = await self.dao.get_by_email(employee_data.email)
        if existing_email:
            errors["add"]("email", "Email already registered", "value_error.already_exists")

        # Raise exception with all collected errors if any exist
        errors["raise_if_errors"]()

        return employee_data

    async def before_update(
        self, employee_id: int, employee_data: EmployeeUpdate
    ) -> EmployeeUpdate:
        """Custom validation before employee update"""
        # Get fields that were provided for update
        update_data = employee_data.model_dump(exclude_unset=True)

        # Initialize error collector
        errors = collect_validation_errors()

        # If employee_id was provided, check if it's unique
        if "employee_id" in update_data:
            existing_emp = await self.dao.get_by_employee_id(update_data["employee_id"])
            if existing_emp and existing_emp.id != employee_id:
                errors["add"](
                    "employee_id",
                    "Employee ID already exists",
                    "value_error.already_exists",
                )

        # If email was provided, check if it's unique
        if "email" in update_data:
            existing_email = await self.dao.get_by_email(update_data["email"])
            if existing_email and existing_email.id != employee_id:
                errors["add"]("email", "Email already registered", "value_error.already_exists")

        # Raise exception with all collected errors if any exist
        errors["raise_if_errors"]()

        return employee_data

    # Custom methods for employee-specific operations
    async def get_employees_by_department(self, department: str) -> List[EmployeeRead]:
        """Get all employees in a specific department"""
        employees = await self.dao.get_by_department(department)
        return self.to_read_model_list(employees)

    async def get_employees_by_position(self, position: str) -> List[EmployeeRead]:
        """Get all employees with a specific position"""
        employees = await self.dao.get_by_position(position)
        return self.to_read_model_list(employees)


class SubscriberService(
    GenericService[Subscriber, SubscriberCreate, SubscriberUpdate, SubscriberRead]
):
    """Subscriber-specific service with custom validations"""

    def __init__(self, session: Session, dao: SubscriberDAO = None):
        super().__init__(session, Subscriber, SubscriberCreate, SubscriberUpdate, SubscriberRead)
        self.dao = dao if dao is not None else SubscriberDAO(session, Subscriber)

    async def before_create(self, subscriber_data: SubscriberCreate) -> SubscriberCreate:
        """Custom validation before subscriber creation"""
        # Initialize error collector
        errors = collect_validation_errors()

        # Check if email already exists
        existing_email = await self.dao.get_by_email(subscriber_data.email)
        if existing_email:
            errors["add"]("email", "Email already registered", "value_error.already_exists")

        # Raise exception with all collected errors if any exist
        errors["raise_if_errors"]()

        return subscriber_data

    async def before_update(
        self, subscriber_id: int, subscriber_data: SubscriberUpdate
    ) -> SubscriberUpdate:
        """Custom validation before subscriber update"""
        # Get fields that were provided for update
        update_data = subscriber_data.model_dump(exclude_unset=True)

        # Initialize error collector
        errors = collect_validation_errors()

        # If email was provided, check if it's unique
        if "email" in update_data:
            existing_email = await self.dao.get_by_email(update_data["email"])
            if existing_email and existing_email.id != subscriber_id:
                errors["add"]("email", "Email already registered", "value_error.already_exists")

        # Raise exception with all collected errors if any exist
        errors["raise_if_errors"]()

        return subscriber_data

    # Custom methods for subscriber-specific operations
    async def get_by_email(self, email: str) -> SubscriberRead:
        """Get a subscriber by email with proper error handling"""
        subscriber = await self.dao.get_by_email(email)
        if not subscriber:
            raise HTTPException(status_code=404, detail="Subscriber not found")
        return self.to_read_model(subscriber)

    async def get_by_subscription_tier(self, tier: SubscriptionTier) -> List[SubscriberRead]:
        """Get all subscribers with a specific subscription tier"""
        subscribers = await self.dao.get_by_subscription_tier(tier)
        return self.to_read_model_list(subscribers)

    async def get_active_subscribers(self) -> List[SubscriberRead]:
        """Get all active subscribers"""
        subscribers = await self.dao.get_active_subscribers()
        return self.to_read_model_list(subscribers)
