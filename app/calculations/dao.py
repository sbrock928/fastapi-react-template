# app/calculations/dao.py
"""Enhanced DAO for calculation operations supporting multiple types."""

from sqlalchemy.orm import Session
from typing import List, Optional
from .models import Calculation, CalculationType, GroupLevel


class CalculationDAO:
    """Enhanced DAO for calculation data access supporting multiple calculation types."""

    def __init__(self, db: Session):
        self.db = db

    def get_all_calculations(
        self,
        group_level: Optional[GroupLevel] = None,
        calculation_type: Optional[CalculationType] = None,
    ) -> List[Calculation]:
        """Get all active calculations, optionally filtered by group level and/or calculation type."""
        query = self.db.query(Calculation).filter(Calculation.is_active == True)

        if group_level:
            query = query.filter(Calculation.group_level == group_level)

        if calculation_type:
            query = query.filter(Calculation.calculation_type == calculation_type)

        return query.order_by(
            Calculation.calculation_type, Calculation.name  # System calculations first
        ).all()

    def get_user_defined_calculations(
        self, group_level: Optional[GroupLevel] = None
    ) -> List[Calculation]:
        """Get only user-defined calculations."""
        return self.get_all_calculations(group_level, CalculationType.USER_DEFINED)

    def get_system_field_calculations(
        self, group_level: Optional[GroupLevel] = None
    ) -> List[Calculation]:
        """Get only system field calculations."""
        return self.get_all_calculations(group_level, CalculationType.SYSTEM_FIELD)

    def get_system_sql_calculations(
        self, group_level: Optional[GroupLevel] = None
    ) -> List[Calculation]:
        """Get only system SQL calculations."""
        return self.get_all_calculations(group_level, CalculationType.SYSTEM_SQL)

    def get_system_calculations(
        self, group_level: Optional[GroupLevel] = None
    ) -> List[Calculation]:
        """Get all system-managed calculations (both field and SQL types)."""
        query = self.db.query(Calculation).filter(
            Calculation.is_active == True, Calculation.is_system_managed == True
        )

        if group_level:
            query = query.filter(Calculation.group_level == group_level)

        return query.order_by(Calculation.calculation_type, Calculation.name).all()

    def get_editable_calculations(
        self, group_level: Optional[GroupLevel] = None
    ) -> List[Calculation]:
        """Get only user-editable calculations."""
        query = self.db.query(Calculation).filter(
            Calculation.is_active == True, Calculation.is_system_managed == False
        )

        if group_level:
            query = query.filter(Calculation.group_level == group_level)

        return query.order_by(Calculation.name).all()

    def get_by_id(self, calc_id: int) -> Optional[Calculation]:
        """Get calculation by ID."""
        return (
            self.db.query(Calculation)
            .filter(Calculation.id == calc_id, Calculation.is_active == True)
            .first()
        )

    def get_by_name_and_group_level(
        self, name: str, group_level: GroupLevel
    ) -> Optional[Calculation]:
        """Get calculation by name and group level."""
        return (
            self.db.query(Calculation)
            .filter(
                Calculation.name == name,
                Calculation.group_level == group_level,
                Calculation.is_active == True,
            )
            .first()
        )

    def get_by_name(self, name: str) -> Optional[Calculation]:
        """Get calculation by name (for backward compatibility)."""
        return (
            self.db.query(Calculation)
            .filter(Calculation.name == name, Calculation.is_active == True)
            .first()
        )

    def get_by_names(self, names: List[str]) -> List[Calculation]:
        """Get calculations by list of names."""
        return (
            self.db.query(Calculation)
            .filter(Calculation.name.in_(names), Calculation.is_active == True)
            .all()
        )

    def get_by_calculation_type(self, calc_type: CalculationType) -> List[Calculation]:
        """Get all calculations of a specific type."""
        return (
            self.db.query(Calculation)
            .filter(Calculation.calculation_type == calc_type, Calculation.is_active == True)
            .order_by(Calculation.name)
            .all()
        )

    def create(self, calculation: Calculation) -> Calculation:
        """Create a new calculation."""
        self.db.add(calculation)
        self.db.commit()
        self.db.refresh(calculation)
        return calculation

    def update(self, calculation: Calculation) -> Calculation:
        """Update an existing calculation."""
        self.db.commit()
        self.db.refresh(calculation)
        return calculation

    def soft_delete(self, calculation: Calculation) -> Calculation:
        """Soft delete a calculation by setting is_active=False."""
        calculation.is_active = False
        self.db.commit()
        return calculation

    def hard_delete(self, calculation: Calculation) -> None:
        """Hard delete a calculation (use with caution)."""
        self.db.delete(calculation)
        self.db.commit()

    def count_by_type(self) -> dict:
        """Get count of calculations by type."""
        counts = {}
        for calc_type in CalculationType:
            count = (
                self.db.query(Calculation)
                .filter(Calculation.calculation_type == calc_type, Calculation.is_active == True)
                .count()
            )
            counts[calc_type.value] = count
        return counts

    def get_system_field_by_source_and_field(
        self, source_model: str, field_name: str, group_level: GroupLevel
    ) -> Optional[Calculation]:
        """Get system field calculation by source model and field name."""
        return (
            self.db.query(Calculation)
            .filter(
                Calculation.calculation_type == CalculationType.SYSTEM_FIELD,
                Calculation.source_model == source_model,
                Calculation.field_name == field_name,
                Calculation.group_level == group_level,
                Calculation.is_active == True,
            )
            .first()
        )

    def bulk_create_system_fields(self, calculations: List[Calculation]) -> List[Calculation]:
        """Bulk create system field calculations for efficiency."""
        self.db.add_all(calculations)
        self.db.commit()

        # Refresh all objects
        for calc in calculations:
            self.db.refresh(calc)

        return calculations
