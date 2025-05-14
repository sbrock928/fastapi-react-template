from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

# Base class for all models
Base = declarative_base()

# Database configuration
SQLITE_DATABASE_URL = "sqlite:///./sql_app.db"
engine = create_engine(SQLITE_DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(
    bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
)


def init_db():
    # Make sure we import all models here
    from app.resources.models import User, Employee
    from app.logging.models import Log

    # Create tables
    Base.metadata.create_all(engine)
    print("Database tables created successfully.")


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
