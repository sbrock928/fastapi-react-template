"""Enhanced dependencies with dual database support and updated query engine import."""

from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db, get_dw_db
from app.query import QueryEngine  # Updated import location

# Existing dependency for config database
SessionDep = Annotated[Session, Depends(get_db)]

# New dependency for data warehouse database
DWSessionDep = Annotated[Session, Depends(get_dw_db)]


# Function-based dependencies for more explicit usage
def get_config_db_session() -> Session:
    """Get config database session - function form for explicit dependency injection."""
    return Depends(get_db)


def get_warehouse_db_session() -> Session:
    """Get data warehouse database session - function form for explicit dependency injection."""
    return Depends(get_dw_db)


# Unified query engine dependency
def get_query_engine(
    dw_db: Session = Depends(get_dw_db), config_db: Session = Depends(get_db)
) -> QueryEngine:
    """Get unified query engine with both database sessions"""
    return QueryEngine(dw_db, config_db)
