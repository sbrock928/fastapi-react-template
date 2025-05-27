#!/usr/bin/env python3
"""
Database Migration Script for Data Model Refactoring
Applies the SQL migration and validates the results
"""

import sqlite3
import os
from pathlib import Path


def run_migration():
    """Execute the data model refactoring migration"""

    # Use the correct data warehouse database path
    db_path = Path(__file__).parent.parent / "vibez_datawarehouse.db"
    migration_path = Path(__file__).parent / "001_refactor_data_model.sql"

    print(f"Database path: {db_path}")
    print(f"Migration path: {migration_path}")

    if not db_path.exists():
        print(f"Error: Data warehouse database not found at {db_path}")
        print("Please run 'python create_sample_data.py' first to create the database.")
        return False

    if not migration_path.exists():
        print(f"Error: Migration file not found at {migration_path}")
        return False

    try:
        # Connect to data warehouse database
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints

        print("Connected to data warehouse database successfully")

        # Check if tables exist before migration
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"Existing tables: {existing_tables}")

        if "deal" not in existing_tables or "tranche" not in existing_tables:
            print("Error: Deal or Tranche tables not found. Please run sample data creation first.")
            return False

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
                return False

        conn.commit()
        print("Migration completed successfully!")

        # Run validation queries
        print("\n--- Validation Results ---")

        # Check table structures
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables in database: {tables}")

        # Check record counts
        cursor = conn.execute("SELECT COUNT(*) FROM deal")
        deal_count = cursor.fetchone()[0]
        print(f"Deal records: {deal_count}")

        cursor = conn.execute("SELECT COUNT(*) FROM tranche")
        tranche_count = cursor.fetchone()[0]
        print(f"Tranche records: {tranche_count}")

        cursor = conn.execute("SELECT COUNT(*) FROM tranche_historical")
        historical_count = cursor.fetchone()[0]
        print(f"Historical records: {historical_count}")

        # Check unique cycles
        cursor = conn.execute(
            "SELECT DISTINCT cycle_code FROM tranche_historical ORDER BY cycle_code"
        )
        cycles = [row[0] for row in cursor.fetchall()]
        print(f"Available cycles: {cycles}")

        # Verify relationships
        cursor = conn.execute(
            """
            SELECT COUNT(*) FROM tranche_historical th
            LEFT JOIN tranche t ON th.tranche_id = t.id
            WHERE t.id IS NULL
        """
        )
        orphaned = cursor.fetchone()[0]
        if orphaned > 0:
            print(f"WARNING: {orphaned} orphaned historical records found!")
        else:
            print("✓ All historical records properly linked to tranches")

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

    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        run_migration()
