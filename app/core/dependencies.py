"""
Async database setup and utility functions.

This module sets up the async database connection, initializes the metadata,
and provides a dependency for async DB sessions.
"""
from fastapi import Depends
from typing import Annotated
from app.core.database import get_session
from sqlalchemy.orm import Session

SessionDep = Annotated[Session, Depends(get_session)]