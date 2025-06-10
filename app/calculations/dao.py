# app/calculations/dao.py
"""Simplified DAO for calculation operations."""

from sqlalchemy.orm import Session
from typing import List, Optional
from .models import Calculation, GroupLevel

class CalculationDAO:
    """Simplified DAO for calculation data access."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all_calculations(self, group_level: Optional[GroupLevel] = None) -> List[Calculation]:
        """Get all active calculations, optionally filtered by group level."""
        query = self.db.query(Calculation).filter(Calculation.is_active == True)
        
        if group_level:
            query = query.filter(Calculation.group_level == group_level)
        
        return query.order_by(Calculation.name).all()
    
    def get_by_id(self, calc_id: int) -> Optional[Calculation]:
        """Get calculation by ID."""
        return self.db.query(Calculation).filter(
            Calculation.id == calc_id,
            Calculation.is_active == True
        ).first()
    
    def get_by_name_and_group_level(self, name: str, group_level: GroupLevel) -> Optional[Calculation]:
        """Get calculation by name and group level."""
        return self.db.query(Calculation).filter(
            Calculation.name == name,
            Calculation.group_level == group_level,
            Calculation.is_active == True
        ).first()
    
    def create(self, calculation: Calculation) -> Calculation:
        """Create a new cal culation."""
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