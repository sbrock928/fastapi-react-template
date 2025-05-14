from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from typing import Iterator, Any, TypeVar, Type, cast

# Type-checking annotation for the Base class
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.declarative import DeclarativeMeta

    Base: DeclarativeMeta
else:
    # Normal runtime Base class
    Base = declarative_base()

# Create a type variable for use with Base models
ModelType = TypeVar("ModelType", bound=Any)

# Database configuration
SQLITE_DATABASE_URL = "sqlite:///./sql_app.db"
engine = create_engine(SQLITE_DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(
    bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
)


def init_db() -> None:
    # Make sure we import all models here
    from app.resources.models import User, Employee, Subscriber
    from app.logging.models import Log
    from app.documentation.models import Note

    # Create tables
    Base.metadata.create_all(engine)
    print("Database tables created successfully.")


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
