# app/calculations/dao.py
"""Data Access Objects for the new separated calculation system"""

from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from .models import UserCalculation, SystemCalculation, GroupLevel


class UserCalculationDAO:
    """DAO for user-defined calculations"""

    def __init__(self, db: Session):
        self.db = db

    def get_all(self, group_level: Optional[GroupLevel] = None) -> List[UserCalculation]:
        """Get all active user calculations"""
        query = self.db.query(UserCalculation).filter(UserCalculation.is_active == True)
        
        if group_level:
            query = query.filter(UserCalculation.group_level == group_level)
        
        return query.order_by(UserCalculation.name).all()

    def get_by_id(self, calc_id: int) -> Optional[UserCalculation]:
        """Get user calculation by ID"""
        return (
            self.db.query(UserCalculation)
            .filter(UserCalculation.id == calc_id, UserCalculation.is_active == True)
            .first()
        )

    def get_by_source_field(self, source_field: str) -> Optional[UserCalculation]:
        """Get user calculation by source_field"""
        return (
            self.db.query(UserCalculation)
            .filter(
                UserCalculation.source_field == source_field,
                UserCalculation.is_active == True
            )
            .first()
        )

    def get_by_name_and_group_level(self, name: str, group_level: GroupLevel) -> Optional[UserCalculation]:
        """Get user calculation by name and group level"""
        return (
            self.db.query(UserCalculation)
            .filter(
                UserCalculation.name == name,
                UserCalculation.group_level == group_level,
                UserCalculation.is_active == True,
            )
            .first()
        )

    def get_by_source_field_and_group_level(self, source_field: str, group_level: GroupLevel) -> Optional[UserCalculation]:
        """Get user calculation by source_field and group_level"""
        return (
            self.db.query(UserCalculation)
            .filter(
                UserCalculation.source_field == source_field,
                UserCalculation.group_level == group_level,
                UserCalculation.is_active == True
            )
            .first()
        )

    def get_by_names(self, names: List[str]) -> List[UserCalculation]:
        """Get user calculations by list of names"""
        return (
            self.db.query(UserCalculation)
            .filter(UserCalculation.name.in_(names), UserCalculation.is_active == True)
            .all()
        )

    def get_by_created_by(self, created_by: str) -> List[UserCalculation]:
        """Get user calculations created by a specific user"""
        return (
            self.db.query(UserCalculation)
            .filter(UserCalculation.created_by == created_by, UserCalculation.is_active == True)
            .order_by(UserCalculation.created_at.desc())
            .all()
        )

    def get_with_advanced_features(self) -> List[UserCalculation]:
        """Get user calculations that use advanced features"""
        return (
            self.db.query(UserCalculation)
            .filter(
                UserCalculation.is_active == True,
                UserCalculation.advanced_config.isnot(None)
            )
            .all()
        )

    def create(self, calculation: UserCalculation) -> UserCalculation:
        """Create a new user calculation"""
        self.db.add(calculation)
        self.db.commit()
        self.db.refresh(calculation)
        return calculation

    def update(self, calculation: UserCalculation) -> UserCalculation:
        """Update an existing user calculation"""
        self.db.commit()
        self.db.refresh(calculation)
        return calculation

    def soft_delete(self, calculation: UserCalculation) -> UserCalculation:
        """Soft delete a user calculation by setting is_active=False"""
        calculation.is_active = False
        self.db.commit()
        return calculation

    def hard_delete(self, calculation: UserCalculation) -> None:
        """Hard delete a user calculation (use with caution)"""
        self.db.delete(calculation)
        self.db.commit()

    def count_by_group_level(self) -> Dict[str, int]:
        """Get count of user calculations by group level"""
        results = (
            self.db.query(UserCalculation.group_level, self.db.func.count(UserCalculation.id))
            .filter(UserCalculation.is_active == True)
            .group_by(UserCalculation.group_level)
            .all()
        )
        return {group_level.value: count for group_level, count in results}

    def count_by_aggregation_function(self) -> Dict[str, int]:
        """Get count of user calculations by aggregation function"""
        results = (
            self.db.query(UserCalculation.aggregation_function, self.db.func.count(UserCalculation.id))
            .filter(UserCalculation.is_active == True)
            .group_by(UserCalculation.aggregation_function)
            .all()
        )
        return {agg_func.value: count for agg_func, count in results}

    def count_by_source_model(self) -> Dict[str, int]:
        """Get count of user calculations by source model"""
        results = (
            self.db.query(UserCalculation.source_model, self.db.func.count(UserCalculation.id))
            .filter(UserCalculation.is_active == True)
            .group_by(UserCalculation.source_model)
            .all()
        )
        return {source_model.value: count for source_model, count in results}

    def get_all_by_source_field(self, source_field: str) -> List[UserCalculation]:
        """Get all active user calculations by source_field (not just the first one)"""
        return (
            self.db.query(UserCalculation)
            .filter(
                UserCalculation.source_field == source_field,
                UserCalculation.is_active == True
            )
            .order_by(
                # Prefer tranche-level calculations first, then deal-level
                UserCalculation.group_level.desc(),  # 'tranche' comes after 'deal' alphabetically
                UserCalculation.created_at.desc()
            )
            .all()
        )

class SystemCalculationDAO:
    """DAO for system-defined calculations"""

    def __init__(self, db: Session):
        self.db = db

    def get_all(self, group_level: Optional[GroupLevel] = None, approved_only: bool = False) -> List[SystemCalculation]:
        """Get all active system calculations"""
        query = self.db.query(SystemCalculation).filter(SystemCalculation.is_active == True)
        
        if group_level:
            query = query.filter(SystemCalculation.group_level == group_level)
        
        if approved_only:
            query = query.filter(SystemCalculation.approved_by.isnot(None))
        
        return query.order_by(SystemCalculation.name).all()

    def get_by_id(self, calc_id: int) -> Optional[SystemCalculation]:
        """Get system calculation by ID"""
        return (
            self.db.query(SystemCalculation)
            .filter(SystemCalculation.id == calc_id, SystemCalculation.is_active == True)
            .first()
        )

    def get_by_result_column_name(self, result_column_name: str) -> Optional[SystemCalculation]:
        """Get system calculation by result_column_name"""
        return (
            self.db.query(SystemCalculation)
            .filter(
                SystemCalculation.result_column_name == result_column_name,
                SystemCalculation.is_active == True
            )
            .first()
        )

    def get_by_name_and_group_level(self, name: str, group_level: GroupLevel) -> Optional[SystemCalculation]:
        """Get system calculation by name and group level"""
        return (
            self.db.query(SystemCalculation)
            .filter(
                SystemCalculation.name == name,
                SystemCalculation.group_level == group_level,
                SystemCalculation.is_active == True,
            )
            .first()
        )

    def get_by_created_by(self, created_by: str) -> List[SystemCalculation]:
        """Get system calculations created by a specific user"""
        return (
            self.db.query(SystemCalculation)
            .filter(SystemCalculation.created_by == created_by, SystemCalculation.is_active == True)
            .order_by(SystemCalculation.created_at.desc())
            .all()
        )

    def get_pending_approval(self) -> List[SystemCalculation]:
        """Get system calculations pending approval"""
        return (
            self.db.query(SystemCalculation)
            .filter(
                SystemCalculation.is_active == True,
                SystemCalculation.approved_by.is_(None)
            )
            .order_by(SystemCalculation.created_at.desc())
            .all()
        )

    def get_approved(self) -> List[SystemCalculation]:
        """Get approved system calculations"""
        return (
            self.db.query(SystemCalculation)
            .filter(
                SystemCalculation.is_active == True,
                SystemCalculation.approved_by.isnot(None)
            )
            .order_by(SystemCalculation.approval_date.desc())
            .all()
        )

    def get_by_complexity(self, complexity: str) -> List[SystemCalculation]:
        """Get system calculations by performance complexity"""
        return (
            self.db.query(SystemCalculation)
            .filter(
                SystemCalculation.is_active == True,
                SystemCalculation.metadata_config.contains({"performance_hints": {"complexity": complexity}})
            )
            .all()
        )

    def create(self, calculation: SystemCalculation) -> SystemCalculation:
        """Create a new system calculation"""
        self.db.add(calculation)
        self.db.commit()
        self.db.refresh(calculation)
        return calculation

    def update(self, calculation: SystemCalculation) -> SystemCalculation:
        """Update an existing system calculation"""
        self.db.commit()
        self.db.refresh(calculation)
        return calculation

    def soft_delete(self, calculation: SystemCalculation) -> SystemCalculation:
        """Soft delete a system calculation by setting is_active=False"""
        calculation.is_active = False
        self.db.commit()
        return calculation

    def hard_delete(self, calculation: SystemCalculation) -> None:
        """Hard delete a system calculation (use with caution)"""
        self.db.delete(calculation)
        self.db.commit()

    def count_by_group_level(self) -> Dict[str, int]:
        """Get count of system calculations by group level"""
        results = (
            self.db.query(SystemCalculation.group_level, self.db.func.count(SystemCalculation.id))
            .filter(SystemCalculation.is_active == True)
            .group_by(SystemCalculation.group_level)
            .all()
        )
        return {group_level.value: count for group_level, count in results}

    def count_by_approval_status(self) -> Dict[str, int]:
        """Get count of system calculations by approval status"""
        approved_count = (
            self.db.query(SystemCalculation)
            .filter(
                SystemCalculation.is_active == True,
                SystemCalculation.approved_by.isnot(None)
            )
            .count()
        )
        
        pending_count = (
            self.db.query(SystemCalculation)
            .filter(
                SystemCalculation.is_active == True,
                SystemCalculation.approved_by.is_(None)
            )
            .count()
        )
        
        return {
            "approved": approved_count,
            "pending": pending_count
        }


class CalculationStatsDAO:
    """DAO for calculation statistics across both types"""

    def __init__(self, db: Session):
        self.db = db
        self.user_dao = UserCalculationDAO(db)
        self.system_dao = SystemCalculationDAO(db)

    def get_overall_counts(self) -> Dict[str, Any]:
        """Get overall calculation counts and statistics"""
        user_count = self.db.query(UserCalculation).filter(UserCalculation.is_active == True).count()
        system_count = self.db.query(SystemCalculation).filter(SystemCalculation.is_active == True).count()
        
        return {
            "total_calculations": user_count + system_count,
            "user_calculations": user_count,
            "system_calculations": system_count,
            "user_by_group_level": self.user_dao.count_by_group_level(),
            "user_by_aggregation_function": self.user_dao.count_by_aggregation_function(),
            "user_by_source_model": self.user_dao.count_by_source_model(),
            "system_by_group_level": self.system_dao.count_by_group_level(),
            "system_by_approval_status": self.system_dao.count_by_approval_status()
        }

    def get_activity_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get calculation activity summary for the last N days"""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        recent_user_calcs = (
            self.db.query(UserCalculation)
            .filter(
                UserCalculation.is_active == True,
                UserCalculation.created_at >= cutoff_date
            )
            .count()
        )
        
        recent_system_calcs = (
            self.db.query(SystemCalculation)
            .filter(
                SystemCalculation.is_active == True,
                SystemCalculation.created_at >= cutoff_date
            )
            .count()
        )
        
        recent_approvals = (
            self.db.query(SystemCalculation)
            .filter(
                SystemCalculation.is_active == True,
                SystemCalculation.approval_date >= cutoff_date
            )
            .count()
        )
        
        return {
            "period_days": days,
            "recent_user_calculations": recent_user_calcs,
            "recent_system_calculations": recent_system_calcs,
            "recent_approvals": recent_approvals,
            "total_recent": recent_user_calcs + recent_system_calcs
        }

    def get_creator_stats(self) -> Dict[str, Any]:
        """Get statistics by creator"""
        # User calculation creators
        user_creators = (
            self.db.query(UserCalculation.created_by, self.db.func.count(UserCalculation.id))
            .filter(UserCalculation.is_active == True)
            .group_by(UserCalculation.created_by)
            .all()
        )
        
        # System calculation creators
        system_creators = (
            self.db.query(SystemCalculation.created_by, self.db.func.count(SystemCalculation.id))
            .filter(SystemCalculation.is_active == True)
            .group_by(SystemCalculation.created_by)
            .all()
        )
        
        return {
            "user_calculation_creators": {creator: count for creator, count in user_creators},
            "system_calculation_creators": {creator: count for creator, count in system_creators}
        }

    def get_advanced_features_usage(self) -> Dict[str, Any]:
        """Get statistics on advanced features usage"""
        user_calcs_with_advanced = (
            self.db.query(UserCalculation)
            .filter(
                UserCalculation.is_active == True,
                UserCalculation.advanced_config.isnot(None)
            )
            .count()
        )
        
        total_user_calcs = (
            self.db.query(UserCalculation)
            .filter(UserCalculation.is_active == True)
            .count()
        )
        
        # Analyze what advanced features are being used
        advanced_calcs = (
            self.db.query(UserCalculation.advanced_config)
            .filter(
                UserCalculation.is_active == True,
                UserCalculation.advanced_config.isnot(None)
            )
            .all()
        )
        
        feature_usage = {}
        for (config,) in advanced_calcs:
            if config:
                for feature in config.keys():
                    feature_usage[feature] = feature_usage.get(feature, 0) + 1
        
        return {
            "total_user_calculations": total_user_calcs,
            "calculations_with_advanced_features": user_calcs_with_advanced,
            "advanced_features_adoption_rate": (
                user_calcs_with_advanced / total_user_calcs * 100 
                if total_user_calcs > 0 else 0
            ),
            "feature_usage_breakdown": feature_usage
        }