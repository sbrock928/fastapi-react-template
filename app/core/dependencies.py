"""Enhanced dependencies with dual database support."""

from typing import Annotated
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db, get_dw_db

# Existing dependency for config database
SessionDep = Annotated[Session, Depends(get_db)]

# New dependency for data warehouse database
DWSessionDep = Annotated[Session, Depends(get_dw_db)]