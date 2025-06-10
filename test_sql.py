#!/usr/bin/env python3
"""
Simple SQL Test Script for FastAPI React Template
Allows you to copy/paste and execute raw SQL queries against the data warehouse database.
"""

import sqlite3
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import json
from datetime import datetime

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))


class SQLTester:
    def __init__(self, db_path: str = "vibez_datawarehouse.db"):
        """Initialize the SQL tester with database connection."""
        self.db_path = db_path
        if not os.path.exists(db_path):
            print(f"❌ Database file not found: {db_path}")
            print("Make sure you're running this from the project root directory.")
            sys.exit(1)

        print(f"✅ Connected to database: {db_path}")

    def execute_sql(self, sql: str) -> List[Dict[str, Any]]:
        """Execute SQL query and return results."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()

            # Execute the query
            cursor.execute(sql)

            # Fetch results
            rows = cursor.fetchall()

            # Convert to list of dictionaries
            results = []
            for row in rows:
                results.append(dict(row))

            conn.close()
            return results

        except Exception as e:
            print(f"❌ SQL Execution Error: {e}")
            return []

    def format_results(self, results: List[Dict[str, Any]]) -> str:
        """Format query results for display."""
        if not results:
            return "No results returned."

        # Get column names
        columns = list(results[0].keys())

        # Calculate column widths
        col_widths = {}
        for col in columns:
            col_widths[col] = max(len(str(col)), max(len(str(row.get(col, ""))) for row in results))

        # Build table
        output = []

        # Header
        header = " | ".join(str(col).ljust(col_widths[col]) for col in columns)
        output.append(header)
        output.append("-" * len(header))

        # Rows
        for row in results:
            row_str = " | ".join(str(row.get(col, "")).ljust(col_widths[col]) for col in columns)
            output.append(row_str)

        return "\n".join(output)

    def save_results(self, results: List[Dict[str, Any]], filename: str = None) -> str:
        """Save results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sql_results_{timestamp}.json"

        with open(filename, "w") as f:
            json.dump(results, f, indent=2, default=str)

        return filename

    def interactive_mode(self):
        """Run in interactive mode for testing multiple queries."""
        print("\n" + "=" * 60)
        print("🧪 SQL TESTER - Interactive Mode")
        print("=" * 60)
        print("Paste your SQL queries and press Enter.")
        print("Commands:")
        print("  - Type 'quit' or 'exit' to stop")
        print("  - Type 'clear' to clear screen")
        print("  - Type 'save' to save last results to JSON")
        print("  - Type 'tables' to show available tables")
        print("  - Type 'schema <table>' to show table schema")
        print("-" * 60)

        last_results = []

        while True:
            try:
                print("\n📝 Enter SQL query (or command):")
                user_input = input("> ").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.lower() in ["quit", "exit"]:
                    print("👋 Goodbye!")
                    break

                elif user_input.lower() == "clear":
                    os.system("clear" if os.name == "posix" else "cls")
                    continue

                elif user_input.lower() == "save":
                    if last_results:
                        filename = self.save_results(last_results)
                        print(f"💾 Results saved to: {filename}")
                    else:
                        print("❌ No results to save. Run a query first.")
                    continue

                elif user_input.lower() == "tables":
                    self._show_tables()
                    continue

                elif user_input.lower().startswith("schema "):
                    table_name = user_input[7:].strip()
                    self._show_schema(table_name)
                    continue

                # Execute SQL
                print(f"\n🔄 Executing query...")
                results = self.execute_sql(user_input)

                if results:
                    last_results = results
                    print(f"\n✅ Query executed successfully! ({len(results)} rows)")
                    print("\n📊 Results:")
                    print(self.format_results(results))
                else:
                    print("❌ Query failed or returned no results.")

            except KeyboardInterrupt:
                print("\n\n👋 Interrupted by user. Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    def _show_tables(self):
        """Show available tables in the database."""
        sql = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        results = self.execute_sql(sql)

        if results:
            print("\n📋 Available Tables:")
            for row in results:
                print(f"  - {row['name']}")
        else:
            print("❌ No tables found.")

    def _show_schema(self, table_name: str):
        """Show schema for a specific table."""
        sql = f"PRAGMA table_info({table_name});"
        results = self.execute_sql(sql)

        if results:
            print(f"\n📋 Schema for table '{table_name}':")
            for row in results:
                nullable = "NULL" if row["notnull"] == 0 else "NOT NULL"
                default = f" DEFAULT {row['dflt_value']}" if row["dflt_value"] else ""
                pk = " PRIMARY KEY" if row["pk"] else ""
                print(f"  - {row['name']}: {row['type']} {nullable}{default}{pk}")
        else:
            print(f"❌ Table '{table_name}' not found.")


def main():
    """Main function to run the SQL tester."""
    print("🧪 FastAPI React Template - SQL Tester")
    print("=" * 50)

    # Check if we're in the right directory
    if not os.path.exists("vibez_datawarehouse.db"):
        print("❌ Database not found in current directory.")
        print("Please run this script from the project root directory.")
        sys.exit(1)

    tester = SQLTester()

    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--file" and len(sys.argv) > 2:
            # Execute SQL from file
            sql_file = sys.argv[2]
            if os.path.exists(sql_file):
                with open(sql_file, "r") as f:
                    sql = f.read()
                print(f"📄 Executing SQL from file: {sql_file}")
                results = tester.execute_sql(sql)
                if results:
                    print(f"✅ Query executed successfully! ({len(results)} rows)")
                    print(tester.format_results(results))

                    # Save results
                    filename = tester.save_results(results)
                    print(f"💾 Results saved to: {filename}")
            else:
                print(f"❌ File not found: {sql_file}")
        elif sys.argv[1] == "--query":
            # Execute SQL from command line
            sql = " ".join(sys.argv[2:])
            print(f"🔄 Executing query: {sql}")
            results = tester.execute_sql(sql)
            if results:
                print(f"✅ Query executed successfully! ({len(results)} rows)")
                print(tester.format_results(results))
        else:
            print("Usage:")
            print("  python test_sql.py                    # Interactive mode")
            print("  python test_sql.py --file query.sql   # Execute from file")
            print("  python test_sql.py --query 'SELECT ...'  # Execute from command line")
    else:
        # Interactive mode
        tester.interactive_mode()


if __name__ == "__main__":
    main()
