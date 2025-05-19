"""Database configuration and connection utilities."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from typing import Iterator
import importlib

Base = declarative_base()


# Database configuration
SQLITE_DATABASE_URL = "sqlite:///./sql_app.db"
engine = create_engine(SQLITE_DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Initialize database tables for all models."""
    # Import models using importlib to avoid circular imports
    importlib.import_module("app.resources.models")
    importlib.import_module("app.logging.models")
    importlib.import_module("app.documentation.models")

    # Create tables
    Base.metadata.create_all(engine)
    print("Database tables created successfully.")


def get_session() -> Iterator[Session]:
    """Get database session as a dependency injection."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
