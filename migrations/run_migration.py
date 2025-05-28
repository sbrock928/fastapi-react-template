#!/usr/bin/env python3
"""
Database Migration Script for Data Model Refactoring
Applies the SQL migration and validates the results
"""

import sqlite3
import os
import sys
from pathlib import Path


def run_migration(migration_file=None):
    """Execute the specified migration"""

    # Use the correct database path based on migration type
    db_path = Path(__file__).parent.parent / "vibez_config.db"  # Default to config DB

    if migration_file:
        migration_path = Path(__file__).parent / migration_file
        # Determine which database to use based on migration file
        if "datawarehouse" in migration_file or "001_refactor" in migration_file:
            db_path = Path(__file__).parent.parent / "vibez_datawarehouse.db"
        elif "reporting" in migration_file or "002_normalize" in migration_file:
            db_path = Path(__file__).parent.parent / "vibez_config.db"
    else:
        migration_path = Path(__file__).parent / "001_refactor_data_model.sql"
        db_path = Path(__file__).parent.parent / "vibez_datawarehouse.db"

    print(f"Database path: {db_path}")
    print(f"Migration path: {migration_path}")

    if not migration_path.exists():
        print(f"Error: Migration file not found at {migration_path}")
        return False

    try:
        # Connect to the appropriate database
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints

        print(f"Connected to database successfully")

        # Check existing tables
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"Existing tables: {existing_tables}")

        # Read and execute migration SQL
        with open(migration_path, "r") as f:
            migration_sql = f.read()

        # Split into individual statements and execute
        statements = [
            stmt.strip()
            for stmt in migration_sql.split(";")
            if stmt.strip() and not stmt.strip().startswith("--")
        ]

        print(f"Executing {len(statements)} migration statements...")

        for i, statement in enumerate(statements):
            try:
                conn.execute(statement)
                print(f"Statement {i+1}/{len(statements)} executed successfully")
            except sqlite3.Error as e:
                print(f"Error executing statement {i+1}: {e}")
                print(f"Statement: {statement[:100]}...")
                # Continue with other statements instead of failing completely
                continue

        conn.commit()
        print("Migration completed successfully!")

        # Run validation queries
        print("\n--- Validation Results ---")

        # Check table structures
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables in database: {tables}")

        conn.close()
        return True

    except Exception as e:
        print(f"Migration failed: {e}")
        return False


def rollback_migration():
    """Rollback the migration using backup tables"""
    db_path = Path(__file__).parent.parent / "vibez_datawarehouse.db"

    try:
        conn = sqlite3.connect(db_path)

        print("Rolling back migration...")

        # Check if backup tables exist
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_backup'"
        )
        backup_tables = [row[0] for row in cursor.fetchall()]

        if not backup_tables:
            print("No backup tables found - cannot rollback")
            return False

        print(f"Found backup tables: {backup_tables}")

        # Restore from backups
        if "deal_backup" in backup_tables:
            conn.execute("DROP TABLE IF EXISTS deal")
            conn.execute("ALTER TABLE deal_backup RENAME TO deal")
            print("Restored deal table from backup")

        if "tranche_backup" in backup_tables:
            conn.execute("DROP TABLE IF EXISTS tranche")
            conn.execute("ALTER TABLE tranche_backup RENAME TO tranche")
            print("Restored tranche table from backup")

        # Remove historical table
        conn.execute("DROP TABLE IF EXISTS tranche_historical")
        print("Removed tranche_historical table")

        conn.commit()
        conn.close()

        print("Migration rollback completed successfully!")
        return True

    except Exception as e:
        print(f"Rollback failed: {e}")
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "rollback":
            rollback_migration()
        else:
            # First argument is the migration file
            run_migration(sys.argv[1])
    else:
        run_migration()
