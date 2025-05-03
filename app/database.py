from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.orm import sessionmaker


# Database configuration
SQLITE_DATABASE_URL = "sqlite:///./sql_app.db"
engine = create_engine(SQLITE_DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

def init_db():
    # Make sure we import all models here
    from app.resources.models import User, Employee
    from app.logging.models import Log
    
    # Create tables
    SQLModel.metadata.create_all(engine)
    print("Database tables created successfully.")

def get_session():
    with Session(engine) as session:
        yield session