"""
Migration 005: Allow NULL values in filter_conditions.value column

This migration fixes the issue where filter operators like IS_NULL and IS_NOT_NULL
cannot store NULL values in the value column due to a NOT NULL constraint.
"""

import sqlite3
import os

def run_migration():
    """Run migration to allow NULL values in filter_conditions.value column."""
    db_path = "vibez_config.db"
    
    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found. Skipping migration.")
        return
    
    print(f"Running migration 005 on {db_path}...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='filter_conditions'
        """)
        
        if not cursor.fetchone():
            print("filter_conditions table not found. Skipping migration.")
            conn.close()
            return
        
        # SQLite doesn't support ALTER COLUMN directly, so we need to recreate the table
        print("Creating new filter_conditions table with nullable value column...")
        
        # Create new table with correct schema
        cursor.execute("""
            CREATE TABLE filter_conditions_new (
                id INTEGER PRIMARY KEY,
                report_id INTEGER NOT NULL,
                field_name VARCHAR NOT NULL,
                operator VARCHAR NOT NULL,
                value VARCHAR NULL,
                FOREIGN KEY(report_id) REFERENCES reports (id)
            )
        """)
        
        # Copy data from old table to new table
        cursor.execute("""
            INSERT INTO filter_conditions_new (id, report_id, field_name, operator, value)
            SELECT id, report_id, field_name, operator, value
            FROM filter_conditions
        """)
        
        # Drop old table
        cursor.execute("DROP TABLE filter_conditions")
        
        # Rename new table
        cursor.execute("ALTER TABLE filter_conditions_new RENAME TO filter_conditions")
        
        # Recreate indexes if they existed
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_filter_conditions_id ON filter_conditions (id)")
        
        conn.commit()
        print("Migration 005 completed successfully!")
        
    except Exception as e:
        print(f"Error running migration 005: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()