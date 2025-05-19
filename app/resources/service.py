"""Service layer for managing user, employee, and subscriber resources."""

from typing import List, Optional, Dict, Any
from fastapi import HTTPException
from app.resources.dao import UserDAO, EmployeeDAO, SubscriberDAO
from app.resources.models import User, Employee, Subscriber
from app.resources.schemas import (
    UserRead,
    UserCreate,
    UserUpdate,
    EmployeeRead,
    EmployeeCreate,
    EmployeeUpdate,
    SubscriberRead,
    SubscriberCreate,
    SubscriberUpdate,
    SubscriptionTier,
)


def collect_validation_errors() -> Dict:
    """
    Helper function to collect multiple validation errors.

    Returns:
        A dictionary with methods to add errors and generate the final HTTPException
    """
    errors = []

    def add_error(field: str, msg: str, error_type: str = "value_error") -> None:
        """Add an error to the collection"""
        errors.append({"loc": ["body", field], "msg": msg, "type": error_type})

    def has_errors() -> bool:
        """Check if any errors have been collected"""
        return len(errors) > 0

    def raise_if_errors() -> Any:
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


class UserService:
    """Service for interacting with User resources."""

    def __init__(self, dao: UserDAO) -> None:
        self.dao = dao

    async def get_all(self) -> List[UserRead]:
        """Get all users."""
        users = await self.dao.get_all()
        return [UserRead.model_validate(user) for user in users]

    async def get_by_id(self, user_id: int) -> Optional[UserRead]:
        """Get a user by ID."""
        user = await self.dao.get_by_id(user_id)
        if not user:
            return None
        return UserRead.model_validate(user)

    async def get_by_username(self, username: str) -> Optional[UserRead]:
        """Get a user by username."""
        user = await self.dao.get_by_username(username)
        if not user:
            return None
        return UserRead.model_validate(user)

    async def get_by_email(self, email: str) -> Optional[UserRead]:
        """Get a user by email."""
        user = await self.dao.get_by_email(email)
        if not user:
            return None
        return UserRead.model_validate(user)

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
        # Initialize error collector
        errors = collect_validation_errors()

        # Get current user to check if we're changing username/email
        current_user = await self.dao.get_by_id(user_id)
        if not current_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check if username already exists (if changed)
        if current_user.username != user_data.username:
            existing_user = await self.dao.get_by_username(user_data.username)
            if existing_user:
                errors["add"]("username", "Username already taken", "value_error.already_exists")

        # Check if email already exists (if changed)
        if current_user.email != user_data.email:
            existing_email = await self.dao.get_by_email(user_data.email)
            if existing_email:
                errors["add"]("email", "Email already registered", "value_error.already_exists")

        # Raise exception with all collected errors if any exist
        errors["raise_if_errors"]()

        return user_data

    async def create(self, user_data: UserCreate) -> UserRead:
        """Create a new user."""
        # Validate user data before creation
        await self.before_create(user_data)

        user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
        )
        created_user = await self.dao.create(user)
        return UserRead.model_validate(created_user)

    async def update(self, user_id: int, user_data: UserUpdate) -> Optional[UserRead]:
        """Update a user."""
        # Validate user data before update
        await self.before_update(user_id, user_data)

        user = await self.dao.get_by_id(user_id)
        if not user:
            return None

        user.username = user_data.username
        user.email = user_data.email
        user.full_name = user_data.full_name

        updated_user = await self.dao.update(user)
        return UserRead.model_validate(updated_user)

    async def delete(self, user_id: int) -> bool:
        """Delete a user."""
        return await self.dao.delete(user_id)


class EmployeeService:
    """Service for interacting with Employee resources."""

    def __init__(self, dao: EmployeeDAO) -> None:
        self.dao = dao

    async def get_all(self) -> List[EmployeeRead]:
        """Get all employees."""
        employees = await self.dao.get_all()
        return [EmployeeRead.model_validate(employee) for employee in employees]

    async def get_by_id(self, employee_id: int) -> Optional[EmployeeRead]:
        """Get an employee by ID."""
        employee = await self.dao.get_by_id(employee_id)
        if not employee:
            return None
        return EmployeeRead.model_validate(employee)

    async def get_by_employee_id(self, employee_id: str) -> Optional[EmployeeRead]:
        """Get an employee by employee_id."""
        employee = await self.dao.get_by_employee_id(employee_id)
        if not employee:
            return None
        return EmployeeRead.model_validate(employee)

    async def get_by_email(self, email: str) -> Optional[EmployeeRead]:
        """Get an employee by email."""
        employee = await self.dao.get_by_email(email)
        if not employee:
            return None
        return EmployeeRead.model_validate(employee)

    async def get_employees_by_department(self, department: str) -> List[EmployeeRead]:
        """Get employees by department."""
        employees = await self.dao.get_by_department(department)
        return [EmployeeRead.model_validate(employee) for employee in employees]

    async def get_employees_by_position(self, position: str) -> List[EmployeeRead]:
        """Get employees by position."""
        employees = await self.dao.get_by_position(position)
        return [EmployeeRead.model_validate(employee) for employee in employees]

    async def before_create(self, employee_data: EmployeeCreate) -> EmployeeCreate:
        """Custom validation before employee creation"""
        # Initialize error collector
        errors = collect_validation_errors()

        # Check if employee_id already exists
        existing_employee = await self.dao.get_by_employee_id(employee_data.employee_id)
        if existing_employee:
            errors["add"]("employee_id", "Employee ID already in use", "value_error.already_exists")

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
        # Initialize error collector
        errors = collect_validation_errors()

        # Get current employee to check if we're changing employee_id/email
        current_employee = await self.dao.get_by_id(employee_id)
        if not current_employee:
            raise HTTPException(status_code=404, detail="Employee not found")

        # Check if employee_id already exists (if changed)
        if current_employee.employee_id != employee_data.employee_id:
            existing_employee = await self.dao.get_by_employee_id(employee_data.employee_id)
            if existing_employee:
                errors["add"](
                    "employee_id", "Employee ID already in use", "value_error.already_exists"
                )

        # Check if email already exists (if changed)
        if current_employee.email != employee_data.email:
            existing_email = await self.dao.get_by_email(employee_data.email)
            if existing_email:
                errors["add"]("email", "Email already registered", "value_error.already_exists")

        # Raise exception with all collected errors if any exist
        errors["raise_if_errors"]()

        return employee_data

    async def create(self, employee_data: EmployeeCreate) -> EmployeeRead:
        """Create a new employee."""
        # Validate employee data before creation
        await self.before_create(employee_data)

        employee = Employee(
            employee_id=employee_data.employee_id,
            email=employee_data.email,
            full_name=employee_data.full_name,
            department=employee_data.department,
            position=employee_data.position,
        )
        created_employee = await self.dao.create(employee)
        return EmployeeRead.model_validate(created_employee)

    async def update(
        self, employee_id: int, employee_data: EmployeeUpdate
    ) -> Optional[EmployeeRead]:
        """Update an employee."""
        # Validate employee data before update
        await self.before_update(employee_id, employee_data)

        employee = await self.dao.get_by_id(employee_id)
        if not employee:
            return None

        employee.employee_id = employee_data.employee_id
        employee.email = employee_data.email
        employee.full_name = employee_data.full_name
        employee.department = employee_data.department
        employee.position = employee_data.position

        updated_employee = await self.dao.update(employee)
        return EmployeeRead.model_validate(updated_employee)

    async def delete(self, employee_id: int) -> bool:
        """Delete an employee."""
        return await self.dao.delete(employee_id)


class SubscriberService:
    """Service for interacting with Subscriber resources."""

    def __init__(self, dao: SubscriberDAO) -> None:
        self.dao = dao

    async def get_all(self) -> List[SubscriberRead]:
        """Get all subscribers."""
        subscribers = await self.dao.get_all()
        return [SubscriberRead.model_validate(subscriber) for subscriber in subscribers]

    async def get_by_id(self, subscriber_id: int) -> Optional[SubscriberRead]:
        """Get a subscriber by ID."""
        subscriber = await self.dao.get_by_id(subscriber_id)
        if not subscriber:
            return None
        return SubscriberRead.model_validate(subscriber)

    async def get_by_email(self, email: str) -> Optional[SubscriberRead]:
        """Get a subscriber by email."""
        subscriber = await self.dao.get_by_email(email)
        if not subscriber:
            return None
        return SubscriberRead.model_validate(subscriber)

    async def get_by_subscription_tier(self, tier: SubscriptionTier) -> List[SubscriberRead]:
        """Get subscribers by tier."""
        subscribers = await self.dao.get_by_subscription_tier(tier)
        return [SubscriberRead.model_validate(subscriber) for subscriber in subscribers]

    async def get_active_subscribers(self) -> List[SubscriberRead]:
        """Get active subscribers."""
        subscribers = await self.dao.get_active_subscribers()
        return [SubscriberRead.model_validate(subscriber) for subscriber in subscribers]

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
        # Initialize error collector
        errors = collect_validation_errors()

        # Get current subscriber to check if we're changing email
        current_subscriber = await self.dao.get_by_id(subscriber_id)
        if not current_subscriber:
            raise HTTPException(status_code=404, detail="Subscriber not found")

        # Check if email already exists (if changed)
        if current_subscriber.email != subscriber_data.email:
            existing_email = await self.dao.get_by_email(subscriber_data.email)
            if existing_email:
                errors["add"]("email", "Email already registered", "value_error.already_exists")

        # Raise exception with all collected errors if any exist
        errors["raise_if_errors"]()

        return subscriber_data

    async def create(self, subscriber_data: SubscriberCreate) -> SubscriberRead:
        """Create a new subscriber."""
        # Validate subscriber data before creation
        await self.before_create(subscriber_data)

        subscriber = Subscriber(
            email=subscriber_data.email,
            full_name=subscriber_data.full_name,
            subscription_tier=subscriber_data.subscription_tier.value,
            signup_date=subscriber_data.signup_date,
            is_active=subscriber_data.is_active,
            last_billing_date=subscriber_data.last_billing_date,
        )
        created_subscriber = await self.dao.create(subscriber)
        return SubscriberRead.model_validate(created_subscriber)

    async def update(
        self, subscriber_id: int, subscriber_data: SubscriberUpdate
    ) -> Optional[SubscriberRead]:
        """Update a subscriber."""
        # Validate subscriber data before update
        await self.before_update(subscriber_id, subscriber_data)

        subscriber = await self.dao.get_by_id(subscriber_id)
        if not subscriber:
            return None

        subscriber.email = subscriber_data.email
        subscriber.full_name = subscriber_data.full_name
        subscriber.subscription_tier = subscriber_data.subscription_tier.value
        subscriber.is_active = subscriber_data.is_active
        subscriber.last_billing_date = subscriber_data.last_billing_date

        updated_subscriber = await self.dao.update(subscriber)
        return SubscriberRead.model_validate(updated_subscriber)

    async def delete(self, subscriber_id: int) -> bool:
        """Delete a subscriber."""
        return await self.dao.delete(subscriber_id)
