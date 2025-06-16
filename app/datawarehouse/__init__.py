# app/datawarehouse/__init__.py - UPDATE YOUR EXISTING FILE TO INCLUDE THE NEW MODEL

from .models import Deal, Tranche, TrancheBal, DealCdiVarRpt
from .dao import DatawarehouseDAO

__all__ = [
    # Models
    "Deal",
    "Tranche", 
    "TrancheBal",
    "DealCdiVarRpt",  # Add the new CDI Variable model
    
    # DAOs
    "DatawarehouseDAO",
]