from sqlmodel import SQLModel, Session, create_engine

# Database configuration
SQLITE_DATABASE_URL = "sqlite:///./sql_app.db"
engine = create_engine(SQLITE_DATABASE_URL, connect_args={"check_same_thread": False})

def init_db():
    # Make sure we import all models here
    from app.models.base import User, Employee
    
    # Create tables
    SQLModel.metadata.create_all(engine)
    print("Database tables created successfully.")

def get_session():
    with Session(engine) as session:
        yield session