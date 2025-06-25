#!/usr/bin/env python3
"""
Add Dependent Calculation Columns Migration
Adds calculation_dependencies and calculation_expression columns to user_calculations table
"""

import sqlite3
import os
import sys
from pathlib import Path


def add_dependent_calculation_columns():
    """Add the new columns for dependent calculations"""
    
    # Path to the config database (where user_calculations table is)
    db_path = Path(__file__).parent.parent / "vibez_config.db"
    
    print(f"Database path: {db_path}")
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        
        print("Connected to database successfully")
        
        # Check if user_calculations table exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_calculations'"
        )
        if not cursor.fetchone():
            print("Error: user_calculations table not found")
            return False
        
        # Check current table structure
        cursor = conn.execute("PRAGMA table_info(user_calculations)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"Current columns: {columns}")
        
        # Check if columns already exist
        if 'calculation_dependencies' in columns:
            print("calculation_dependencies column already exists")
        else:
            print("Adding calculation_dependencies column...")
            conn.execute("""
                ALTER TABLE user_calculations 
                ADD COLUMN calculation_dependencies TEXT NULL
            """)
            print("✓ calculation_dependencies column added")
        
        if 'calculation_expression' in columns:
            print("calculation_expression column already exists")
        else:
            print("Adding calculation_expression column...")
            conn.execute("""
                ALTER TABLE user_calculations 
                ADD COLUMN calculation_expression TEXT NULL
            """)
            print("✓ calculation_expression column added")
        
        # Create schema_migrations table if it doesn't exist
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL,
                description TEXT
            )
        """)
        
        # Record this migration
        conn.execute("""
            INSERT OR REPLACE INTO schema_migrations (version, applied_at, description) 
            VALUES (8, datetime('now'), 'Add dependent calculation columns')
        """)
        
        conn.commit()
        
        # Verify the changes
        print("\n--- Verification ---")
        cursor = conn.execute("PRAGMA table_info(user_calculations)")
        updated_columns = [row[1] for row in cursor.fetchall()]
        print(f"Updated columns: {updated_columns}")
        
        if 'calculation_dependencies' in updated_columns and 'calculation_expression' in updated_columns:
            print("✓ Migration completed successfully!")
        else:
            print("✗ Migration may have failed - columns not found")
            return False
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        return False


if __name__ == "__main__":
    print("Adding dependent calculation columns to user_calculations table...")
    success = add_dependent_calculation_columns()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("The user_calculations table now supports dependent calculations.")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)