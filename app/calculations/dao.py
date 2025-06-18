# app/calculations/dao.py
"""Unified Data Access Object for the calculation system"""

from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from .models import Calculation, GroupLevel, CalculationType


class UnifiedCalculationDAO:
    """Unified DAO for all calculation types"""

    def __init__(self, db: Session):
        self.db = db

    def get_all(self, calculation_type: Optional[CalculationType] = None, group_level: Optional[GroupLevel] = None) -> List[Calculation]:
        """Get all active calculations with optional filtering"""
        query = self.db.query(Calculation).filter(Calculation.is_active == True)
        
        if calculation_type:
            query = query.filter(Calculation.calculation_type == calculation_type)
        
        if group_level:
            query = query.filter(Calculation.group_level == group_level)
        
        return query.order_by(Calculation.name).all()

    def get_by_id(self, calc_id: int) -> Optional[Calculation]:
        """Get calculation by ID"""
        return (
            self.db.query(Calculation)
            .filter(Calculation.id == calc_id, Calculation.is_active == True)
            .first()
        )

    def get_by_type(self, calculation_type: CalculationType, group_level: Optional[GroupLevel] = None) -> List[Calculation]:
        """Get calculations by type"""
        query = self.db.query(Calculation).filter(
            Calculation.calculation_type == calculation_type,
            Calculation.is_active == True
        )
        
        if group_level:
            query = query.filter(Calculation.group_level == group_level)
        
        return query.order_by(Calculation.name).all()

    def get_by_source_field(self, source_field: str) -> Optional[Calculation]:
        """Get user calculation by source_field"""
        return (
            self.db.query(Calculation)
            .filter(
                Calculation.source_field == source_field,
                Calculation.calculation_type == CalculationType.USER_AGGREGATION,
                Calculation.is_active == True
            )
            .first()
        )

    def get_by_result_column_name(self, result_column_name: str) -> Optional[Calculation]:
        """Get system calculation by result_column_name"""
        return (
            self.db.query(Calculation)
            .filter(
                Calculation.result_column_name == result_column_name,
                Calculation.calculation_type == CalculationType.SYSTEM_SQL,
                Calculation.is_active == True
            )
            .first()
        )

    def get_by_name_and_group_level(self, name: str, group_level: GroupLevel, calculation_type: Optional[CalculationType] = None) -> Optional[Calculation]:
        """Get calculation by name and group level"""
        query = self.db.query(Calculation).filter(
            Calculation.name == name,
            Calculation.group_level == group_level,
            Calculation.is_active == True,
        )
        
        if calculation_type:
            query = query.filter(Calculation.calculation_type == calculation_type)
        
        return query.first()

    def get_by_created_by(self, created_by: str, calculation_type: Optional[CalculationType] = None) -> List[Calculation]:
        """Get calculations created by a specific user"""
        query = self.db.query(Calculation).filter(
            Calculation.created_by == created_by, 
            Calculation.is_active == True
        )
        
        if calculation_type:
            query = query.filter(Calculation.calculation_type == calculation_type)
        
        return query.order_by(Calculation.created_at.desc()).all()

    def get_pending_approval(self) -> List[Calculation]:
        """Get calculations pending approval"""
        return (
            self.db.query(Calculation)
            .filter(
                Calculation.is_active == True,
                Calculation.approved_by.is_(None)
            )
            .order_by(Calculation.created_at.desc())
            .all()
        )

    def get_approved(self, calculation_type: Optional[CalculationType] = None) -> List[Calculation]:
        """Get approved calculations"""
        query = self.db.query(Calculation).filter(
            Calculation.is_active == True,
            Calculation.approved_by.isnot(None)
        )
        
        if calculation_type:
            query = query.filter(Calculation.calculation_type == calculation_type)
        
        return query.order_by(Calculation.approval_date.desc()).all()

    def create(self, calculation: Calculation) -> Calculation:
        """Create a new calculation"""
        self.db.add(calculation)
        self.db.commit()
        self.db.refresh(calculation)
        return calculation

    def update(self, calculation: Calculation) -> Calculation:
        """Update an existing calculation"""
        self.db.commit()
        self.db.refresh(calculation)
        return calculation

    def soft_delete(self, calculation: Calculation) -> Calculation:
        """Soft delete a calculation by setting is_active=False"""
        calculation.is_active = False
        self.db.commit()
        return calculation

    def hard_delete(self, calculation: Calculation) -> None:
        """Hard delete a calculation (use with caution)"""
        self.db.delete(calculation)
        self.db.commit()

    def count_by_type(self) -> Dict[str, int]:
        """Get count of calculations by type"""
        results = (
            self.db.query(Calculation.calculation_type, self.db.func.count(Calculation.id))
            .filter(Calculation.is_active == True)
            .group_by(Calculation.calculation_type)
            .all()
        )
        return {calc_type.value: count for calc_type, count in results}

    def count_by_group_level(self, calculation_type: Optional[CalculationType] = None) -> Dict[str, int]:
        """Get count of calculations by group level"""
        query = self.db.query(Calculation.group_level, self.db.func.count(Calculation.id)).filter(
            Calculation.is_active == True
        )
        
        if calculation_type:
            query = query.filter(Calculation.calculation_type == calculation_type)
        
        results = query.group_by(Calculation.group_level).all()
        return {group_level.value: count for group_level, count in results}

    def count_by_approval_status(self, calculation_type: Optional[CalculationType] = None) -> Dict[str, int]:
        """Get count of calculations by approval status"""
        base_query = self.db.query(Calculation).filter(Calculation.is_active == True)
        
        if calculation_type:
            base_query = base_query.filter(Calculation.calculation_type == calculation_type)
        
        approved_count = base_query.filter(Calculation.approved_by.isnot(None)).count()
        pending_count = base_query.filter(Calculation.approved_by.is_(None)).count()
        
        return {
            "approved": approved_count,
            "pending": pending_count
        }

    def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall calculation statistics"""
        total_count = self.db.query(Calculation).filter(Calculation.is_active == True).count()
        
        return {
            "total_calculations": total_count,
            "by_type": self.count_by_type(),
            "by_group_level": self.count_by_group_level(),
            "approval_status": self.count_by_approval_status()
        }

    def get_activity_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get calculation activity summary for the last N days"""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        recent_count = (
            self.db.query(Calculation)
            .filter(
                Calculation.is_active == True,
                Calculation.created_at >= cutoff_date
            )
            .count()
        )
        
        recent_approvals = (
            self.db.query(Calculation)
            .filter(
                Calculation.is_active == True,
                Calculation.approval_date >= cutoff_date
            )
            .count()
        )
        
        return {
            "period_days": days,
            "recent_calculations": recent_count,
            "recent_approvals": recent_approvals
        }


# Keep the old class names as aliases for backward compatibility during transition
UserCalculationDAO = UnifiedCalculationDAO
SystemCalculationDAO = UnifiedCalculationDAO
CalculationStatsDAO = UnifiedCalculationDAO