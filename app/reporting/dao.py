"""Data Access Objects for the reporting module."""

import logging
from sqlalchemy.orm import Session
from sqlalchemy import select, func, text
from typing import List, Dict, Any, Optional
from app.resources.models import User, Employee, Subscriber
from app.reporting.models import Report
from app.logging.models import Log


class ReportingDAO:
    """Data access methods for reports and statistics."""

    def __init__(self, session: Session):
        self.session = session

    async def get_user_count(self) -> int:
        """Get the total number of users"""
        result = self.session.execute(select(func.count()).select_from(User))
        return int(result.scalar_one() or 0)

    async def get_employee_count(self) -> int:
        """Get the total number of employees"""
        result = self.session.execute(select(func.count()).select_from(Employee))
        return int(result.scalar_one() or 0)

    async def get_subscriber_count(self) -> int:
        """Get the total number of subscribers"""
        result = self.session.execute(select(func.count()).select_from(Subscriber))
        return int(result.scalar_one() or 0)

    async def get_log_count(self) -> int:
        """Get the total number of logs"""
        result = self.session.execute(select(func.count()).select_from(Log))
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
        except Exception:  # pylint: disable=broad-except
            # If the table doesn't exist yet or there's another error
            return []

    async def get_employees_by_department(self) -> List[Dict[str, Any]]:
        """Get employee counts grouped by department"""
        query = (
            select(Employee.department, func.count().label("count"))
            .group_by(Employee.department)
            .order_by(Employee.department)
        )

        result = self.session.execute(query)
        departments = []
        for row in result:
            departments.append(
                {
                    "department": row[0],  # Access by index rather than attribute name
                    "count": row[1],
                }
            )
        return departments

    async def get_resource_counts(self, cycle_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get counts of different resource types

        Args:
            cycle_code: Optional filter, reserved for future implementation
                        when cycle filtering is implemented

        Returns:
            List of dictionaries with resource counts
        """
        # This is a simplified query that doesn't use cycle_code yet
        # Future implementation will use cycle_code for filtering

        user_count = await self.get_user_count()
        employee_count = await self.get_employee_count()
        subscriber_count = await self.get_subscriber_count()

        return [
            {"resource_type": "Users", "count": user_count},
            {"resource_type": "Employees", "count": employee_count},
            {"resource_type": "Subscribers", "count": subscriber_count},
        ]

    async def get_employee_details(self) -> List[Dict[str, Any]]:
        """Get detailed employee information for reporting"""
        # Import needed models/schemas
        from app.resources.models import Employee, Department
        from sqlalchemy import select
        
        try:
            # Query to get employee details with department name
            query = (
                select(Employee, Department.name.label("department_name"))
                .join(Department, Employee.department_id == Department.id)
            )
            
            # Execute query without awaiting
            result = self.session.execute(query)
            
            # Process results into dictionary format
            employee_data = []
            for row in result.all():
                employee = row[0]
                department_name = row[1]
                
                employee_dict = {
                    "id": employee.id,
                    "first_name": employee.first_name,
                    "last_name": employee.last_name,
                    "email": employee.email,
                    "hire_date": employee.hire_date.isoformat() if employee.hire_date else None,
                    "position": employee.position,
                    "department": department_name,
                    "salary": employee.salary,
                    "is_active": employee.is_active,
                }
                employee_data.append(employee_dict)
                
            return employee_data
        except Exception as e:
            logging.error(f"Error in get_employee_details: {str(e)}")
            raise

    async def get_user_details(
        self, 
        username: Optional[str] = None, 
        email: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_superuser: Optional[bool] = None,
        days: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get detailed user information for reporting with filtering options
        
        Args:
            username: Optional filter by username (partial match)
            email: Optional filter by email (partial match)
            is_active: Optional filter by active status (ignored - not in model)
            is_superuser: Optional filter by superuser status (ignored - not in model)
            days: Optional number of days filter (ignored - no date field in User model)
        """
        # Import needed models
        from app.resources.models import User
        from sqlalchemy import select
        
        try:
            # Start building the query
            query = select(User)
            
            # Apply filters if they are provided
            filters = []
            
            if username:
                filters.append(User.username.ilike(f"%{username}%"))
                
            if email:
                filters.append(User.email.ilike(f"%{email}%"))
            
            # Apply filters to query if any exist
            if filters:
                from sqlalchemy import and_
                query = query.where(and_(*filters))
                
            # Execute query - don't await the execution result
            result = self.session.execute(query)
            
            # Process results into dictionary format
            user_data = []
            for row in result.all():
                user = row[0]
                
                user_dict = {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name
                }
                user_data.append(user_dict)
                
            return user_data
        except Exception as e:
            logging.error(f"Error in get_user_details: {str(e)}")
            raise

    async def get_subscriber_details(self) -> List[Dict[str, Any]]:
        """Get detailed subscriber information for reporting"""
        # Import needed models
        from app.resources.models import Subscriber
        from sqlalchemy import select
        
        try:
            # Query to get all subscribers
            query = select(Subscriber)
            result = self.session.execute(query)
            
            # Process results into dictionary format
            subscriber_data = []
            for row in result.all():
                subscriber = row[0]
                
                subscriber_dict = {
                    "id": subscriber.id,
                    "email": subscriber.email,
                    "name": subscriber.name,
                    "subscription_date": subscriber.subscription_date.isoformat() if subscriber.subscription_date else None,
                    "subscription_tier": subscriber.subscription_tier,
                    "is_active": subscriber.is_active
                }
                subscriber_data.append(subscriber_dict)
                
            return subscriber_data
        except Exception as e:
            logging.error(f"Error in get_subscriber_details: {str(e)}")
            raise

    async def get_log_details(self) -> List[Dict[str, Any]]:
        """Get detailed log information for reporting"""
        # Import needed models
        from app.logging.models import Log
        from sqlalchemy import select, desc
        
        try:
            # Query to get all logs, ordered by most recent first
            query = select(Log).order_by(desc(Log.timestamp))
            result = self.session.execute(query)
            
            # Process results into dictionary format
            log_data = []
            for row in result.all():
                log = row[0]
                
                log_dict = {
                    "id": log.id,
                    "level": log.level,
                    "message": log.message,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    "user_id": log.user_id,
                    "username": log.username,
                    "source": log.source,
                    "request_id": log.request_id,
                    "method": log.method,
                    "path": log.path,
                    "status_code": log.status_code,
                    "host": log.host,
                    "app_id": log.app_id
                }
                log_data.append(log_dict)
                
            return log_data
        except Exception as e:
            logging.error(f"Error in get_log_details: {str(e)}")
            raise


class ReportDAO:
    """DB functionality for interaction with `Report` objects in config database."""

    def __init__(self, db_session: Session):
        self.db = db_session

    async def get_all(self) -> List[Report]:
        """Get all reports"""
        stmt = select(Report).where(Report.is_active == True)
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, report_id: int) -> Optional[Report]:
        """Get a report by ID"""
        stmt = select(Report).where(Report.id == report_id)
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_created_by(self, created_by: str) -> List[Report]:
        """Get reports by creator"""
        stmt = select(Report).where(
            Report.created_by == created_by,
            Report.is_active == True
        ).order_by(Report.created_date.desc())
        result = self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_name_and_creator(self, name: str, created_by: str) -> Optional[Report]:
        """Get a report by name and creator (for duplicate checking)"""
        stmt = select(Report).where(
            Report.name == name,
            Report.created_by == created_by,
            Report.is_active == True
        )
        result = self.db.execute(stmt)
        return result.scalars().first()

    async def create(self, report_obj: Report) -> Report:
        """Create a new report"""
        self.db.add(report_obj)
        self.db.commit()
        self.db.refresh(report_obj)
        return report_obj

    async def update(self, report_obj: Report) -> Report:
        """Update an existing report"""
        self.db.add(report_obj)
        self.db.commit()
        self.db.refresh(report_obj)
        return report_obj

    async def delete(self, report_id: int) -> bool:
        """Soft delete a report by ID"""
        report = await self.get_by_id(report_id)
        if report:
            report.is_active = False
            await self.update(report)
            return True
        return False

    async def hard_delete(self, report_id: int) -> bool:
        """Hard delete a report by ID"""
        report = await self.get_by_id(report_id)
        if report:
            self.db.delete(report)
            self.db.commit()
            return True
        return False

    async def get_report_count(self) -> int:
        """Get total count of active reports"""
        result = self.db.execute(select(func.count()).select_from(Report).where(Report.is_active == True))
        return int(result.scalar_one() or 0)

    async def get_reports_by_scope(self, scope: str) -> List[Report]:
        """Get reports by scope (DEAL or TRANCHE)"""
        stmt = select(Report).where(
            Report.scope == scope,
            Report.is_active == True
        ).order_by(Report.created_date.desc())
        result = self.db.execute(stmt)
        return list(result.scalars().all())
    

    """Data Access Objects for tranche overrides."""

from sqlalchemy.orm import Session
from sqlalchemy import select, delete, func, and_
from typing import List, Optional, Dict, Any
from app.reporting.models import ReportTrancheOverride
from app.reporting.schemas import OverrideType


class OverrideDAO:
    """Data access methods for tranche overrides."""

    def __init__(self, session: Session):
        self.session = session

    async def get_all_for_report(self, report_id: int) -> List[ReportTrancheOverride]:
        """Get all overrides for a specific report."""
        stmt = select(ReportTrancheOverride).where(
            ReportTrancheOverride.report_id == report_id
        ).order_by(
            ReportTrancheOverride.tranche_id,
            ReportTrancheOverride.column_name
        )
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_tranche(self, report_id: int, tranche_id: int) -> List[ReportTrancheOverride]:
        """Get all overrides for a specific tranche in a report."""
        stmt = select(ReportTrancheOverride).where(
            and_(
                ReportTrancheOverride.report_id == report_id,
                ReportTrancheOverride.tranche_id == tranche_id
            )
        ).order_by(ReportTrancheOverride.column_name)
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_column(self, report_id: int, column_name: str) -> List[ReportTrancheOverride]:
        """Get all overrides for a specific column in a report."""
        stmt = select(ReportTrancheOverride).where(
            and_(
                ReportTrancheOverride.report_id == report_id,
                ReportTrancheOverride.column_name == column_name
            )
        ).order_by(ReportTrancheOverride.tranche_id)
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_specific_override(
        self, 
        report_id: int, 
        tranche_id: int, 
        column_name: str
    ) -> Optional[ReportTrancheOverride]:
        """Get a specific override by report, tranche, and column."""
        stmt = select(ReportTrancheOverride).where(
            and_(
                ReportTrancheOverride.report_id == report_id,
                ReportTrancheOverride.tranche_id == tranche_id,
                ReportTrancheOverride.column_name == column_name
            )
        )
        result = self.session.execute(stmt)
        return result.scalars().first()

    async def create_override(self, override_obj: ReportTrancheOverride) -> ReportTrancheOverride:
        """Create a new override."""
        self.session.add(override_obj)
        self.session.commit()
        self.session.refresh(override_obj)
        return override_obj

    async def update_override(self, override_obj: ReportTrancheOverride) -> ReportTrancheOverride:
        """Update an existing override."""
        self.session.add(override_obj)
        self.session.commit()
        self.session.refresh(override_obj)
        return override_obj

    async def upsert_override(
        self,
        report_id: int,
        tranche_id: int,
        column_name: str,
        override_value: str,
        override_type: str,
        notes: Optional[str],
        created_by: str
    ) -> ReportTrancheOverride:
        """Create or update an override (upsert operation)."""
        existing = await self.get_specific_override(report_id, tranche_id, column_name)
        
        if existing:
            # Update existing override
            existing.override_value = override_value
            existing.override_type = override_type
            existing.notes = notes
            return await self.update_override(existing)
        else:
            # Create new override
            new_override = ReportTrancheOverride(
                report_id=report_id,
                tranche_id=tranche_id,
                column_name=column_name,
                override_value=override_value,
                override_type=override_type,
                notes=notes,
                created_by=created_by
            )
            return await self.create_override(new_override)

    async def delete_override(
        self, 
        report_id: int, 
        tranche_id: int, 
        column_name: str
    ) -> bool:
        """Delete a specific override."""
        stmt = delete(ReportTrancheOverride).where(
            and_(
                ReportTrancheOverride.report_id == report_id,
                ReportTrancheOverride.tranche_id == tranche_id,
                ReportTrancheOverride.column_name == column_name
            )
        )
        result = self.session.execute(stmt)
        self.session.commit()
        return result.rowcount > 0

    async def delete_all_for_report(self, report_id: int) -> int:
        """Delete all overrides for a report."""
        stmt = delete(ReportTrancheOverride).where(
            ReportTrancheOverride.report_id == report_id
        )
        result = self.session.execute(stmt)
        self.session.commit()
        return result.rowcount

    async def delete_all_for_tranche(self, report_id: int, tranche_id: int) -> int:
        """Delete all overrides for a specific tranche in a report."""
        stmt = delete(ReportTrancheOverride).where(
            and_(
                ReportTrancheOverride.report_id == report_id,
                ReportTrancheOverride.tranche_id == tranche_id
            )
        )
        result = self.session.execute(stmt)
        self.session.commit()
        return result.rowcount

    async def get_override_summary(self, report_id: int) -> Dict[str, Any]:
        """Get summary statistics about overrides for a report."""
        # Total count
        total_stmt = select(func.count()).select_from(ReportTrancheOverride).where(
            ReportTrancheOverride.report_id == report_id
        )
        total_count = self.session.execute(total_stmt).scalar_one_or_none() or 0

        # Count by type
        type_stmt = select(
            ReportTrancheOverride.override_type,
            func.count()
        ).where(
            ReportTrancheOverride.report_id == report_id
        ).group_by(ReportTrancheOverride.override_type)
        
        type_result = self.session.execute(type_stmt).all()
        overrides_by_type = {row[0]: row[1] for row in type_result}

        # Count by column
        column_stmt = select(
            ReportTrancheOverride.column_name,
            func.count()
        ).where(
            ReportTrancheOverride.report_id == report_id
        ).group_by(ReportTrancheOverride.column_name)
        
        column_result = self.session.execute(column_stmt).all()
        overrides_by_column = {row[0]: row[1] for row in column_result}

        # Last updated
        last_updated_stmt = select(
            func.max(ReportTrancheOverride.updated_date)
        ).where(ReportTrancheOverride.report_id == report_id)
        last_updated = self.session.execute(last_updated_stmt).scalar_one_or_none()

        return {
            "report_id": report_id,
            "total_overrides": total_count,
            "overrides_by_type": overrides_by_type,
            "overrides_by_column": overrides_by_column,
            "last_updated": last_updated
        }

    async def bulk_create_overrides(self, overrides: List[ReportTrancheOverride]) -> List[ReportTrancheOverride]:
        """Create multiple overrides in bulk."""
        for override in overrides:
            self.session.add(override)
        
        self.session.commit()
        
        # Refresh all objects
        for override in overrides:
            self.session.refresh(override)
        
        return overrides

    async def get_overrideable_tranches(self, report_id: int) -> List[int]:
        """Get list of tranche IDs that have overrides in this report."""
        stmt = select(ReportTrancheOverride.tranche_id.distinct()).where(
            ReportTrancheOverride.report_id == report_id
        )
        result = self.session.execute(stmt)
        return [row[0] for row in result.all()]