import sqlite3
import os
from sqlmodel import SQLModel, create_engine
from app.database import SQLITE_DATABASE_URL

def add_missing_columns():
    """Add missing columns to the database."""
    print("Starting database migration to add missing columns...")
    
    # First check if the database file exists
    db_path = SQLITE_DATABASE_URL.replace('sqlite:///', '')
    if not os.path.exists(db_path):
        print(f"Database file {db_path} does not exist. Will be created with new schema.")
        # Import models to ensure they're registered with SQLModel
        from app.logging.models import Log
        from app.resources.models import User, Employee, Subscriber
        
        # Create tables with new schema
        engine = create_engine(SQLITE_DATABASE_URL, connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(engine)
        print("Database created with new schema.")
        return
    
    # Connect directly to the SQLite database
    print(f"Connecting to existing database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if 'username' column exists in the log table
    cursor.execute("PRAGMA table_info(log)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # Add missing columns if they don't exist
    try:
        if 'username' not in columns:
            print("Adding 'username' column to log table...")
            cursor.execute("ALTER TABLE log ADD COLUMN username TEXT")
        
        if 'hostname' not in columns:
            print("Adding 'hostname' column to log table...")
            cursor.execute("ALTER TABLE log ADD COLUMN hostname TEXT")
        
        # Check if application_id column exists in log table and add it if it doesn't
        cursor.execute("PRAGMA table_info(log)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if "application_id" not in column_names:
            print("Adding application_id column to log table...")
            cursor.execute("ALTER TABLE log ADD COLUMN application_id TEXT")
        
        conn.commit()
        print("Migration completed successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_missing_columns()
