import os
import sqlite3
import sys

def add_missing_columns():
    """Add missing columns to the database."""
    print("Starting database migration to add missing columns...")
    
    # Define database path
    db_path = "vibez.db"  # Default SQLite database path
    
    # First check if the database file exists
    if not os.path.exists(db_path):
        print(f"Database file {db_path} does not exist.")
        print("Please start the application at least once to create the database.")
        return
    
    # Connect directly to the SQLite database
    print(f"Connecting to existing database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if 'log' table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='log'")
        if not cursor.fetchone():
            print("Log table does not exist. Please start the application at least once.")
            return
            
        # Check existing columns in the log table
        cursor.execute("PRAGMA table_info(log)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        # Add application_id column if it doesn't exist
        if "application_id" not in column_names:
            print("Adding application_id column to log table...")
            cursor.execute("ALTER TABLE log ADD COLUMN application_id TEXT")
            print("Migration completed successfully.")
        else:
            print("application_id column already exists.")
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {str(e)}")
        return 1
    finally:
        conn.close()
    
    print("Migration process completed.")
    return 0

if __name__ == "__main__":
    sys.exit(add_missing_columns())
