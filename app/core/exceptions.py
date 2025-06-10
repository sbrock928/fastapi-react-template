# app/core/exceptions.py
"""Custom exceptions for the application"""


class ReportingSystemException(Exception):
    """Base exception for the reporting system"""

    pass


class CalculationNotFoundError(ReportingSystemException):
    """Raised when a calculation is not found"""

    pass


class CalculationAlreadyExistsError(ReportingSystemException):
    """Raised when trying to create a calculation that already exists"""

    pass


class InvalidCalculationError(ReportingSystemException):
    """Raised when a calculation is invalid"""

    pass


class ReportGenerationError(ReportingSystemException):
    """Raised when report generation fails"""

    pass


class DataWarehouseError(ReportingSystemException):
    """Raised when data warehouse operations fail"""

    pass


class ConfigurationError(ReportingSystemException):
    """Raised when configuration operations fail"""

    pass
