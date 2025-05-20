"""
Database connection utilities for Celery tasks
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path

# Get the project root path
PROJECT_ROOT = os.environ.get('PROJECT_ROOT', str(Path(__file__).resolve().parent.parent.parent))

# Database connection configuration
# Modified to work with Docker environment
DB_USER = os.environ.get('VIBEZ_DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('VIBEZ_DB_PASSWORD', 'password')
DB_HOST = os.environ.get('VIBEZ_DB_HOST', 'backend')  # Use backend service name in Docker
DB_PORT = os.environ.get('VIBEZ_DB_PORT', '5432')
DB_NAME = os.environ.get('VIBEZ_DB_NAME', 'vibez')
DB_URL = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

def get_db_engine():
    """Create and return a SQLAlchemy engine for the database"""
    return create_engine(DB_URL)

def get_db_session():
    """Create and return a SQLAlchemy session"""
    engine = get_db_engine()
    Session = sessionmaker(bind=engine)
    return Session()
