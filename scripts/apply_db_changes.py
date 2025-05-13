#!/usr/bin/env python3
"""
Script to apply database changes from SQL scripts.
"""
import sqlite3
import os
import sys


def apply_sql_script(db_path, script_path):
    """Apply SQL script to the database"""
    print(f"Applying SQL script: {script_path} to database: {db_path}")

    try:
        # Read the SQL script
        with open(script_path, "r") as f:
            sql_script = f.read()

        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Execute the SQL script
        cursor.executescript(sql_script)

        # Commit the changes
        conn.commit()

        # Close the connection
        conn.close()

        print("SQL script applied successfully!")
        return True
    except Exception as e:
        print(f"Error applying SQL script: {e}")
        return False


if __name__ == "__main__":
    # Path to the database
    db_path = "./sql_app.db"

    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Full path to the database
    db_full_path = os.path.join(project_root, db_path)

    # Path to the SQL script
    script_path = os.path.join(project_root, "scripts", "create_cycles_table.sql")

    print(f"Database path: {db_full_path}")
    print(f"SQL script path: {script_path}")

    if not os.path.exists(db_full_path):
        print(f"Error: Database file does not exist: {db_full_path}")
        sys.exit(1)

    if not os.path.exists(script_path):
        print(f"Error: SQL script file does not exist: {script_path}")
        sys.exit(1)

    success = apply_sql_script(db_full_path, script_path)
    sys.exit(0 if success else 1)
